from datetime import date

from app.repository.career import CoverLetter, JobGroup
from app.repository.user import User


def test_create_cover_letter_requires_auth(client, db_session):
    job_group = JobGroup(name="dev-test", description="test", is_active=True)
    db_session.add(job_group)
    db_session.commit()

    res = client.post(
        "/cover-letters",
        data={
            "question_text": "question",
            "answer_text": "answer",
            "job_group_id": job_group.id,
        },
    )

    assert res.status_code == 401


def test_create_cover_letter_saves_question_answer_pairs(auth_client, test_user, db_session):
    job_group = JobGroup(name="dev-test", description="test", is_active=True)
    db_session.add(job_group)
    db_session.commit()

    res = auth_client.post(
        "/cover-letters",
        data={
            "question_text": ["question one", "question two"],
            "answer_text": ["answer one", "answer two with | pipe"],
            "job_group_id": str(job_group.id),
            "company_name": "Tooktac",
            "title": "backend cover letter",
        },
    )

    assert res.status_code == 201
    body = res.json()
    assert body["company_name"] == "Tooktac"
    assert body["title"] == "backend cover letter"
    assert body["question_text"] == "question one|question two"
    assert body["answer_text"] == "answer one|answer two with ｜ pipe"
    assert body["items"] == [
        {"question_text": "question one", "answer_text": "answer one"},
        {"question_text": "question two", "answer_text": "answer two with ｜ pipe"},
    ]

    saved = db_session.query(CoverLetter).filter_by(user_id=test_user.id).one()
    assert saved.job_group_id == job_group.id


def test_create_cover_letter_requires_complete_pairs(auth_client, db_session):
    job_group = JobGroup(name="dev-test", description="test", is_active=True)
    db_session.add(job_group)
    db_session.commit()

    res = auth_client.post(
        "/cover-letters",
        data={
            "question_text": "question only",
            "answer_text": "",
            "job_group_id": job_group.id,
        },
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "질문과 답변을 모두 입력해주세요."


def test_update_cover_letter_replaces_question_answer_pairs(auth_client, test_user, db_session):
    first_group = JobGroup(name="dev-test", description="test", is_active=True)
    second_group = JobGroup(name="pm-test", description="test", is_active=True)
    db_session.add_all([first_group, second_group])
    db_session.flush()
    cover_letter = CoverLetter(
        user_id=test_user.id,
        job_group_id=first_group.id,
        title="old title",
        company_name="Old",
        question_text="old question",
        answer_text="old answer",
    )
    db_session.add(cover_letter)
    db_session.commit()

    res = auth_client.patch(
        f"/cover-letters/{cover_letter.id}",
        data={
            "question_text": ["new question one", "new question two"],
            "answer_text": ["new answer one", "new answer two"],
            "job_group_id": str(second_group.id),
            "company_name": "New",
            "title": "new title",
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["job_group_id"] == second_group.id
    assert body["company_name"] == "New"
    assert body["title"] == "new title"
    assert body["question_text"] == "new question one|new question two"
    assert body["answer_text"] == "new answer one|new answer two"
    assert body["items"] == [
        {"question_text": "new question one", "answer_text": "new answer one"},
        {"question_text": "new question two", "answer_text": "new answer two"},
    ]


def test_cover_letters_are_scoped_to_current_user(auth_client, test_user, db_session):
    job_group = JobGroup(name="dev-test", description="test", is_active=True)
    other_user = User(
        username="other",
        password="pw1234",
        name="다른 사용자",
        nickname="다른",
        email="other@example.com",
        birthdate=date(2000, 1, 1),
        desired_job="백엔드 개발자",
    )
    db_session.add_all([job_group, other_user])
    db_session.flush()
    own_letter = CoverLetter(
        user_id=test_user.id,
        job_group_id=job_group.id,
        title="own cover letter",
        question_text="own question",
        answer_text="own answer",
    )
    other_letter = CoverLetter(
        user_id=other_user.id,
        job_group_id=job_group.id,
        title="other cover letter",
        question_text="other question",
        answer_text="other answer",
    )
    db_session.add_all([own_letter, other_letter])
    db_session.commit()

    res = auth_client.get("/cover-letters")
    assert res.status_code == 200
    assert [item["id"] for item in res.json()] == [own_letter.id]

    res = auth_client.patch(
        f"/cover-letters/{other_letter.id}",
        data={
            "question_text": "hacked question",
            "answer_text": "hacked answer",
            "job_group_id": str(job_group.id),
        },
    )
    assert res.status_code == 404

    res = auth_client.delete(f"/cover-letters/{other_letter.id}")
    assert res.status_code == 404
    assert db_session.get(CoverLetter, other_letter.id) is not None


def test_cover_letter_rejects_unknown_job_group(auth_client):
    res = auth_client.post(
        "/cover-letters",
        data={
            "question_text": "question",
            "answer_text": "answer",
            "job_group_id": "999999",
        },
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "존재하지 않는 직무군입니다."


def test_list_and_delete_cover_letters(auth_client, test_user, db_session):
    job_group = JobGroup(name="dev-test", description="test", is_active=True)
    db_session.add(job_group)
    db_session.flush()
    cover_letter = CoverLetter(
        user_id=test_user.id,
        job_group_id=job_group.id,
        title="test cover letter",
        question_text="question",
        answer_text="answer",
    )
    db_session.add(cover_letter)
    db_session.commit()

    res = auth_client.get("/cover-letters")
    assert res.status_code == 200
    assert len(res.json()) == 1

    res = auth_client.delete(f"/cover-letters/{cover_letter.id}")
    assert res.status_code == 204
    assert db_session.get(CoverLetter, cover_letter.id) is None
