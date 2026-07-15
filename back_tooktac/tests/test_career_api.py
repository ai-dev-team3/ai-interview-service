import pytest

from app.repository.career import (
    ActionTemplate,
    CareerDiagnosisResult,
    CoverLetter,
    CoverLetterItem,
    JobGroup,
    JobReadinessCriteria,
)
from app.repository.resume import Resume
from app.services.career import readiness


def _disable_llm_review(*_args, **_kwargs):
    return {}


@pytest.fixture(autouse=True)
def disable_career_llm_review(monkeypatch):
    # 이 파일의 API 테스트는 외부 LLM 네트워크 호출 없이 룰 기반 흐름만 검증한다.
    monkeypatch.setattr(readiness, "_run_llm_review", _disable_llm_review)


def _seed_career_master_data(db_session):
    groups = [
        JobGroup(id=1, name="백엔드 개발", description="서버, API, 데이터베이스, 배포 중심 개발 직무", is_active=True),
        JobGroup(id=2, name="마케팅", description="콘텐츠, 캠페인, 채널 운영, 성과 분석 직무", is_active=True),
        JobGroup(id=3, name="사무행정", description="문서 작성, OA, 일정 관리, 행정 지원 직무", is_active=True),
    ]
    db_session.add_all(groups)
    criterion = JobReadinessCriteria(
        id=1,
        job_group_id=1,
        criterion_name="프로젝트 경험",
        description="실제 개발 프로젝트 경험이 있는지 평가합니다.",
        keywords=["프로젝트", "개발", "python", "fastapi", "mysql"],
        weight=100,
        sort_order=1,
    )
    db_session.add(criterion)
    db_session.flush()
    db_session.add(
        ActionTemplate(
            id=1,
            job_group_id=1,
            criterion_id=criterion.id,
            action_title="대표 프로젝트를 구체화하세요",
            action_detail="프로젝트 목적, 본인 역할, 사용 기술, 결과를 정리하세요.",
            sort_order=1,
        )
    )
    db_session.commit()


def test_career_diagnosis_requires_auth(client):
    res = client.post("/career/diagnosis")
    assert res.status_code == 401


def test_list_job_groups_does_not_seed_on_request(auth_client, db_session):
    res = auth_client.get("/career/job-groups")

    assert res.status_code == 200
    assert res.json() == []
    assert db_session.query(JobGroup).count() == 0


def test_list_job_groups_returns_seeded_master_data(auth_client, db_session):
    _seed_career_master_data(db_session)

    res = auth_client.get("/career/job-groups")

    assert res.status_code == 200
    assert [item["name"] for item in res.json()] == ["백엔드 개발", "마케팅", "사무행정"]
    assert db_session.query(JobGroup).count() == 3


def test_career_diagnosis_requires_resume_and_cover_letter(auth_client):
    res = auth_client.post("/career/diagnosis")
    assert res.status_code == 400
    assert res.json()["detail"] == "자소서와 이력서를 등록 후 이용하시기 바랍니다."


def test_career_diagnosis_returns_action_plan(auth_client, test_user, db_session):
    _seed_career_master_data(db_session)

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
    unselected_cover_letter = CoverLetter(
        user_id=test_user.id,
        job_group_id=1,
        title="선택하지 않은 자소서",
        items=[
            CoverLetterItem(
                sort_order=1,
                question_text="다른 자소서입니다.",
                answer_text="이 자소서는 이번 진단에 사용하지 않습니다.",
            ),
        ],
    )
    cover_letter = CoverLetter(
        user_id=test_user.id,
        job_group_id=1,
        title="지원동기",
        items=[
            CoverLetterItem(
                sort_order=1,
                question_text="지원동기를 작성해주세요.",
                answer_text=(
                    "사용자 문제를 해결하는 서비스를 만들고 싶습니다. Python FastAPI MySQL 프로젝트를 "
                    "개발했고 GitHub에 정리했습니다."
                ),
            ),
        ],
    )
    db_session.add_all([unselected_cover_letter, cover_letter])
    db_session.commit()

    res = auth_client.post("/career/diagnosis", json={"cover_letter_id": cover_letter.id})

    assert res.status_code == 200
    body = res.json()
    assert body["job_group"]["name"] == "백엔드 개발"
    assert body["source_cover_letter"]["id"] == cover_letter.id
    assert 0 <= body["total_score"] <= 100
    assert body["criteria_results"]
    assert body["action_plan"]
    assert "합격 가능성" in body["caution"]

    saved = db_session.query(CareerDiagnosisResult).filter_by(user_id=test_user.id).one()
    assert saved.resume_id == resume.id
    assert saved.job_group_id == body["job_group"]["id"]
    assert saved.total_score == body["total_score"]
    assert saved.result_json["summary"] == body["summary"]
    assert saved.result_json["source_cover_letter"]["id"] == cover_letter.id


