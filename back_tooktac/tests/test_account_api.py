"""계정 관리 API 테스트"""
from datetime import date, datetime

from app.core.password import hash_password, is_bcrypt_hash, verify_password
from app.repository.career import CoverLetter, JobGroup
from app.repository.resume import Resume
from app.repository.user import InterviewSchedule, User


def test_account_requires_auth(client):
    res = client.get("/account")
    assert res.status_code == 401


def test_account_returns_current_user_profile(auth_client, test_user):
    res = auth_client.get("/account")

    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == test_user.id
    assert body["username"] == test_user.username
    assert body["nickname"] == test_user.nickname
    assert body["email"] == test_user.email
    assert body["desired_job"] == test_user.desired_job


def test_change_password_hashes_new_password_and_updates_login(
    auth_client,
    client,
    db_session,
    test_user,
):
    res = auth_client.patch(
        "/account/password",
        json={"current_password": "pw1234", "new_password": "new-password-123"},
    )

    assert res.status_code == 200
    db_session.refresh(test_user)
    assert test_user.password != "new-password-123"
    assert is_bcrypt_hash(test_user.password)
    assert verify_password("new-password-123", test_user.password)

    assert client.post("/login", data={"username": "tester", "password": "pw1234"}).status_code == 401
    assert client.post(
        "/login",
        data={"username": "tester", "password": "new-password-123"},
    ).status_code == 200


def test_change_password_rejects_wrong_current_password(auth_client):
    res = auth_client.patch(
        "/account/password",
        json={"current_password": "wrong", "new_password": "new-password-123"},
    )

    assert res.status_code == 400
    assert "현재 비밀번호" in res.json()["detail"]


def test_change_password_rejects_same_password(auth_client, db_session, test_user):
    test_user.password = hash_password("same-password-123")
    db_session.commit()

    res = auth_client.patch(
        "/account/password",
        json={"current_password": "same-password-123", "new_password": "same-password-123"},
    )

    assert res.status_code == 400
    assert "새 비밀번호" in res.json()["detail"]


def test_delete_account_removes_user_resume_cover_letter_and_schedule(auth_client, db_session, test_user):
    user_id = test_user.id
    username = test_user.username
    job_group = JobGroup(name="dev-test", description="test", is_active=True)
    db_session.add(job_group)
    db_session.flush()

    db_session.add_all(
        [
            Resume(user_id=user_id, filename="resume.pdf", content="이력서 내용"),
            CoverLetter(
                user_id=user_id,
                job_group_id=job_group.id,
                title="삭제될 자소서",
                question_text="질문",
                answer_text="답변",
            ),
            InterviewSchedule(
                user_id=username,
                scheduled_at=datetime.combine(date.today(), datetime.min.time()),
                description="삭제될 면접 일정",
            ),
        ]
    )
    db_session.commit()

    res = auth_client.delete("/account")

    assert res.status_code == 200
    set_cookie = res.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower()

    assert db_session.query(User).filter_by(id=user_id).first() is None
    assert db_session.query(Resume).filter_by(user_id=user_id).first() is None
    assert db_session.query(CoverLetter).filter_by(user_id=user_id).first() is None
    assert db_session.query(InterviewSchedule).filter_by(user_id=username).first() is None
    assert auth_client.get("/me").status_code == 401
