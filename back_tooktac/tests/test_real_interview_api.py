"""실전 면접 API — STT·LLM 은 전부 페이크.

고정하려는 성질:
  - 첫 질문은 자기소개로 고정이고 LLM 을 부르지 않는다 (시작이 즉시다).
  - 질문은 이력서 풀이 아니라 매번 LLM 이 만든다. 지금까지의 대화가 프롬프트에 들어간다.
  - 문항 수가 아니라 '시간'이 기준이다. 10분이 지나면 마무리 질문으로 간다.
  - 마무리 답변은 채점하지 않는다 — 질문 행도 결과 행도 만들지 않고 전사만 남긴다.
  - LLM 이 죽어도 면접은 멈추지 않는다 (마무리로 끝낸다).
"""
import io
from datetime import timedelta

import pytest

from app.repository.interview import InterviewQuestion, InterviewSession
from app.repository.resume import Resume
from app.services.interview.next_question import NextQuestion
from app.services.interview.plan import (
    CLOSING_QUESTION_TEXT,
    DEFAULT_QUESTION_TEXT,
    MODE_REAL,
    REAL_TIME_BUDGET_SECONDS,
)
from app.utils.time_utils import utcnow_naive


@pytest.fixture()
def real_client(test_app, test_user):
    from fastapi.testclient import TestClient

    from app.api.real_interview import router as real_router
    from app.core.security import create_access_token

    test_app.include_router(real_router)
    client = TestClient(test_app)
    client.cookies.set("access_token", create_access_token(test_user.id))
    return client


@pytest.fixture()
def resume(db_session, test_user):
    r = Resume(user_id=test_user.id, content="이력서 원문", structured={"skills": ["Python"]})
    db_session.add(r)
    db_session.commit()
    return r


@pytest.fixture(autouse=True)
def fake_pipeline(monkeypatch):
    from app.services.speech import answer_pipeline

    async def fake_convert(self, webm, wav):
        return None

    async def fake_transcribe(self, wav):
        return "구체적인 사례를 들자면 결제 시스템을 만든 경험이 있습니다", {"segments": []}

    async def fake_analyze(self, *args, **kwargs):
        return ({"labels": {}, "score_detail": {}, "total_score": 80}, {"final_score": 70})

    monkeypatch.setattr(answer_pipeline.AnswerAnalysisPipeline, "convert_webm_to_wav", fake_convert)
    monkeypatch.setattr(answer_pipeline.AnswerAnalysisPipeline, "transcribe", fake_transcribe)
    monkeypatch.setattr(answer_pipeline.AnswerAnalysisPipeline, "analyze_and_evaluate", fake_analyze)


def _agent_returns(monkeypatch, result):
    from app.services.interview.next_question import NextQuestionAgent

    calls = []

    def fake(self, resume, history, remaining_seconds):
        calls.append({"history": history, "remaining": remaining_seconds})
        return result

    monkeypatch.setattr(NextQuestionAgent, "generate", fake)
    return calls


def _answer(client, session_id, order):
    return client.post(
        "/real-interview/answer",
        params={"session_id": session_id, "question_order": order},
        files={"audio": ("a.webm", io.BytesIO(b"fake"), "audio/webm")},
    )


def _closing(client, session_id):
    return client.post(
        "/real-interview/closing",
        params={"session_id": session_id},
        files={"audio": ("c.webm", io.BytesIO(b"fake"), "audio/webm")},
    )


def test_첫_질문은_자기소개로_고정이다(real_client, resume, monkeypatch):
    """LLM 을 부르지 않으므로 시작이 즉시다."""
    calls = _agent_returns(monkeypatch, None)

    body = real_client.post("/real-interview/start").json()

    assert body["question"]["question_order"] == 1
    assert body["question"]["question_text"] == DEFAULT_QUESTION_TEXT
    assert calls == [], "첫 질문에 LLM 을 불렀다"
    assert "max_questions" not in body, "문항 수가 아니라 시간이 기준이다"


def test_이력서가_없으면_시작할_수_없다(real_client):
    res = real_client.post("/real-interview/start")

    assert res.status_code == 400
    assert "이력서" in res.json()["detail"]


