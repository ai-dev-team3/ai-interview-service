"""실전 면접의 다음 질문을 만든다.

에이전트는 하나뿐이고 호출도 답변당 한 번이다.
"꼬리질문을 할지, 새 주제로 넘어갈지"와 "그 질문의 내용"을 한 번에 정한다.
라우팅 노드와 생성 노드를 나누면 LLM 호출이 두 번이 되는데, 준비 시간(10초) 안에
STT 까지 끝나야 하므로 그럴 예산이 없다.

질문 풀을 쓰지 않는다.
  연습 면접은 이력서 등록 시 만들어둔 질문 풀에서 사용자가 고른다.
  실전은 이력서와 '지금까지의 대화'를 매번 통째로 주고 새로 만든다. 그래야 같은
  이력서라도 대화 흐름에 따라 다른 질문이 나온다. 이미 물어본 질문이 프롬프트에
  다 들어 있으므로 중복도 자연히 피한다.

이 호출은 사용자를 기다리게 한다. 실패하면 예외를 던지지 않고 None 을 돌려준다 —
호출부가 마무리 질문으로 넘어가 면접을 끝낸다. 면접이 멈추는 것보다 낫다.
"""
import logging
import time
from typing import Any, NamedTuple, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.services.interview.question_generator import _TYPE_GUIDE, _clean, _coerce_type
from app.services.llm import get_chat_model

logger = logging.getLogger(__name__)


class NextQuestion(NamedTuple):
    question_text: str
    question_type: str
    is_follow_up: bool


_TEMPLATE = """당신은 경험 많은 기술 면접관입니다. 실제 면접을 진행하고 있습니다.

지원자의 이력서:
{resume}

지금까지의 면접 내용:
{history}

남은 시간: 약 {remaining_minutes}분

지금까지의 답변을 보고 다음 질문 하나를 정하세요. 두 가지 중 하나입니다.

1. 꼬리질문 — 직전 답변을 더 파고든다
   - 답변이 추상적이어서 구체적인 사례나 수치를 물어야 할 때
   - 답변에 나온 기술·선택의 근거를 물어야 할 때
   - 주장은 강한데 근거가 약해 되물어야 할 때

2. 새 질문 — 아직 확인하지 못한 다른 주제로 넘어간다
   - 직전 답변이 이미 충분히 구체적일 때
   - 이력서에서 아직 검증하지 못한 경험·역량이 남아 있을 때

규칙:
- 이미 물어본 질문과 의미가 겹치면 안 됩니다.
- 이력서에 없는 내용을 지어내지 마세요.
- 질문은 한 문장으로 간결하게. 마크다운이나 별표를 쓰지 마세요.
- 남은 시간이 얼마 없으면 새 주제를 벌이기보다 마무리에 가깝게 물으세요.

질문 유형은 반드시 다음 넷 중 하나입니다.
{type_guide}

출력은 아래 형식의 JSON 객체만 내보내세요. 다른 텍스트는 넣지 마세요.
{{"is_follow_up": true, "question_text": "...", "question_type": "기술형"}}"""


class NextQuestionAgent:
    """이력서 + 지금까지의 대화 -> 다음 질문 하나."""

    def __init__(self, llm: Optional[Runnable] = None):
        self.llm = llm if llm is not None else get_chat_model(primary="gemini", temperature=0.4)
        self.chain = (
            ChatPromptTemplate.from_template(_TEMPLATE)
            | self.llm
            | JsonOutputParser()
        )

    def generate(
        self,
        resume: dict,
        history: list[tuple[str, str]],
        remaining_seconds: int,
    ) -> Optional[NextQuestion]:
        """history: [(질문, 답변), ...] 순서대로. 답변이 없으면 빈 문자열."""
        started = time.perf_counter()
        history_block = format_history(history)

        try:
            data = self.chain.invoke({
                "resume": resume,
                "history": history_block,
                "remaining_minutes": max(0, round(remaining_seconds / 60)),
                "type_guide": _TYPE_GUIDE,
            })
        except Exception:
            logger.warning("다음 질문 생성 실패 — 면접을 마무리한다", exc_info=True)
            return None

        result = _normalize(data)

        # 대화가 길어질수록 프롬프트가 커진다. 정말 느려지는지 로그로 지켜본다.
        # (출력 길이는 안 변하므로 이론상 거의 안 늘어야 한다)
        logger.info(
            "다음 질문 생성: %.1f초 | 문항 %d개까지의 대화, 프롬프트 %d자 | 꼬리질문=%s",
            time.perf_counter() - started,
            len(history),
            len(history_block),
            result.is_follow_up if result else "실패",
        )
        return result


def format_history(history: list[tuple[str, str]]) -> str:
    if not history:
        return "(아직 없음)"
    return "\n\n".join(
        f"질문 {i}: {q}\n답변 {i}: {a or '(답변 없음)'}"
        for i, (q, a) in enumerate(history, start=1)
    )


def _normalize(data: Any) -> Optional[NextQuestion]:
    """LLM 응답을 NextQuestion 또는 None 으로 강제한다."""
    if not isinstance(data, dict):
        logger.warning("다음 질문 응답이 객체가 아님: %r", type(data).__name__)
        return None

    text = _clean(data.get("question_text") or "")
    if not text:
        logger.warning("생성된 질문이 비어 있음 — 무시한다")
        return None

    return NextQuestion(
        question_text=text,
        question_type=_coerce_type(data.get("question_type"), context="다음 질문"),
        is_follow_up=bool(data.get("is_follow_up")),
    )
