"""DB-backed career readiness diagnosis service."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.repository.career import (
    ActionTemplate,
    CareerDiagnosisResult,
    JobGroup,
    JobReadinessCriteria,
)
from app.repository.user import User
from app.services.cover_letter import cover_letter_service
from app.services.resume import resume_service


class CareerDiagnosisPrerequisiteError(Exception):
    """Resume and cover letter are required before running career diagnosis."""


class CareerDiagnosisConfigError(Exception):
    """Career criteria seed data is missing or invalid."""


DEFAULT_JOB_GROUPS = [
    {
        "id": 1,
        "name": "개발/IT",
        "description": "개발자, 데이터, 인프라 등 IT 직무군",
        "keywords": [
            "개발", "백엔드", "프론트엔드", "서버", "데이터", "it", "python",
            "java", "spring", "fastapi", "react", "mysql", "api",
        ],
    },
    {
        "id": 2,
        "name": "마케팅/기획",
        "description": "콘텐츠, 서비스 기획, 마케팅 직무군",
        "keywords": [
            "마케팅", "기획", "콘텐츠", "서비스기획", "캠페인", "sns", "고객",
            "시장", "타깃", "브랜딩",
        ],
    },
    {
        "id": 3,
        "name": "사무/행정",
        "description": "사무보조, 행정, 운영지원 직무군",
        "keywords": [
            "사무", "행정", "운영", "총무", "문서", "보고서", "excel", "엑셀",
            "word", "ppt", "일정", "조율",
        ],
    },
]


def _criterion(
    name: str,
    description: str,
    keywords: list[str],
    weight: int,
    action_title: str,
    action_detail: str,
) -> dict:
    return {
        "criterion_name": name,
        "description": description,
        "keywords": keywords,
        "weight": weight,
        "action_title": action_title,
        "action_detail": action_detail,
    }


DEFAULT_CRITERIA_BY_JOB_GROUP = {
    "개발/IT": [
        _criterion(
            "프로젝트 경험",
            "실제 개발 프로젝트 경험이 있는지 평가합니다.",
            ["프로젝트", "구현", "개발", "기능", "서비스", "팀프로젝트", "개인프로젝트"],
            25,
            "대표 프로젝트를 구체화하세요",
            "프로젝트 목적, 본인 역할, 사용 기술, 구현 기능, 문제 해결 경험, 결과를 6개 항목으로 정리하세요.",
        ),
        _criterion(
            "기술스택 적합도",
            "희망 IT 직무와 관련된 기술을 보유했는지 평가합니다.",
            ["python", "java", "spring", "fastapi", "react", "vue", "mysql", "postgresql", "sqlalchemy"],
            25,
            "기술스택 설명을 보완하세요",
            "사용한 기술을 단순 나열하지 말고, 왜 사용했는지와 어떤 기능에 적용했는지 함께 정리하세요.",
        ),
        _criterion(
            "문제 해결 경험",
            "오류 해결, 구조 개선, 성능 개선 등 문제 해결 경험이 있는지 평가합니다.",
            ["오류", "에러", "개선", "리팩토링", "최적화", "트러블슈팅", "해결"],
            20,
            "트러블슈팅 사례를 정리하세요",
            "오류 상황, 원인 분석, 해결 방법, 결과 순서로 최소 1개 이상의 문제 해결 경험을 작성하세요.",
        ),
        _criterion(
            "문서화/포트폴리오",
            "GitHub, README, API 명세, ERD 등 결과물을 정리했는지 평가합니다.",
            ["github", "readme", "erd", "api 명세", "포트폴리오", "문서화", "wiki"],
            15,
            "GitHub README를 보완하세요",
            "프로젝트 소개, 실행 방법, 주요 기능, 기술스택, ERD, API 명세, 트러블슈팅 항목을 추가하세요.",
        ),
        _criterion(
            "배포/운영 경험",
            "서비스 배포, 서버 운영, 클라우드 사용 경험이 있는지 평가합니다.",
            ["aws", "ec2", "docker", "nginx", "pm2", "배포", "운영", "서버"],
            15,
            "배포 경험을 구조화하세요",
            "실제 배포 경험이 있다면 배포 주소와 서버 구조를 정리하고, 없다면 배포 계획과 학습 내용을 정리하세요.",
        ),
    ],
    "마케팅/기획": [
        _criterion(
            "콘텐츠/기획 경험",
            "콘텐츠 제작 또는 기획 경험이 있는지 평가합니다.",
            ["콘텐츠", "카드뉴스", "캠페인", "기획", "sns", "서비스기획"],
            25,
            "콘텐츠 사례를 정리하세요",
            "제작한 콘텐츠의 목적, 대상, 제작 과정, 반응을 정리하세요.",
        ),
        _criterion(
            "고객/시장 이해",
            "타깃, 고객, 시장 분석 경험이 있는지 평가합니다.",
            ["타깃", "고객", "시장조사", "경쟁사", "니즈", "페르소나"],
            20,
            "타깃 분석을 보완하세요",
            "콘텐츠나 기획의 대상 사용자가 누구였는지, 어떤 니즈를 고려했는지 작성하세요.",
        ),
        _criterion(
            "성과 지표 제시",
            "활동 결과를 수치로 설명할 수 있는지 평가합니다.",
            ["조회수", "클릭률", "전환율", "팔로워", "참여율", "%", "증가"],
            25,
            "성과 수치를 정리하세요",
            "조회수, 클릭률, 팔로워 증가, 참여율 등 가능한 지표를 수치로 정리하세요.",
        ),
        _criterion(
            "툴 활용 능력",
            "마케팅/기획 관련 도구를 활용했는지 평가합니다.",
            ["ga4", "excel", "notion", "figma", "광고관리자", "엑셀"],
            15,
            "사용한 툴과 활용 목적을 정리하세요",
            "Notion, Excel, GA4, Figma 등을 어떤 목적으로 사용했는지 구체화하세요.",
        ),
        _criterion(
            "자료화 능력",
            "기획서, 보고서, 포트폴리오로 경험을 정리했는지 평가합니다.",
            ["기획서", "보고서", "제안서", "포트폴리오", "문서", "발표자료"],
            15,
            "기획서를 포트폴리오화하세요",
            "기획 배경, 문제 정의, 실행 과정, 결과를 한 장짜리 요약 자료로 정리하세요.",
        ),
    ],
    "사무/행정": [
        _criterion(
            "문서 작성 능력",
            "회의록, 보고서, 문서 정리 경험이 있는지 평가합니다.",
            ["회의록", "보고서", "문서", "정리", "작성", "공문"],
            25,
            "문서 작성 사례를 정리하세요",
            "회의록, 보고서, 정리 문서 등 본인이 작성한 문서 유형과 목적을 정리하세요.",
        ),
        _criterion(
            "OA/Excel 활용",
            "Excel, Word, PPT 등 사무 도구 활용 경험이 있는지 평가합니다.",
            ["excel", "엑셀", "word", "ppt", "함수", "피벗", "데이터"],
            25,
            "Excel 활용 사례를 구체화하세요",
            "사용해본 함수, 표 정리, 데이터 관리 경험을 구체적으로 작성하세요.",
        ),
        _criterion(
            "일정/업무 관리",
            "일정 조율, 업무 분담, 관리 경험이 있는지 평가합니다.",
            ["일정", "관리", "조율", "체크리스트", "업무분장", "마감"],
            20,
            "일정 관리 경험을 정리하세요",
            "일정 조율, 마감 관리, 업무 분담 경험을 상황-역할-결과 순서로 정리하세요.",
        ),
        _criterion(
            "커뮤니케이션",
            "팀원, 고객, 조직 내 소통 경험이 있는지 평가합니다.",
            ["협업", "소통", "전달", "조율", "응대", "커뮤니케이션"],
            15,
            "협업 경험을 정리하세요",
            "팀원, 교수, 고객, 동료와의 소통 경험을 구체적으로 작성하세요.",
        ),
        _criterion(
            "정확성/꼼꼼함",
            "반복 업무, 자료 검토, 오류 방지 경험이 있는지 평가합니다.",
            ["검토", "확인", "정확성", "꼼꼼", "누락", "오류 방지"],
            15,
            "실수 방지 경험을 정리하세요",
            "자료 검토, 누락 확인, 반복 업무 처리 경험을 사례 중심으로 정리하세요.",
        ),
    ],
}


def _seed_default_data_if_empty(db: Session) -> None:
    if db.query(JobGroup).first():
        return

    groups_by_name: dict[str, JobGroup] = {}
    for group_data in DEFAULT_JOB_GROUPS:
        group = JobGroup(
            id=group_data["id"],
            name=group_data["name"],
            description=group_data["description"],
            is_active=True,
        )
        db.add(group)
        groups_by_name[group.name] = group

    db.flush()

    sort_action = 1
    for group_name, criteria in DEFAULT_CRITERIA_BY_JOB_GROUP.items():
        group = groups_by_name[group_name]
        for sort_order, criterion_data in enumerate(criteria, start=1):
            criterion = JobReadinessCriteria(
                job_group_id=group.id,
                criterion_name=criterion_data["criterion_name"],
                description=criterion_data["description"],
                keywords=criterion_data["keywords"],
                weight=criterion_data["weight"],
                sort_order=sort_order,
            )
            db.add(criterion)
            db.flush()
            db.add(
                ActionTemplate(
                    job_group_id=group.id,
                    criterion_id=criterion.id,
                    action_title=criterion_data["action_title"],
                    action_detail=criterion_data["action_detail"],
                    sort_order=sort_action,
                )
            )
            sort_action += 1

    db.commit()


def list_job_groups(db: Session) -> list[dict]:
    _seed_default_data_if_empty(db)
    groups = (
        db.query(JobGroup)
        .filter(JobGroup.is_active.is_(True))
        .order_by(JobGroup.id)
        .all()
    )
    return [
        {"id": group.id, "name": group.name, "description": group.description}
        for group in groups
    ]


def _structured_to_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(v) for v in value)
    if value is None:
        return ""
    return str(value)


def _has_meaningful_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_meaningful_value(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_meaningful_value(v) for v in value)
    return value is not None


def _keyword_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _count_matches(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    normalized = text.lower()
    matches = [keyword for keyword in keywords if keyword.lower() in normalized]
    return len(matches), matches


def _group_match_keywords(group: JobGroup, criteria: list[JobReadinessCriteria]) -> list[str]:
    words = [group.name, group.description or ""]
    for seed_group in DEFAULT_JOB_GROUPS:
        if seed_group["name"] == group.name:
            words.extend(seed_group["keywords"])
            break
    for criterion in criteria:
        words.extend(_keyword_list(criterion.keywords))
    return [word for word in words if word]


def _load_active_groups_with_criteria(db: Session) -> tuple[list[JobGroup], dict[int, list[JobReadinessCriteria]]]:
    groups = (
        db.query(JobGroup)
        .filter(JobGroup.is_active.is_(True))
        .order_by(JobGroup.id)
        .all()
    )
    criteria_by_group: dict[int, list[JobReadinessCriteria]] = {}
    for group in groups:
        criteria_by_group[group.id] = (
            db.query(JobReadinessCriteria)
            .filter(JobReadinessCriteria.job_group_id == group.id)
            .order_by(JobReadinessCriteria.sort_order, JobReadinessCriteria.id)
            .all()
        )
    return groups, criteria_by_group


def _choose_job_group(
    groups: list[JobGroup],
    criteria_by_group: dict[int, list[JobReadinessCriteria]],
    desired_job: str,
    corpus: str,
) -> JobGroup:
    if not groups:
        raise CareerDiagnosisConfigError("등록된 직무군이 없습니다.")

    target_text = f"{desired_job} {corpus}".lower()
    scored = []
    for group in groups:
        score, _ = _count_matches(target_text, _group_match_keywords(group, criteria_by_group[group.id]))
        scored.append((score, group))
    scored.sort(key=lambda item: (item[0], -item[1].id), reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else groups[0]


def _specificity_score(structured: dict, content: str) -> int:
    text_length = len(content.strip())
    length_score = min(18, text_length // 120)

    sections = 0
    for key in ("skills", "career", "projects", "self_introduction", "education"):
        if _has_meaningful_value(structured.get(key)):
            sections += 1

    return min(30, 6 + length_score + sections * 3)


def _material_score(corpus: str) -> int:
    score = 20
    material_keywords = [
        "github",
        "포트폴리오",
        "readme",
        "erd",
        "api 명세",
        "자격증",
        "보고서",
        "기획서",
        "배포",
    ]
    matched, _ = _count_matches(corpus, material_keywords)
    return min(30, score + matched * 3)


def _score_criterion(criterion: JobReadinessCriteria, structured: dict, content: str) -> dict:
    keywords = _keyword_list(criterion.keywords)
    corpus = f"{content} {_flatten(structured)}"
    matched_count, matched_keywords = _count_matches(corpus, keywords)
    keyword_score = min(40, matched_count * 8)
    detail_score = _specificity_score(structured, content)
    material_score = _material_score(corpus)
    score = min(100, keyword_score + detail_score + material_score)

    if score >= 75:
        feedback = f"{criterion.criterion_name}은 현재 자료에서 근거가 비교적 잘 보입니다."
    elif score >= 55:
        feedback = f"{criterion.criterion_name}은 기본 근거가 있으나 더 구체적인 사례 정리가 필요합니다."
    else:
        feedback = f"{criterion.criterion_name}은 자료에서 확인되는 근거가 부족합니다. 액션 플랜부터 보완해보세요."

    if matched_keywords:
        feedback += f" 확인된 키워드: {', '.join(matched_keywords[:4])}"

    return {
        "criterion_id": criterion.id,
        "criterion_name": criterion.criterion_name,
        "description": criterion.description,
        "score": score,
        "weight": criterion.weight,
        "feedback": feedback,
        "matched_keywords": matched_keywords,
    }


def _score_label(score: int) -> str:
    if score >= 80:
        return "준비 상태가 좋은 편입니다."
    if score >= 60:
        return "기본 준비는 되어 있으나 보완이 필요합니다."
    if score >= 40:
        return "주요 준비 항목이 부족합니다."
    return "기초 자료부터 정리가 필요합니다."


def _build_action_plan(
    db: Session,
    job_group_id: int,
    sorted_results: list[dict],
) -> list[dict]:
    criterion_ids = [item["criterion_id"] for item in sorted_results[:3]]
    actions = (
        db.query(ActionTemplate)
        .filter(
            ActionTemplate.job_group_id == job_group_id,
            ActionTemplate.criterion_id.in_(criterion_ids),
        )
        .order_by(ActionTemplate.sort_order, ActionTemplate.id)
        .all()
    )
    action_by_criterion = {action.criterion_id: action for action in actions}

    plan = []
    for item in sorted_results[:3]:
        action = action_by_criterion.get(item["criterion_id"])
        if action:
            plan.append({"title": action.action_title, "detail": action.action_detail})
    return plan


def create_diagnosis(db: Session, user_id: int) -> dict:
    _seed_default_data_if_empty(db)

    status = resume_service.get_resume_status(db, user_id)
    if not status["ready_for_career_diagnosis"]:
        raise CareerDiagnosisPrerequisiteError("자소서와 이력서를 등록 후 이용하시기 바랍니다.")

    resume = resume_service.get_resume(db, user_id)
    user = db.get(User, user_id)
    cover_letter = cover_letter_service.get_latest_cover_letter(db, user_id)
    cover_letter_text = cover_letter_service.to_analysis_text(cover_letter)
    structured = _structured_to_dict(resume.structured)
    desired_job = user.desired_job if user and user.desired_job else ""
    content = f"{resume.content}\n{cover_letter_text}"
    corpus = f"{desired_job} {content} {_flatten(structured)}"

    groups, criteria_by_group = _load_active_groups_with_criteria(db)
    job_group = _choose_job_group(groups, criteria_by_group, desired_job, corpus)
    criteria = criteria_by_group[job_group.id]
    if not criteria:
        raise CareerDiagnosisConfigError("선택된 직무군의 진단 기준이 없습니다.")

    criteria_results = [
        _score_criterion(criterion, structured, content)
        for criterion in criteria
    ]
    total_weight = sum(item["weight"] for item in criteria_results) or 100
    total_score = round(
        sum(item["score"] * item["weight"] for item in criteria_results) / total_weight
    )

    sorted_results = sorted(criteria_results, key=lambda item: item["score"])
    strengths = [
        item["criterion_name"]
        for item in sorted(criteria_results, key=lambda item: item["score"], reverse=True)
        if item["score"] >= 65
    ][:3]
    weaknesses = [item["criterion_name"] for item in sorted_results[:3]]
    action_plan = _build_action_plan(db, job_group.id, sorted_results)

    target = desired_job or job_group.name
    summary = (
        f"{target} 기준 종합 취업 준비도는 {total_score}점입니다. "
        f"{_score_label(total_score)} "
        f"{', '.join(strengths) if strengths else '구체화된 강점'}은 강점으로 보이고, "
        f"{', '.join(weaknesses)}은 우선 보완할 항목입니다."
    )

    payload = {
        "job_group": {
            "id": job_group.id,
            "name": job_group.name,
            "description": job_group.description,
        },
        "desired_job": desired_job,
        "total_score": total_score,
        "score_label": _score_label(total_score),
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "criteria_results": criteria_results,
        "action_plan": action_plan,
        "caution": "이 점수는 합격 가능성이 아니라, 입력된 자료 기준으로 희망 직무 대비 준비 자료와 경험 근거가 얼마나 정리되어 있는지를 나타냅니다.",
    }

    result = CareerDiagnosisResult(
        user_id=user_id,
        resume_id=resume.id,
        job_group_id=job_group.id,
        desired_job=desired_job,
        total_score=total_score,
        result_json=payload,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return {"diagnosis_id": result.id, **payload}