def test_다음_질문은_LLM이_만든다(real_client, resume, monkeypatch):
    calls = _agent_returns(
        monkeypatch,
        NextQuestion(question_text="왜 그 선택을 했나요?", question_type="기술형", is_follow_up=True),
    )
    session_id = real_client.post("/real-interview/start").json()["session_id"]

    body = _answer(real_client, session_id, 1).json()

    assert body["question"]["question_text"] == "왜 그 선택을 했나요?"
    assert body["question"]["is_follow_up"] is True
    assert body["closing"] is False

    # 지금까지의 대화가 프롬프트로 들어가야 중복을 피할 수 있다
    assert len(calls) == 1
    history = calls[0]["history"]
    assert history[0][0] == DEFAULT_QUESTION_TEXT
    assert "결제 시스템" in history[0][1]


def test_시간이_다_되면_마무리_질문으로_간다(real_client, resume, db_session, monkeypatch):
    _agent_returns(
        monkeypatch,
        NextQuestion(question_text="다음 질문", question_type="기술형", is_follow_up=False),
    )
    session_id = real_client.post("/real-interview/start").json()["session_id"]

    # 세션이 10분 전에 시작한 것으로 되돌린다
    session = db_session.query(InterviewSession).filter_by(id=session_id).first()
    session.started_at = utcnow_naive() - timedelta(seconds=REAL_TIME_BUDGET_SECONDS + 1)
    db_session.commit()

    body = _answer(real_client, session_id, 1).json()

    assert body["closing"] is True
    assert body["closing_question"] == CLOSING_QUESTION_TEXT
    assert body["question"] is None


def test_LLM이_죽어도_면접이_멈추지_않는다(real_client, resume, monkeypatch):
    """질문을 못 만들면 마무리로 끝낸다. 예외를 던지면 면접이 멈춘다."""
    _agent_returns(monkeypatch, None)
    session_id = real_client.post("/real-interview/start").json()["session_id"]

    res = _answer(real_client, session_id, 1)

    assert res.status_code == 200
    assert res.json()["closing"] is True


def test_마무리_답변은_채점하지_않는다(real_client, resume, db_session, monkeypatch):
    """질문 행도 결과 행도 만들지 않는다. 전사만 세션에 남는다."""
    from app.repository.analysis import EvaluationResult

    _agent_returns(monkeypatch, None)
    session_id = real_client.post("/real-interview/start").json()["session_id"]

    questions_before = db_session.query(InterviewQuestion).filter_by(session_id=session_id).count()

    res = _closing(real_client, session_id)

    assert res.status_code == 200
    assert "결제 시스템" in res.json()["transcript"]

    db_session.expire_all()
    session = db_session.query(InterviewSession).filter_by(id=session_id).first()
    assert "결제 시스템" in session.closing_remark

    questions_after = db_session.query(InterviewQuestion).filter_by(session_id=session_id).count()
    assert questions_after == questions_before, "마무리 질문이 질문 행으로 저장됐다"

    results = db_session.query(EvaluationResult).filter_by(session_id=session_id).count()
    assert results == 0, "마무리 답변이 채점됐다"


def test_남의_세션에는_답변할_수_없다(real_client, resume, db_session):
    from datetime import date

    from app.repository.user import User

    stranger = User(
        username="stranger", password="pw", name="남", nickname="남남",
        email="stranger@example.com", birthdate=date(1999, 1, 1), desired_job="기획자",
    )
    db_session.add(stranger)
    db_session.flush()

    other = InterviewSession(user_id=stranger.id, mode=MODE_REAL)
    db_session.add(other)
    db_session.commit()

    assert _answer(real_client, other.id, 1).status_code == 404
    assert _closing(real_client, other.id).status_code == 404


def test_연습_세션은_실전_API로_접근할_수_없다(real_client, resume, db_session, test_user):
    practice = InterviewSession(user_id=test_user.id, mode="practice")
    db_session.add(practice)
    db_session.commit()

    res = real_client.get("/real-interview/analysis-status", params={"session_id": practice.id})

    assert res.status_code == 404
