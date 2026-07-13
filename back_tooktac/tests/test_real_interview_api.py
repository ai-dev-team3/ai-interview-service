"""실전 면접 API 테스트 — STT·LLM은 전부 페이크.

고정하려는 성질:
  - 서버가 질문을 정한다. 응답에 다음 질문이 하나만 담긴다(미리 다 주지 않는다).
  - 꼬리질문이 붙으면 총 문항 수 안에서 기본 질문을 밀어낸다 (상한 7).
  - 분석이 실패해도 결과 행은 남는다 — 안 그러면 마지막 대기 화면이 안 끝난다.
"""
import io

import pytest

from app.repository.interview import InterviewQuestion, InterviewSession
from app.repository.resume import Resume, ResumeQuestion
from app.services.interview.followup import FollowUp
from app.services.interview.plan import (
    DEFAULT_QUESTION_TEXT,
    MAX_INTERVIEW_QUESTIONS,
    MODE_REAL,
)


@pytest.fixture()
def real_app(test_app, db_session):
    from app.api.real_interview import router as real_router

    test_app.include_router(real_router)
    return test_app


@pytest.fixture()
def real_client(real_app, test_user):
    from fastapi.testclient import TestClient

    from app.core.security import create_access_token

    client = TestClient(real_app)
    client.cookies.set("access_token", create_access_token(test_user.id))
    return client


@pytest.fixture()
def resume_pool(db_session, test_user):
    """자기소개 + 풀 질문 8개 (상한 7보다 많게 두어 '고른다'를 확인한다)"""
    resume = Resume(user_id=test_user.id, content="이력서 원문", structured={"skills": []})
    db_session.add(resume)
    db_session.flush()

    db_session.add(ResumeQuestion(
        resume_id=resume.id,
        question_text=DEFAULT_QUESTION_TEXT,
        question_type="행동형",
        is_default=True,
    ))
    for i in range(8):
        db_session.add(ResumeQuestion(
            resume_id=resume.id,
            question_text=f"풀 질문 {i}",
            question_type="기술형",
            is_default=False,
        ))
    db_session.commit()
    return resume


@pytest.fixture(autouse=True)
def fake_analysis(monkeypatch):
    """STT/변환/평가를 전부 가짜로. 기본은 꼬리질문 없음."""
    from app.services.speech import answer_pipeline

    async def fake_convert(self, webm, wav):
        return None

    async def fake_transcribe(self, wav):
        return "구체적인 사례를 들어 답변드리자면 결제 시스템을 만든 경험이 있습니다", {"segments": []}

    async def fake_analyze(self, *args, **kwargs):
        return ({"labels": {}, "score_detail": {}, "total_score": 80}, {"final_score": 70})

    monkeypatch.setattr(answer_pipeline.AnswerAnalysisPipeline, "convert_webm_to_wav", fake_convert)
    monkeypatch.setattr(answer_pipeline.AnswerAnalysisPipeline, "transcribe", fake_transcribe)
    monkeypatch.setattr(answer_pipeline.AnswerAnalysisPipeline, "analyze_and_evaluate", fake_analyze)

    from app.services.interview.followup import FollowUpQuestionAgent

    monkeypatch.setattr(FollowUpQuestionAgent, "generate", lambda self, q, a: None)


def _no_followup(monkeypatch):
    from app.services.interview.followup import FollowUpQuestionAgent

    monkeypatch.setattr(FollowUpQuestionAgent, "generate", lambda self, q, a: None)


def _always_followup(monkeypatch):
    from app.services.interview.followup import FollowUpQuestionAgent

    monkeypatch.setattr(
        FollowUpQuestionAgent,
        "generate",
        lambda self, q, a: FollowUp(question_text=f"[꼬리] {q}", question_type="기술형"),
    )


