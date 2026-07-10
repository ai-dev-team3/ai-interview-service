"""연습 면접 시작/조회 API 테스트 — LLM 호출은 모킹"""
import datetime

import pytest

from app.repository.interview import InterviewQuestion, InterviewSession
from app.repository.resume import Resume, ResumeQuestion
from app.repository.user import User
from app.services.interview.plan import (
    DEFAULT_QUESTION_TEXT,
    DEFAULT_QUESTION_TYPE,
    MAX_INTERVIEW_QUESTIONS,
)


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    """질문 풀이 이미 채워져 있으므로 생성기가 불릴 일이 없어야 한다."""
    class Boom:
        def generate(self, *a, **k):
            raise AssertionError("질문이 이미 있는데 생성기가 호출되었다")

    monkeypatch.setattr("app.services.resume.resume_service.ResumeQuestionGenerator", Boom)


@pytest.fixture
def pool(db_session, test_user):
    """자기소개 1개 + 일반 질문 8개가 든 질문 풀"""
    resume = Resume(user_id=test_user.id, content="이력서 원문",
                    structured={"skills": []}, questions_generated=True)
    resume.questions.append(ResumeQuestion(
        question_text=DEFAULT_QUESTION_TEXT, question_type=DEFAULT_QUESTION_TYPE,
        is_default=True, sort_order=0,
    ))
    for i in range(1, 9):
        resume.questions.append(ResumeQuestion(
            question_text=f"질문 {i}", question_type="기술형", is_default=False, sort_order=i,
        ))
    db_session.add(resume)
    db_session.commit()
    return resume


def _ids(pool, *indexes):
    """pool.questions는 [자기소개, 질문1, ..., 질문8] 순"""
    return [pool.questions[i].id for i in indexes]


def test_start_requires_auth(client):
    assert client.post("/start-interview", json={"question_ids": []}).status_code == 401


def test_start_creates_session_and_snapshots_questions(auth_client, pool, db_session, test_user):
    body = auth_client.post("/start-interview", json={"question_ids": _ids(pool, 3, 1)}).json()

    assert body["total_questions"] == 3
    assert [q["question_order"] for q in body["questions"]] == [1, 2, 3]
    # 자기소개가 언제나 1번
    assert body["questions"][0]["question_text"] == DEFAULT_QUESTION_TEXT
    # 나머지는 요청한 순서대로
    assert body["questions"][1]["question_text"] == "질문 3"
    assert body["questions"][2]["question_text"] == "질문 1"

    session = db_session.get(InterviewSession, body["session_id"])
    assert session.user_id == test_user.id
    rows = (db_session.query(InterviewQuestion)
            .filter_by(session_id=session.id)
            .order_by(InterviewQuestion.question_order).all())
    assert [r.question_order for r in rows] == [1, 2, 3]
    assert rows[0].question_type == DEFAULT_QUESTION_TYPE


def test_start_inserts_default_even_when_not_requested(auth_client, pool):
    body = auth_client.post("/start-interview", json={"question_ids": _ids(pool, 1)}).json()
    assert body["total_questions"] == 2
    assert body["questions"][0]["question_text"] == DEFAULT_QUESTION_TEXT


def test_start_does_not_duplicate_default_when_requested(auth_client, pool):
    body = auth_client.post("/start-interview", json={"question_ids": _ids(pool, 0, 1)}).json()
    texts = [q["question_text"] for q in body["questions"]]
    assert texts == [DEFAULT_QUESTION_TEXT, "질문 1"]


def test_start_with_only_default_is_allowed(auth_client, pool):
    body = auth_client.post("/start-interview", json={"question_ids": []}).json()
    assert body["total_questions"] == 1
    assert body["questions"][0]["question_text"] == DEFAULT_QUESTION_TEXT


def test_start_rejects_more_than_max(auth_client, pool):
    # 자기소개(1) + 일반 7개 = 8 > 7
    res = auth_client.post("/start-interview", json={"question_ids": _ids(pool, 1, 2, 3, 4, 5, 6, 7)})
    assert res.status_code == 400
    assert str(MAX_INTERVIEW_QUESTIONS) in res.json()["detail"]


def test_start_accepts_exactly_max(auth_client, pool):
    # 자기소개(1) + 일반 6개 = 7
    body = auth_client.post("/start-interview", json={"question_ids": _ids(pool, 1, 2, 3, 4, 5, 6)}).json()
    assert body["total_questions"] == MAX_INTERVIEW_QUESTIONS


def test_start_rejects_unknown_question_id(auth_client, pool):
    res = auth_client.post("/start-interview", json={"question_ids": [999999]})
    assert res.status_code == 400
    assert "찾을 수 없습니다" in res.json()["detail"]


def test_start_rejects_duplicate_selection(auth_client, pool):
    ids = _ids(pool, 1)
    res = auth_client.post("/start-interview", json={"question_ids": ids + ids})
    assert res.status_code == 400
    assert "중복" in res.json()["detail"]


def test_start_rejects_other_users_question(auth_client, pool, db_session):
    other = User(username="o", password="p", name="n", email="o@e.com", nickname="o",
                 birthdate=datetime.date(2000, 1, 1), desired_job="백엔드")
    db_session.add(other)
    db_session.flush()
    other_resume = Resume(user_id=other.id, content="남의 이력서")
    other_resume.questions.append(ResumeQuestion(
        question_text="남의 질문", question_type="기술형", is_default=False, sort_order=1,
    ))
    db_session.add(other_resume)
    db_session.commit()

    res = auth_client.post("/start-interview", json={"question_ids": [other_resume.questions[0].id]})
    assert res.status_code == 400


def test_start_without_resume_returns_400(auth_client):
    res = auth_client.post("/start-interview", json={"question_ids": []})
    assert res.status_code == 400
    assert "이력서" in res.json()["detail"]


def test_interview_question_is_a_snapshot(auth_client, pool, db_session):
    """면접 시작 후 풀의 질문을 고쳐도 세션의 질문은 그대로여야 한다."""
    body = auth_client.post("/start-interview", json={"question_ids": _ids(pool, 1)}).json()

    pool.questions[1].question_text = "완전히 다른 질문"
    db_session.commit()

    row = (db_session.query(InterviewQuestion)
           .filter_by(session_id=body["session_id"], question_order=2).one())
    assert row.question_text == "질문 1"


def test_get_session_questions_returns_saved_order(auth_client, pool):
    started = auth_client.post("/start-interview", json={"question_ids": _ids(pool, 2, 1)}).json()

    body = auth_client.get("/interview/questions").json()
    assert body["session_id"] == started["session_id"]
    assert [q["question_text"] for q in body["questions"]] == [
        DEFAULT_QUESTION_TEXT, "질문 2", "질문 1",
    ]


def test_get_session_questions_without_session_404(auth_client):
    assert auth_client.get("/interview/questions").status_code == 404
