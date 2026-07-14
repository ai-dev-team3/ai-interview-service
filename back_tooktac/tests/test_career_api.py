from app.repository.career import CareerDiagnosisResult, CoverLetter, JobGroup
from app.repository.resume import Resume


def test_career_diagnosis_requires_auth(client):
    res = client.post("/career/diagnosis")
    assert res.status_code == 401


def test_list_job_groups_seeds_default_data(auth_client, db_session):
    res = auth_client.get("/career/job-groups")

    assert res.status_code == 200
    assert [item["name"] for item in res.json()] == ["개발/IT", "마케팅/기획", "사무/행정"]
    assert db_session.query(JobGroup).count() == 3


def test_career_diagnosis_requires_resume_and_cover_letter(auth_client):
    res = auth_client.post("/career/diagnosis")
    assert res.status_code == 400
    assert res.json()["detail"] == "자소서와 이력서를 등록 후 이용하시기 바랍니다."


def test_career_diagnosis_returns_action_plan(auth_client, test_user, db_session):
    auth_client.get("/career/job-groups")

    resume = Resume(
        user_id=test_user.id,
        filename="resume.pdf",
        content=(
            "백엔드 개발자 이력서입니다. Python FastAPI MySQL로 AI 면접 플랫폼 프로젝트를 "
            "개발했고 GitHub에 정리했습니다. 자기소개서 지원동기는 사용자 문제를 해결하는 "
            "서비스를 만들고 싶다는 점입니다."
        ),
        structured={
            "skills": ["Python", "FastAPI", "MySQL"],
            "projects": [
                {
                    "name": "AI 면접 플랫폼",
                    "description": "면접 질문 생성과 답변 분석 기능을 구현했습니다.",
                    "tech_stack": ["Python", "FastAPI", "MySQL"],
                }
            ],
            "self_introduction": {
                "motivation": "사용자 문제를 해결하는 서비스를 만들고 싶습니다.",
                "strengths": "꾸준한 구현 경험",
            },
            "desired_position": {"job_type": "백엔드 개발자"},
        },
    )
    db_session.add(resume)
    cover_letter = CoverLetter(
        user_id=test_user.id,
        job_group_id=1,
        title="지원동기",
        question_text="지원동기를 작성해주세요.",
        answer_text=(
            "사용자 문제를 해결하는 서비스를 만들고 싶습니다. Python FastAPI MySQL 프로젝트를 "
            "개발했고 GitHub에 정리했습니다."
        ),
    )
    db_session.add(cover_letter)
    db_session.commit()

    res = auth_client.post("/career/diagnosis")

    assert res.status_code == 200
    body = res.json()
    assert body["job_group"]["name"] == "개발/IT"
    assert 0 <= body["total_score"] <= 100
    assert body["criteria_results"]
    assert body["action_plan"]
    assert "합격 가능성" in body["caution"]

    saved = db_session.query(CareerDiagnosisResult).filter_by(user_id=test_user.id).one()
    assert saved.resume_id == resume.id
    assert saved.job_group_id == body["job_group"]["id"]
    assert saved.total_score == body["total_score"]
    assert saved.result_json["summary"] == body["summary"]