def _answer(client, session_id, order):
    return client.post(
        "/real-interview/answer",
        params={"session_id": session_id, "question_order": order},
        files={"audio": ("a.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
    )


def test_시작하면_첫_질문만_준다(real_client, resume_pool):
    res = real_client.post("/real-interview/start")

    assert res.status_code == 200
    body = res.json()
    assert body["question"]["question_order"] == 1
    assert body["question"]["question_text"] == DEFAULT_QUESTION_TEXT  # 자기소개가 항상 1번
    assert body["max_questions"] == MAX_INTERVIEW_QUESTIONS
    assert body["prepare_seconds"] == 10
    assert body["answer_seconds"] == 90
    assert "questions" not in body, "질문 목록을 통째로 주면 실전이 아니다"


def test_이력서가_없으면_시작할_수_없다(real_client):
    res = real_client.post("/real-interview/start")

    assert res.status_code == 400
    assert "이력서" in res.json()["detail"]


def test_답변하면_다음_질문이_온다(real_client, resume_pool, db_session):
    start = real_client.post("/real-interview/start").json()

    res = _answer(real_client, start["session_id"], 1)

    assert res.status_code == 200
    body = res.json()
    assert body["finished"] is False
    assert body["question"]["question_order"] == 2
    assert body["is_follow_up"] is False
    assert body["transcript"]


def test_꼬리질문이_붙으면_그_질문이_다음으로_온다(real_client, resume_pool, monkeypatch):
    _always_followup(monkeypatch)
    start = real_client.post("/real-interview/start").json()

    body = _answer(real_client, start["session_id"], 1).json()

    assert body["is_follow_up"] is True
    assert body["question"]["question_text"].startswith("[꼬리]")
    assert body["question"]["question_order"] == 2


def test_총_7문항을_넘지_않는다(real_client, resume_pool, db_session, monkeypatch):
    """풀에 9개(자기소개+8)가 있어도 7문항에서 끝나야 한다."""
    _no_followup(monkeypatch)
    session_id = real_client.post("/real-interview/start").json()["session_id"]

    order = 1
    while True:
        body = _answer(real_client, session_id, order).json()
        if body["finished"]:
            break
        order = body["question"]["question_order"]
        assert order <= MAX_INTERVIEW_QUESTIONS

    asked = db_session.query(InterviewQuestion).filter_by(session_id=session_id).count()
    assert asked == MAX_INTERVIEW_QUESTIONS


def test_꼬리질문도_문항_수에_포함된다(real_client, resume_pool, db_session, monkeypatch):
    """꼬리질문이 매번 붙어도 총 7문항. 그만큼 기본 질문을 덜 묻는다."""
    _always_followup(monkeypatch)
    session_id = real_client.post("/real-interview/start").json()["session_id"]

    order = 1
    follow_ups = 0
    while True:
        body = _answer(real_client, session_id, order).json()
        if body["finished"]:
            break
        if body["is_follow_up"]:
            follow_ups += 1
        order = body["question"]["question_order"]

    questions = (
        db_session.query(InterviewQuestion)
        .filter_by(session_id=session_id)
        .order_by(InterviewQuestion.question_order)
        .all()
    )
    assert len(questions) == MAX_INTERVIEW_QUESTIONS
    assert follow_ups > 0
    # 꼬리질문이 붙은 만큼 풀 질문은 덜 나왔다
    pool_asked = sum(1 for q in questions if not q.question_text.startswith("[꼬리]"))
    assert pool_asked == MAX_INTERVIEW_QUESTIONS - follow_ups


def test_남의_세션에는_답변할_수_없다(real_client, resume_pool, db_session):
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

    res = _answer(real_client, other.id, 1)

    assert res.status_code == 404


def test_연습_세션은_실전_API로_접근할_수_없다(real_client, resume_pool, db_session, test_user):
    practice = InterviewSession(user_id=test_user.id, mode="practice")
    db_session.add(practice)
    db_session.commit()

    res = real_client.get("/real-interview/analysis-status", params={"session_id": practice.id})

    assert res.status_code == 404
