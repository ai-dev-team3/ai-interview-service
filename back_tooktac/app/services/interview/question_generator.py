"""이력서 → 예상 면접 질문 생성 및 질문 유형 분류 (LCEL 체인).

LLM 출력은 신뢰하지 않는다. 정규화 단계에서 형태·유형·개수를 모두 강제한다.
"""
import logging
import re
from typing import Any, Optional

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.services.interview.plan import (
    FALLBACK_QUESTION_TYPE,
    MAX_GENERATED_QUESTIONS,
    QUESTION_TYPES,
)
from app.services.llm import get_chat_model

logger = logging.getLogger(__name__)


class ResumeQuestionGenerationError(Exception):
    """LLM 호출 실패 또는 응답에서 쓸 만한 질문을 하나도 얻지 못함"""


_TYPE_GUIDE = """- 개념설명형: 지식이나 개념의 설명을 요구한다. 예) "오버피팅이 무엇인지 설명해주세요"
- 기술형: 특정 기술의 사용·구현 경험의 상세를 요구한다. 예) "PostgreSQL 파이프라인을 어떻게 구성했나요"
- 상황형: 가정된 상황에서의 대응 방식을 요구한다. 예) "출시 직전 데이터 오류가 발견된다면 어떻게 하시겠습니까"
- 행동형: 과거의 실제 경험과 행동을 요구한다. 예) "협업 중 갈등을 해결한 경험을 말해주세요\""""

_GENERATE_TEMPLATE = """당신은 경험 많은 기술 면접관입니다.
아래 지원자의 구조화된 이력서를 분석해 예상 면접 질문을 만드세요.

이력서:
{resume}

질문 유형은 반드시 다음 넷 중 하나입니다.
{type_guide}

규칙:
1. 이력서의 내용이 풍부하고 경력이 길수록 질문을 많이, 빈약하고 신입이면 적게 만드세요.
   질문 수는 당신이 판단하되 최소 1개, 최대 {max_questions}개입니다.
2. 아래 기존 질문들과 의미가 겹치는 질문은 절대 만들지 마세요.
{existing}
3. 새로 만드는 질문들끼리도 의미가 겹치면 안 됩니다.
4. 질문은 한 문장으로 간결하게 쓰고, 마크다운이나 별표를 쓰지 마세요.

출력은 아래 형식의 JSON 객체만 내보내세요. 다른 텍스트는 넣지 마세요.
{{"questions": [{{"question_text": "...", "question_type": "개념설명형"}}]}}"""

_CLASSIFY_TEMPLATE = """다음 면접 질문이 어떤 유형인지 분류하세요.

{type_guide}

질문: {question}

위 네 개의 유형 이름 중 정확히 하나만 출력하세요. 다른 말은 하지 마세요."""


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _dedup_key(text: str) -> str:
    """공백·문장부호를 지운 비교용 키 (정확 중복만 걸러내는 최후 방어)"""
    return re.sub(r"[^\w가-힣]", "", _clean(text)).lower()


def _coerce_type(raw: Any, *, context: str) -> str:
    """LLM이 내놓은 유형 문자열을 QUESTION_TYPES 안의 값으로 강제한다."""
    candidate = _clean(str(raw)).strip("\"'`")
    if candidate in QUESTION_TYPES:
        return candidate
    logger.warning(
        "알 수 없는 질문 유형 %r (%s) — %s으로 폴백", raw, context, FALLBACK_QUESTION_TYPE
    )
    return FALLBACK_QUESTION_TYPE


def _normalize_questions(data: Any) -> list[dict[str, str]]:
    """LLM 응답을 [{"question_text", "question_type"}] 목록으로 정규화한다.

    쓸 수 없는 항목은 조용히 버린다. 하나도 남지 않으면 빈 목록을 반환한다.
    """
    if isinstance(data, dict):
        items = data.get("questions")
    else:
        items = data  # 배열을 바로 뱉는 경우도 허용

    if not isinstance(items, list):
        logger.warning("질문 생성 응답이 목록이 아님: %r", type(items).__name__)
        return []

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        text = _clean(item.get("question_text") or item.get("question") or "")
        if not text:
            continue
        key = _dedup_key(text)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({
            "question_text": text,
            "question_type": _coerce_type(item.get("question_type"), context=text[:30]),
        })
        if len(normalized) >= MAX_GENERATED_QUESTIONS:
            break
    return normalized


class ResumeQuestionGenerator:
    """구조화 이력서로부터 예상 면접 질문을 1~10개 생성한다."""

    def __init__(self, llm: Optional[Runnable] = None):
        self.llm = llm if llm is not None else get_chat_model(primary="gemini", temperature=0.4)
        self.chain = (
            ChatPromptTemplate.from_template(_GENERATE_TEMPLATE)
            | self.llm
            | JsonOutputParser()
        )

    def generate(self, structured: dict, existing: list[str] | None = None) -> list[dict[str, str]]:
        existing = existing or []
        existing_block = (
            "\n".join(f"- {q}" for q in existing) if existing else "(없음)"
        )
        try:
            data = self.chain.invoke({
                "resume": structured,
                "type_guide": _TYPE_GUIDE,
                "max_questions": MAX_GENERATED_QUESTIONS,
                "existing": existing_block,
            })
        except Exception as e:
            logger.exception("면접 질문 생성 실패")
            raise ResumeQuestionGenerationError(str(e)) from e

        questions = _normalize_questions(data)
        if not questions:
            raise ResumeQuestionGenerationError("생성된 질문이 없습니다.")
        return questions


class QuestionTypeClassifier:
    """사용자가 직접 쓴 질문의 유형을 판별한다.

    채점 가중치(score/scoring.py)가 이 값에 의존하므로, 판별 실패는
    조용히 넘기지 않고 경고 로그를 남긴 뒤 폴백한다.
    """

    def __init__(self, llm: Optional[Runnable] = None):
        # 같은 질문에 항상 같은 유형이 나오도록 온도를 0으로 둔다
        self.llm = llm if llm is not None else get_chat_model(primary="gemini", temperature=0.0)
        self.chain = (
            ChatPromptTemplate.from_template(_CLASSIFY_TEMPLATE)
            | self.llm
            | StrOutputParser()
        )

    def classify(self, question_text: str) -> str:
        """항상 QUESTION_TYPES 안의 값을 반환한다. LLM이 실패해도 예외를 던지지 않는다."""
        try:
            raw = self.chain.invoke({
                "type_guide": _TYPE_GUIDE,
                "question": _clean(question_text),
            })
        except Exception:
            logger.warning(
                "질문 유형 분류 실패 — %s으로 폴백 (question=%.30s)",
                FALLBACK_QUESTION_TYPE, question_text, exc_info=True,
            )
            return FALLBACK_QUESTION_TYPE
        return _coerce_type(raw, context="분류기 출력")
