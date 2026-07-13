"""꼬리질문 에이전트 테스트 — LLM은 가짜로 대체한다.

이 에이전트는 사용자를 기다리게 한다(준비 시간 10초 안에 STT + 이 호출이 끝나야 함).
그래서 "실패해도 면접은 이어진다"가 가장 중요한 성질이다. 그것부터 고정한다.
"""
from langchain_core.runnables import RunnableLambda

from app.services.interview.followup import (
    MIN_ANSWER_CHARS,
    FollowUpQuestionAgent,
    _normalize,
)
from app.services.interview.plan import FALLBACK_QUESTION_TYPE

LONG_ANSWER = "저는 결제 시스템을 만들면서 동시성 문제를 겪었고 낙관적 락으로 해결했습니다." * 2


def _agent_returning(payload):
    """체인이 payload를 그대로 뱉는 에이전트"""
    agent = FollowUpQuestionAgent(llm=RunnableLambda(lambda _: payload))
    agent.chain = RunnableLambda(lambda _: payload)
    return agent


def _agent_raising(exc):
    def boom(_):
        raise exc

    agent = FollowUpQuestionAgent(llm=RunnableLambda(boom))
    agent.chain = RunnableLambda(boom)
    return agent


def test_꼬리질문을_만든다():
    agent = _agent_returning({
        "follow_up": True,
        "question_text": "낙관적 락을 고른 이유가 무엇인가요?",
        "question_type": "기술형",
    })

    result = agent.generate("결제 경험을 말해주세요", LONG_ANSWER)

    assert result.question_text == "낙관적 락을 고른 이유가 무엇인가요?"
    assert result.question_type == "기술형"


def test_필요_없으면_None():
    agent = _agent_returning({"follow_up": False})

    assert agent.generate("질문", LONG_ANSWER) is None


def test_짧은_답변은_LLM을_부르지_않는다():
    """LLM 호출은 준비 시간 예산을 먹는다. 부를 가치가 없으면 건너뛴다."""
    called = []

    agent = FollowUpQuestionAgent(llm=RunnableLambda(lambda _: {}))
    agent.chain = RunnableLambda(lambda _: called.append(1) or {"follow_up": True})

    assert agent.generate("질문", "네.") is None
    assert agent.generate("질문", "가" * (MIN_ANSWER_CHARS - 1)) is None
    assert called == [], "짧은 답변인데 LLM을 불렀다"


def test_LLM이_죽어도_면접은_이어진다():
    """꼬리질문은 있으면 좋은 것이다. 실패가 면접을 멈춰선 안 된다."""
    agent = _agent_raising(RuntimeError("gemini 503"))

    assert agent.generate("질문", LONG_ANSWER) is None  # 예외가 아니라 None


def test_이상한_유형은_폴백한다():
    """채점 가중치가 question_type에 의존하므로 목록 밖 값이 새면 안 된다."""
    agent = _agent_returning({
        "follow_up": True,
        "question_text": "더 설명해주세요",
        "question_type": "심층질문형",  # 존재하지 않는 유형
    })

    assert agent.generate("질문", LONG_ANSWER).question_type == FALLBACK_QUESTION_TYPE


def test_follow_up이_true인데_질문이_비면_무시한다():
    assert _normalize({"follow_up": True, "question_text": "  "}) is None
    assert _normalize({"follow_up": True}) is None


def test_응답이_객체가_아니면_무시한다():
    assert _normalize(["아무거나"]) is None
    assert _normalize(None) is None
