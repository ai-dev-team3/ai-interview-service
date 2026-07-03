"""이력서 등록/조회 API 유닛 테스트 — Gemini 구조화는 모킹"""
import pytest

from app.repository.resume import Resume
from app.services.resume.structurer import ResumeStructuringError

FAKE_STRUCTURED = {
    "skills": ["Python"],
    "education": {"major": "컴퓨터공학"},
    "career": {},
    "projects": [],
    "self_introduction": {},
    "desired_position": {},
}


class FakeStructurer:
    def structure(self, content):
        return dict(FAKE_STRUCTURED)


class FailingStructurer:
    def structure(self, content):
        raise ResumeStructuringError("mock failure")


@pytest.fixture(autouse=True)
def mock_structurer(monkeypatch):
    monkeypatch.setattr(
        "app.services.resume.resume_service.ResumeStructurer", FakeStructurer
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

    resume = db_session.query(Resume).filter_by(user_id=test_user.id).first()
    assert resume is not None
    assert resume.content == "저는 열정적인 개발자입니다."
    assert resume.filename == "resume.pdf"
    assert resume.structured == FAKE_STRUCTURED


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

    # 구조화 실패해도 원문은 저장되어야 함 (면접 시작 시 재시도 대상)
    resume = db_session.query(Resume).filter_by(user_id=test_user.id).first()
    assert resume.content == "저의 이력서"
    assert resume.structured is None


def test_reupload_replaces_content_and_restructures(auth_client, test_user, db_session):
    db_session.add(Resume(
        user_id=test_user.id,
        filename="old.pdf",
        content="이전 이력서",
        structured={"skills": ["Java"]},
    ))
    db_session.commit()

    res = auth_client.post("/resume", data={"resume_text": "새 이력서", "filename": "new.pdf"})
    assert res.status_code == 200

    rows = db_session.query(Resume).filter_by(user_id=test_user.id).all()
    assert len(rows) == 1  # 업서트: 행이 늘어나지 않아야 함
    db_session.refresh(rows[0])
    assert rows[0].content == "새 이력서"
    assert rows[0].filename == "new.pdf"
    assert rows[0].structured == FAKE_STRUCTURED  # 새 원문 기준으로 재구조화


def test_resume_status_reflects_registration(auth_client, test_user, db_session):
    res = auth_client.get("/resume/status")
    assert res.status_code == 200
    assert res.json()["has_resume"] is False

    auth_client.post("/resume", data={"resume_text": "저의 이력서입니다."})

    res = auth_client.get("/resume/status")
    assert res.json()["has_resume"] is True


def test_start_interview_without_resume_returns_400(auth_client):
    res = auth_client.post("/start-interview")
    assert res.status_code == 400
    assert "이력서" in res.json()["detail"]
