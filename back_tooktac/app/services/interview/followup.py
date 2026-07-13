"""꼬리질문 에이전트 (실전 면접 전용).

직전 답변을 읽고 파고들 지점이 있으면 꼬리질문을 만든다. 없으면 만들지 않는다.

이 에이전트는 사용자를 기다리게 한다. 답변이 끝나고 다음 질문이 뜨기까지의
준비 시간(10초) 안에 STT + 이 호출이 모두 끝나야 면접이 안 끊긴다.
그래서 두 가지를 지킨다.

  1) LLM을 부를 가치가 없는 답변(너무 짧거나 STT 실패)은 호출 자체를 건너뛴다.
  2) 실패하면 예외를 던지지 않고 "꼬리질문 없음"으로 답한다.
     꼬리질문은 있으면 좋은 것이지, 없다고 면접이 멈춰선 안 된다.
"""
import logging
from typing import Any, NamedTuple, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.services.interview.question_generator import _TYPE_GUIDE, _clean, _coerce_type
from app.services.llm import get_chat_model

logger = logging.getLogger(__name__)

# 이보다 짧은 답변은 파고들 내용이 없다. LLM을 부르지 않는다 (시간·비용).
MIN_ANSWER_CHARS = 30


class FollowUp(NamedTuple):
    question_text: str
    question_type: str


_TEMPLATE = """당신은 경험 많은 기술 면접관입니다.
지원자의 답변을 듣고, 더 파고들 가치가 있으면 꼬리질문을 하나만 만드세요.

방금 한 질문: {question}
지원자의 답변: {answer}

꼬리질문을 만들어야 하는 경우:
- 답변이 추상적이어서 구체적인 사례나 수치를 물어야 할 때
- 답변에 나온 기술·선택의 근거를 물어야 할 때
- 답변에 흥미로운 지점이 있어 더 깊이 확인할 가치가 있을 때

꼬리질문을 만들지 말아야 하는 경우:
- 답변이 이미 충분히 구체적일 때
- 답변이 질문과 동떨어져 있거나 내용이 없을 때
- 같은 것을 되묻게 될 때

질문 유형은 반드시 다음 넷 중 하나입니다.
{type_guide}

출력은 아래 형식의 JSON 객체만 내보내세요. 다른 텍스트는 넣지 마세요.
꼬리질문이 필요 없으면 {{"follow_up": false}} 만 내보내세요.
{{"follow_up": true, "question_text": "...", "question_type": "기술형"}}"""


class FollowUpQuestionAgent:
    """직전 답변에 대한 꼬리질문을 만든다. 필요 없으면 None."""

    def __init__(self, llm: Optional[Runnable] = None):
        self.llm = llm if llm is not None else get_chat_model(primary="gemini", temperature=0.3)
        self.chain = (
            ChatPromptTemplate.from_template(_TEMPLATE)
            | self.llm
            | JsonOutputParser()
        )

    def generate(self, question_text: str, answer_text: str) -> Optional[FollowUp]:
        answer = _clean(answer_text)
        if len(answer) < MIN_ANSWER_CHARS:
            logger.info("답변이 짧아 꼬리질문을 만들지 않는다 (%d자)", len(answer))
            return None

        try:
            data = self.chain.invoke({
                "question": _clean(question_text),
                "answer": answer,
                "type_guide": _TYPE_GUIDE,
            })
        except Exception:
            # 면접을 멈추느니 꼬리질문을 포기한다.
            logger.warning("꼬리질문 생성 실패 — 다음 기본 질문으로 진행", exc_info=True)
            return None

        return _normalize(data)


def _normalize(data: Any) -> Optional[FollowUp]:
    """LLM 응답을 FollowUp 또는 None으로 강제한다."""
    if not isinstance(data, dict):
        logger.warning("꼬리질문 응답이 객체가 아님: %r", type(data).__name__)
        return None

    if not data.get("follow_up"):
        return None

    text = _clean(data.get("question_text") or "")
    if not text:
        # follow_up=true 인데 질문이 비었다 — 신뢰할 수 없는 응답
        logger.warning("꼬리질문이 비어 있음 — 무시한다")
        return None

    return FollowUp(
        question_text=text,
        question_type=_coerce_type(data.get("question_type"), context="꼬리질문"),
    )
