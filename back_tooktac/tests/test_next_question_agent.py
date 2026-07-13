"""다음 질문 에이전트 — LLM 은 가짜로 대체한다.

에이전트는 하나뿐이고 호출도 답변당 한 번이다. "꼬리질문을 할지 새 주제로 넘어갈지"와
"그 질문의 내용"을 한 번에 정한다. 라우팅과 생성을 나누면 호출이 두 번이 되는데,
준비 시간(10초) 안에 STT 까지 끝나야 하므로 그럴 예산이 없다.

이 호출은 사용자를 기다리게 한다. 그래서 "실패해도 면접이 멈추지 않는다"가
가장 중요한 성질이다.
"""
from langchain_core.runnables import RunnableLambda

from app.services.interview.next_question import (
    NextQuestionAgent,
    _normalize,
    format_history,
)
from app.services.interview.plan import FALLBACK_QUESTION_TYPE

RESUME = {"skills": ["Python"], "career": {"status": "신입"}}
HISTORY = [("1분 자기소개 부탁드립니다.", "결제 시스템을 만든 경험이 있습니다.")]


def _agent(payload=None, exc=None):
    def run(_):
        if exc is not None:
            raise exc
        return payload

    agent = NextQuestionAgent(llm=RunnableLambda(run))
    agent.chain = RunnableLambda(run)
    return agent


def test_꼬리질문을_만든다():
    agent = _agent({
        "is_follow_up": True,
        "question_text": "낙관적 락을 고른 이유가 무엇인가요?",
        "question_type": "기술형",
    })

    result = agent.generate(RESUME, HISTORY, remaining_seconds=400)

    assert result.question_text == "낙관적 락을 고른 이유가 무엇인가요?"
    assert result.question_type == "기술형"
    assert result.is_follow_up is True


def test_새_주제로_넘어간다():
    agent = _agent({
        "is_follow_up": False,
        "question_text": "팀 협업에서 갈등을 해결한 경험이 있나요?",
        "question_type": "행동형",
    })

    result = agent.generate(RESUME, HISTORY, remaining_seconds=400)

    assert result.is_follow_up is False


def test_LLM이_죽어도_면접이_멈추지_않는다():
    """None 을 돌려주면 호출부가 마무리 질문으로 넘어간다. 예외를 던지면 면접이 멈춘다."""
    agent = _agent(exc=RuntimeError("gemini 503"))

    assert agent.generate(RESUME, HISTORY, remaining_seconds=400) is None


def test_이상한_유형은_폴백한다():
    """채점 가중치가 question_type 에 의존하므로 목록 밖 값이 새면 안 된다."""
    agent = _agent({
        "is_follow_up": False,
        "question_text": "더 설명해주세요",
        "question_type": "심층질문형",  # 존재하지 않는 유형
    })

    result = agent.generate(RESUME, HISTORY, remaining_seconds=400)

    assert result.question_type == FALLBACK_QUESTION_TYPE


def test_질문이_비면_무시한다():
    assert _normalize({"is_follow_up": True, "question_text": "   "}) is None
    assert _normalize({"is_follow_up": True}) is None


def test_응답이_객체가_아니면_무시한다():
    assert _normalize(["아무거나"]) is None
    assert _normalize(None) is None


def test_대화_기록이_프롬프트에_들어간다():
    """이미 물어본 질문이 프롬프트에 있어야 중복을 피한다."""
    block = format_history([
        ("1분 자기소개 부탁드립니다.", "안녕하세요"),
        ("결제 경험을 말해주세요", "낙관적 락을 썼습니다"),
    ])

    assert "1분 자기소개" in block
    assert "결제 경험" in block
    assert "낙관적 락" in block


def test_답변이_없으면_그렇게_표시한다():
    block = format_history([("질문", "")])

    assert "(답변 없음)" in block
