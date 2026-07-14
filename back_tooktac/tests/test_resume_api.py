"""이력서 등록/조회 API 유닛 테스트 — Gemini 구조화·질문 생성은 모킹"""
import pytest

from app.repository.resume import Resume, ResumeQuestion
from app.services.interview.plan import DEFAULT_QUESTION_TEXT
from app.services.resume.structurer import ResumeStructuringError

FAKE_STRUCTURED = {
    "skills": ["Python"],
    "education": {"major": "컴퓨터공학"},
    "career": {},
    "projects": [],
    "self_introduction": {},
    "desired_position": {},
}

FAKE_GENERATED = [
    {"question_text": "GIL을 설명해주세요.", "question_type": "개념설명형"},
    {"question_text": "FastAPI를 어떻게 썼나요?", "question_type": "기술형"},
]


class FakeStructurer:
    def structure(self, content):
        return dict(FAKE_STRUCTURED)


class FailingStructurer:
    def structure(self, content):
        raise ResumeStructuringError("mock failure")


class FakeQuestionGenerator:
    def generate(self, structured, existing=None):
        return [dict(q) for q in FAKE_GENERATED]


@pytest.fixture(autouse=True)
def mock_structurer(monkeypatch):
    monkeypatch.setattr(
        "app.services.resume.resume_service.ResumeStructurer", FakeStructurer
    )


@pytest.fixture(autouse=True)
def mock_question_generator(monkeypatch):
    monkeypatch.setattr(
        "app.services.resume.resume_service.ResumeQuestionGenerator", FakeQuestionGenerator
    )


def test_upload_resume_requires_auth(client):
    res = client.post("/resume", data={"resume_text": "텍스트"})
    assert res.status_code == 401


def test_upload_resume_creates_row_and_structures(auth_client, test_user, db_session):
    res = auth_client.post(
        "/resume",
        data={"resume_text": "저는 열정적인 개발자입니다.", "filename": "resume.pdf"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "resume_id" in body
    assert body["structured"] is True
    assert body["questions_generated"] is True

    resume = db_session.query(Resume).filter_by(user_id=test_user.id).first()
    assert resume is not None
    assert resume.content == "저는 열정적인 개발자입니다."
    assert resume.filename == "resume.pdf"
    assert resume.structured == FAKE_STRUCTURED

    # 기본 자기소개 질문 + LLM 생성 질문이 풀에 들어간다
    texts = [q.question_text for q in resume.questions]
    assert texts[0] == DEFAULT_QUESTION_TEXT
    assert resume.questions[0].is_default is True
    assert texts[1:] == [q["question_text"] for q in FAKE_GENERATED]
    assert resume.questions_generated is True


def test_upload_resume_rejects_empty_text(auth_client):
    res = auth_client.post("/resume", data={"resume_text": "   "})
    assert res.status_code == 400


def test_upload_succeeds_even_if_structuring_fails(auth_client, test_user, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.resume.resume_service.ResumeStructurer", FailingStructurer
    )

    res = auth_client.post("/resume", data={"resume_text": "저의 이력서"})
    assert res.status_code == 200
    assert res.json()["structured"] is False
    assert res.json()["questions_generated"] is False

    # 구조화 실패해도 원문은 저장되어야 함 (면접 시작 시 재시도 대상)
    resume = db_session.query(Resume).filter_by(user_id=test_user.id).first()
    assert resume.content == "저의 이력서"
    assert resume.structured is None
    # 구조화가 실패해도 기본 자기소개 질문은 항상 있어야 한다
    assert [q.question_text for q in resume.questions] == [DEFAULT_QUESTION_TEXT]
    assert resume.questions_generated is False


def test_reupload_replaces_content_and_restructures(auth_client, test_user, db_session):
    resume = Resume(
        user_id=test_user.id,
        filename="old.pdf",
        content="이전 이력서",
        structured={"skills": ["Java"]},
        questions_generated=True,
    )
    resume.questions.append(ResumeQuestion(
        question_text="옛 이력서 기반 질문", question_type="기술형", is_default=False, sort_order=1,
    ))
    db_session.add(resume)
    db_session.commit()
    old_question_id = resume.questions[0].id

    res = auth_client.post("/resume", data={"resume_text": "새 이력서", "filename": "new.pdf"})
    assert res.status_code == 200

    rows = db_session.query(Resume).filter_by(user_id=test_user.id).all()
    assert len(rows) == 1  # 업서트: 행이 늘어나지 않아야 함
    db_session.refresh(rows[0])
    assert rows[0].content == "새 이력서"
    assert rows[0].filename == "new.pdf"
    assert rows[0].structured == FAKE_STRUCTURED  # 새 원문 기준으로 재구조화

    # 옛 질문은 사라지고, 자기소개 + 새로 생성된 질문만 남는다
    assert db_session.get(ResumeQuestion, old_question_id) is None
    texts = [q.question_text for q in rows[0].questions]
    assert texts[0] == DEFAULT_QUESTION_TEXT
    assert "옛 이력서 기반 질문" not in texts
    assert texts[1:] == [q["question_text"] for q in FAKE_GENERATED]


def test_resume_status_reflects_registration(auth_client, test_user, db_session):
    res = auth_client.get("/resume/status")
    assert res.status_code == 200
    assert res.json()["has_resume"] is False
    assert res.json()["has_cover_letter"] is False
    assert res.json()["ready_for_career_diagnosis"] is False

    auth_client.post("/resume", data={"resume_text": "저의 이력서와 자기소개서입니다. 지원동기는 개발 경험입니다."})

    res = auth_client.get("/resume/status")
    assert res.json()["has_resume"] is True
    assert res.json()["has_cover_letter"] is False
    assert res.json()["ready_for_career_diagnosis"] is False


def test_list_questions_without_resume_returns_400(auth_client):
    res = auth_client.get("/resume/questions")
    assert res.status_code == 400
    assert "이력서" in res.json()["detail"]
