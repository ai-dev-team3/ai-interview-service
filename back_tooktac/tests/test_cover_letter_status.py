from app.repository.career import CoverLetter, JobGroup


def test_resume_status_includes_cover_letter(auth_client, test_user, db_session):
    auth_client.post("/resume", data={"resume_text": "resume content"})

    res = auth_client.get("/resume/status")
    assert res.status_code == 200
    assert res.json()["has_resume"] is True
    assert res.json()["has_cover_letter"] is False
    assert res.json()["ready_for_career_diagnosis"] is False

    job_group = JobGroup(name="dev-test", description="test job group", is_active=True)
    db_session.add(job_group)
    db_session.flush()
    db_session.add(
        CoverLetter(
            user_id=test_user.id,
            job_group_id=job_group.id,
            title="test cover letter",
            question_text="Why do you apply?",
            answer_text="This is a test answer.",
        )
    )
    db_session.commit()

    res = auth_client.get("/resume/status")
    assert res.json()["has_resume"] is True
    assert res.json()["has_cover_letter"] is True
    assert res.json()["ready_for_career_diagnosis"] is True
