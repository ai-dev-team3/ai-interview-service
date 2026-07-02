"""면접 질문 생성 API 유닛 테스트 — Gemini 호출은 모킹"""
import pytest

from app.repository.interview import InterviewQuestion, InterviewSession


class FakeQuestionGenerator:
    """InterviewQuestionGenerator를 대체하는 목 — 네트워크 호출 없음"""

    def load_structured_from_db(self, db, user_id):
        return {"structured_content": {"skills": ["Python"], "education": {}}}

    def generate_conceptual_question(self, parsed):
        return {"question": "개념 질문입니다", "question_type": "개념설명형"}

    def generate_technical_question(self, parsed):
        return {"question": "기술 질문입니다", "question_type": "기술형"}

    def generate_followup_resume_question(self, parsed, q1, a1, q2, a2):
        return {"question": "꼬리 질문입니다", "question_type": "개념설명형"}

    def generate_situational_question(self, parsed):
        return {"question": "상황 질문입니다", "question_type": "상황형"}

    def generate_behavioral_question(self, parsed):
        return {"question": "행동 질문입니다", "question_type": "행동형"}

    def generate_followup_coverletter_question(self, parsed, q4, a4, q5, a5):
        return {"question": "자소서 꼬리 질문입니다", "question_type": "상황형"}


@pytest.fixture(autouse=True)
def mock_generator(monkeypatch):
    monkeypatch.setattr(
        "app.api.interview.InterviewQuestionGenerator", FakeQuestionGenerator
    )


def test_start_interview_creates_session_and_q1(auth_client, db_session, test_user):
    res = auth_client.post("/start-interview")
    assert res.status_code == 200
    body = res.json()
    assert body["question"] == "개념 질문입니다"

    session = db_session.query(InterviewSession).filter_by(user_id=test_user.id).first()
    assert session is not None
    q1 = db_session.query(InterviewQuestion).filter_by(
        session_id=session.id, question_order=1
    ).first()
    assert q1 is not None
    assert q1.question_type == "개념설명형"


def test_generate_question_order2(auth_client, db_session, test_user):
    auth_client.post("/start-interview")

    res = auth_client.post("/generate-question/2")
    assert res.status_code == 200
    assert res.json()["question"] == "기술 질문입니다"

    session = db_session.query(InterviewSession).filter_by(user_id=test_user.id).first()
    q2 = db_session.query(InterviewQuestion).filter_by(
        session_id=session.id, question_order=2
    ).first()
    assert q2 is not None


def test_generate_question_invalid_order_400(auth_client):
    auth_client.post("/start-interview")
    res = auth_client.post("/generate-question/7")
    assert res.status_code == 400


def test_generate_question_without_session_404(auth_client):
    res = auth_client.post("/generate-question/2")
    assert res.status_code == 404


def test_start_interview_requires_auth(client):
    res = client.post("/start-interview")
    assert res.status_code == 401