def test_career_diagnosis_rejects_unknown_cover_letter(auth_client, test_user, db_session):
    _seed_career_master_data(db_session)
    db_session.add(
        Resume(
            user_id=test_user.id,
            filename="resume.pdf",
            content="Python FastAPI 프로젝트를 진행했습니다.",
            structured={"skills": ["Python", "FastAPI"]},
        )
    )
    db_session.add(
        CoverLetter(
            user_id=test_user.id,
            job_group_id=1,
            title="등록된 자소서",
            items=[
                CoverLetterItem(
                    sort_order=1,
                    question_text="지원동기",
                    answer_text="개발 프로젝트 경험을 바탕으로 지원했습니다.",
                ),
            ],
        )
    )
    db_session.commit()

    res = auth_client.post("/career/diagnosis", json={"cover_letter_id": 999999})

    assert res.status_code == 400
    assert res.json()["detail"] == "선택한 자소서를 찾을 수 없습니다."


def test_career_diagnosis_returns_unavailable_for_placeholder_cover_letter(
    auth_client,
    test_user,
    db_session,
):
    _seed_career_master_data(db_session)
    resume = Resume(
        user_id=test_user.id,
        filename="resume.pdf",
        content=(
            "Python FastAPI MySQL을 활용해 API 서버를 개발했고, 오류 원인을 분석해 "
            "응답 속도를 개선한 프로젝트 경험이 있습니다."
        ),
        structured={"skills": ["Python", "FastAPI", "MySQL"]},
    )
    cover_letter = CoverLetter(
        user_id=test_user.id,
        job_group_id=1,
        title="임시 자소서",
        items=[
            CoverLetterItem(sort_order=1, question_text="질문1", answer_text="답변1"),
        ],
    )
    db_session.add_all([resume, cover_letter])
    db_session.commit()

    res = auth_client.post("/career/diagnosis", json={"cover_letter_id": cover_letter.id})

    assert res.status_code == 200
    body = res.json()
    assert body["evaluation_available"] is False
    assert body["total_score"] == 0
    assert body["score_label"] == "평가 불가"
    assert body["criteria_results"] == []
    assert body["unavailable_reasons"]

    saved = db_session.query(CareerDiagnosisResult).filter_by(user_id=test_user.id).one()
    assert saved.total_score == 0
    assert saved.result_json["evaluation_available"] is False


def test_career_diagnosis_caps_score_when_material_does_not_match_selected_job_group(
    auth_client,
    test_user,
    db_session,
):
    _seed_career_master_data(db_session)
    office_criteria = [
        ("문서 작성 능력", ["회의록", "보고서", "문서", "정리", "작성", "공문"]),
        ("OA/Excel 활용", ["excel", "엑셀", "word", "ppt", "함수", "피벗", "데이터"]),
        ("일정/업무 관리", ["일정", "관리", "조율", "체크리스트", "업무분장", "마감"]),
        ("커뮤니케이션", ["협업", "소통", "전달", "조율", "응대", "커뮤니케이션"]),
        ("정확성/꼼꼼함", ["검토", "확인", "정확성", "꼼꼼", "누락", "오류 방지"]),
    ]
    for index, (name, keywords) in enumerate(office_criteria, start=20):
        db_session.add(
            JobReadinessCriteria(
                id=index,
                job_group_id=3,
                criterion_name=name,
                description=f"{name}을 평가합니다.",
                keywords=keywords,
                weight=20,
                sort_order=index,
            )
        )

    resume = Resume(
        user_id=test_user.id,
        filename="resume.pdf",
        content=(
            "Python FastAPI MySQL 기반 백엔드 API를 개발했고 GitHub README와 ERD, "
            "배포 과정을 정리했습니다. 오류 원인을 분석해 서버 응답 속도를 개선했습니다."
        ),
        structured={
            "skills": ["Python", "FastAPI", "MySQL"],
            "projects": [{"name": "API 서버", "description": "백엔드 개발과 배포"}],
        },
    )
    cover_letter = CoverLetter(
        user_id=test_user.id,
        job_group_id=3,
        title="지원동기",
        items=[
            CoverLetterItem(
                sort_order=1,
                question_text="대표 경험을 작성해주세요.",
                answer_text=(
                    "제가 백엔드 API 개발을 담당했고 Python FastAPI로 인증 기능을 구현했습니다. "
                    "배포 중 발생한 오류를 분석해 원인을 해결했고 GitHub README에 개발 과정을 정리했습니다."
                ),
            ),
        ],
    )
    db_session.add_all([resume, cover_letter])
    db_session.commit()

    res = auth_client.post("/career/diagnosis", json={"cover_letter_id": cover_letter.id})

    assert res.status_code == 200
    body = res.json()
    assert body["evaluation_available"] is True
    assert body["job_group"]["name"] == "사무행정"
    assert body["job_fit"]["cap"] <= 40
    assert body["total_score"] <= body["job_fit"]["cap"]


def test_career_diagnosis_strengths_and_weaknesses_do_not_overlap(
    auth_client,
    test_user,
    db_session,
):
    _seed_career_master_data(db_session)
    for index in range(2, 6):
        db_session.add(
            JobReadinessCriteria(
                id=index,
                job_group_id=1,
                criterion_name=f"진단 기준 {index}",
                description="중복 강약점 방지용 기준입니다.",
                keywords=["python", "fastapi", "mysql", "github", "배포"],
                weight=100,
                sort_order=index,
            )
        )

    resume = Resume(
        user_id=test_user.id,
        filename="resume.pdf",
        content=(
            "Python FastAPI MySQL 프로젝트를 개발했고 GitHub, README, ERD, API 명세, "
            "배포 경험을 포트폴리오에 정리했습니다."
        ),
        structured={
            "skills": ["Python", "FastAPI", "MySQL"],
            "projects": [{"name": "AI 면접 플랫폼", "description": "API 개발과 배포"}],
            "self_introduction": {"strengths": "프로젝트 실행력"},
        },
    )
    cover_letter = CoverLetter(
        user_id=test_user.id,
        job_group_id=1,
        title="강점 자소서",
        items=[
            CoverLetterItem(
                sort_order=1,
                question_text="대표 경험",
                answer_text=(
                    "제가 백엔드 API 개발을 담당했고 GitHub와 README에 구현 기능, ERD, "
                    "배포 링크를 정리했습니다. 그 결과 팀원이 프로젝트 구조를 빠르게 이해했고 "
                    "면접 포트폴리오에서도 근거 자료로 활용할 수 있었습니다."
                ),
            ),
        ],
    )
    db_session.add_all([resume, cover_letter])
    db_session.commit()

    res = auth_client.post("/career/diagnosis", json={"cover_letter_id": cover_letter.id})

    assert res.status_code == 200
    body = res.json()
    assert not (set(body["strengths"]) & set(body["weaknesses"]))
    assert body["weaknesses"] == []
    assert "뚜렷한 약점은 적지만" in body["summary"]


def test_score_criterion_has_no_default_floor():
    criterion = JobReadinessCriteria(
        id=1,
        job_group_id=1,
        criterion_name="프로젝트 경험",
        description="프로젝트 경험이 있는지 평가합니다.",
        keywords=["python"],
        weight=100,
        sort_order=1,
    )

    result = readiness._score_criterion(criterion, {}, "")

    assert result["score"] == 0
    assert "근거가 부족합니다" in result["feedback"]


def test_keyword_stuffing_is_penalized_without_evidence():
    criterion = JobReadinessCriteria(
        id=1,
        job_group_id=1,
        criterion_name="기술스택 적합도",
        description="기술 근거를 평가합니다.",
        keywords=["python"],
        weight=100,
        sort_order=1,
    )

    result = readiness._score_criterion(
        criterion,
        {},
        "python python python python python",
        [{"question_text": "사용 기술", "answer_text": "python python python"}],
    )

    assert result["keyword_stuffing_penalty"] > 0
    assert result["score"] < 20
    assert "키워드 반복 나열" in result["feedback"]


def test_evidence_sentence_and_qa_quality_raise_score():
    criterion = JobReadinessCriteria(
        id=1,
        job_group_id=1,
        criterion_name="문제 해결 경험",
        description="문제 해결 근거를 평가합니다.",
        keywords=["오류", "개선", "해결"],
        weight=100,
        sort_order=1,
    )
    answer_units = [
        {
            "question_text": "문제를 해결한 경험을 작성해주세요.",
            "answer_text": (
                "제가 API 오류 원인을 분석했고 쿼리 구조를 개선했습니다. "
                "그 결과 응답 시간이 30% 감소했고 팀 배포 일정도 지킬 수 있었습니다."
            ),
        }
    ]

    result = readiness._score_criterion(
        criterion,
        {"projects": [{"name": "API 개선"}]},
        "API 오류 원인을 분석하고 쿼리 구조를 개선해 문제를 해결했습니다.",
        answer_units,
    )

    assert result["evidence_keywords"]
    assert result["qa_score"] >= 15
    assert result["score"] >= 55


def test_llm_review_adjusts_rule_score_and_marks_reviewed():
    criteria_results = [
        {
            "criterion_name": "프로젝트 경험",
            "description": "실제 프로젝트 경험",
            "score": 80,
            "rule_score": 80,
            "feedback": "룰 기반 피드백",
            "matched_keywords": ["프로젝트"],
            "evidence_keywords": ["프로젝트"],
            "weight": 100,
        }
    ]

    adjusted = readiness._apply_llm_review(
        criteria_results,
        {
            "프로젝트 경험": {
                "score": 40,
                "feedback": "키워드만 있고 역할과 결과가 부족합니다.",
                "evidence_summary": "구체 근거 부족",
                "is_keyword_stuffed": True,
            }
        },
    )

    assert adjusted[0]["llm_reviewed"] is True
    assert adjusted[0]["llm_score"] == 40
    assert adjusted[0]["score"] < 80
    assert "AI 검토" in adjusted[0]["feedback"]


def test_llm_review_score_is_capped_when_direct_evidence_is_missing():
    criteria_results = [
        {
            "criterion_name": "OA/Excel 활용",
            "description": "사무 도구 활용",
            "score": 32,
            "rule_score": 32,
            "criterion_cap": 40,
            "feedback": "직접 근거 부족",
            "matched_keywords": ["excel"],
            "evidence_keywords": [],
            "weight": 100,
        }
    ]

    adjusted = readiness._apply_llm_review(
        criteria_results,
        {
            "OA/Excel 활용": {
                "score": 90,
                "feedback": "전반적으로 성실하게 작성되었습니다.",
                "evidence_summary": "직접 근거 부족",
                "is_keyword_stuffed": False,
            }
        },
    )

    assert adjusted[0]["llm_raw_score"] == 90
    assert adjusted[0]["llm_score"] == 40
    assert adjusted[0]["llm_score_cap"] == 40
    assert adjusted[0]["score"] <= 40


def test_job_group_evaluation_rubric_is_specific_to_selected_group():
    backend_group = JobGroup(
        id=1,
        name="백엔드 개발",
        description="서버, API, 데이터베이스, 배포 중심 개발 직무",
        is_active=True,
    )
    office_group = JobGroup(
        id=3,
        name="사무행정",
        description="문서 작성, OA, 일정 관리, 행정 지원 직무",
        is_active=True,
    )

    backend_rubric = readiness._job_group_evaluation_rubric(backend_group)
    office_rubric = readiness._job_group_evaluation_rubric(office_group)

    assert "API/서버 기능" in backend_rubric
    assert "문서 작성 또는 OA 활용" in office_rubric
    assert "API/서버 기능" not in office_rubric


def test_job_group_evaluation_rubric_falls_back_for_unknown_group():
    rubric = readiness._job_group_evaluation_rubric("미등록 직군")

    assert "별도 평가 가이드가 없습니다" in rubric


def test_choose_job_group_returns_none_when_keywords_do_not_match():
    groups = [
        JobGroup(id=1, name="백엔드 개발", description="서버, API, 데이터베이스, 배포 중심 개발 직무", is_active=True),
        JobGroup(id=2, name="마케팅", description="콘텐츠, 캠페인, 채널 운영, 성과 분석 직무", is_active=True),
    ]

    selected = readiness._choose_job_group(
        groups,
        criteria_by_group={1: [], 2: []},
        desired_job="",
        corpus="직무와 무관한 일반 문장",
    )

    assert selected is None
