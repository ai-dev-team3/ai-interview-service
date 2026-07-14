"""DB-backed career readiness diagnosis service."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.repository.career import (
    ActionTemplate,
    CareerDiagnosisResult,
    JobGroup,
    JobReadinessCriteria,
)
from app.repository.user import User
from app.services.cover_letter import cover_letter_service
from app.services.llm import get_chat_model
from app.services.resume import resume_service

logger = logging.getLogger(__name__)


class CareerDiagnosisPrerequisiteError(Exception):
    """Resume and cover letter are required before running career diagnosis."""


class CareerDiagnosisConfigError(Exception):
    """Career criteria seed data is missing or invalid."""


class LLMCriterionReview(BaseModel):
    criterion_name: str
    score: int = Field(ge=0, le=100)
    feedback: str
    evidence_summary: str = ""
    is_keyword_stuffed: bool = False


class LLMDiagnosisReview(BaseModel):
    criteria: list[LLMCriterionReview]
    overall_comment: str = ""


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

def list_job_groups(db: Session) -> list[dict]:
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
    seen = set()
    matches = []
    for keyword in keywords:
        key = keyword.lower()
        if key in seen:
            continue
        seen.add(key)
        if key in normalized:
            matches.append(keyword)
    return len(matches), matches


_ACTION_INDICATORS = [
    "개발", "구현", "설계", "해결", "개선", "분석", "작성", "기획", "운영", "배포",
    "관리", "활용", "정리", "제작", "도입", "검토", "확인", "수정", "테스트", "협업",
    "조율", "응대", "발표", "제안", "자동화", "최적화", "리팩토링", "built", "implemented",
    "designed", "deployed", "managed", "analyzed",
]
_RESULT_INDICATORS = [
    "결과", "성과", "달성", "증가", "감소", "개선", "완료", "성공", "효율", "시간",
    "기간", "사용자", "고객", "트래픽", "매출", "조회수", "전환율", "%", "명", "건",
    "회", "점", "등", "위",
]
_ROLE_INDICATORS = [
    "제가", "본인", "담당", "역할", "주도", "참여", "맡", "기여", "책임", "리드",
    "직접", "팀", "협업",
]
_PROBLEM_INDICATORS = [
    "문제", "과제", "상황", "어려움", "이슈", "오류", "에러", "원인", "요구사항",
    "목표", "필요",
]
_MATERIAL_KEYWORDS = [
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


def _contains_any(text: str, words: list[str]) -> bool:
    normalized = text.lower()
    return any(word.lower() in normalized for word in words)


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?。！？])\s+|[\n\r]+|[•·\-]\s*", text or "")
    return [re.sub(r"\s+", " ", chunk).strip() for chunk in chunks if chunk.strip()]


def _is_evidence_sentence(sentence: str) -> bool:
    compact = sentence.strip()
    if len(compact) < 12:
        return False
    return _contains_any(compact, _ACTION_INDICATORS) or _contains_any(compact, _RESULT_INDICATORS)


def _keyword_occurrences(text: str, keywords: list[str]) -> dict[str, int]:
    normalized = text.lower()
    counts: dict[str, int] = {}
    for keyword in keywords:
        key = keyword.lower()
        if not key:
            continue
        counts[keyword] = normalized.count(key)
    return counts


def _find_keyword_evidence(text: str, keywords: list[str]) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for sentence in _split_sentences(text):
        normalized_sentence = sentence.lower()
        if not _is_evidence_sentence(sentence):
            continue
        for keyword in keywords:
            if keyword.lower() in normalized_sentence and keyword not in evidence:
                evidence[keyword] = sentence
    return evidence


def _keyword_stuffing_penalty(text: str, matched_keywords: list[str]) -> int:
    if not matched_keywords:
        return 0

    counts = _keyword_occurrences(text, matched_keywords)
    repeated_overage = sum(max(0, count - 2) for count in counts.values())
    if repeated_overage <= 2:
        return 0

    evidence_count = len(_find_keyword_evidence(text, matched_keywords))
    if evidence_count >= len(matched_keywords):
        return min(8, repeated_overage)
    return min(20, repeated_overage * 3)


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
    criteria_by_group: dict[int, list[JobReadinessCriteria]] = {group.id: [] for group in groups}
    group_ids = [group.id for group in groups]
    if not group_ids:
        return groups, criteria_by_group

    criteria = (
        db.query(JobReadinessCriteria)
        .filter(JobReadinessCriteria.job_group_id.in_(group_ids))
        .order_by(
            JobReadinessCriteria.job_group_id,
            JobReadinessCriteria.sort_order,
            JobReadinessCriteria.id,
        )
        .all()
    )
    for criterion in criteria:
        criteria_by_group.setdefault(criterion.job_group_id, []).append(criterion)
    return groups, criteria_by_group


def _choose_job_group(
    groups: list[JobGroup],
    criteria_by_group: dict[int, list[JobReadinessCriteria]],
    desired_job: str,
    corpus: str,
) -> JobGroup | None:
    if not groups:
        raise CareerDiagnosisConfigError("등록된 직무군이 없습니다.")

    target_text = f"{desired_job} {corpus}".lower()
    scored = []
    for group in groups:
        score, _ = _count_matches(target_text, _group_match_keywords(group, criteria_by_group.get(group.id, [])))
        scored.append((score, group))
    scored.sort(key=lambda item: (item[0], -item[1].id), reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else None


def _specificity_score(structured: dict, content: str) -> int:
    text_length = len(content.strip())
    length_score = min(10, text_length // 180)

    sections = 0
    for key in ("skills", "career", "projects", "self_introduction", "education"):
        if _has_meaningful_value(structured.get(key)):
            sections += 1

    return min(20, length_score + sections * 2)


def _material_score(corpus: str) -> int:
    _, raw_matches = _count_matches(corpus, _MATERIAL_KEYWORDS)
    evidence = _find_keyword_evidence(corpus, _MATERIAL_KEYWORDS)
    evidence_matches = [keyword for keyword in raw_matches if keyword in evidence]
    weak_matches = [keyword for keyword in raw_matches if keyword not in evidence]
    return min(20, len(evidence_matches) * 5 + len(weak_matches) * 2)


def _answer_unit_quality(pair: dict[str, str]) -> int:
    question = (pair.get("question_text") or "").strip()
    answer = (pair.get("answer_text") or "").strip()
    if not answer:
        return 0

    score = 0
    answer_length = len(answer)
    score += min(5, answer_length // 80)
    if _contains_any(answer, _ROLE_INDICATORS):
        score += 4
    if _contains_any(answer, _PROBLEM_INDICATORS):
        score += 5
    if _contains_any(answer, _ACTION_INDICATORS):
        score += 6
    if _contains_any(answer, _RESULT_INDICATORS):
        score += 6
    if question and len(answer) >= 40:
        score += 2
    return min(25, score)


def _qa_unit_quality_score(answer_units: list[dict[str, str]], keywords: list[str]) -> int:
    if not answer_units:
        return 0

    relevant_scores = []
    generic_scores = []
    for pair in answer_units:
        unit_text = f"{pair.get('question_text', '')} {pair.get('answer_text', '')}"
        score = _answer_unit_quality(pair)
        generic_scores.append(score)
        if any(keyword.lower() in unit_text.lower() for keyword in keywords):
            relevant_scores.append(score)

    if relevant_scores:
        return round(sum(sorted(relevant_scores, reverse=True)[:2]) / min(2, len(relevant_scores)))

    generic_average = round(sum(generic_scores) / len(generic_scores))
    return min(8, round(generic_average * 0.35))


def _score_criterion(
    criterion: JobReadinessCriteria,
    structured: dict,
    content: str,
    answer_units: list[dict[str, str]] | None = None,
) -> dict:
    keywords = _keyword_list(criterion.keywords)
    structured_text = _flatten(structured)
    corpus = f"{content} {structured_text}"
    _, matched_keywords = _count_matches(corpus, keywords)
    evidence_by_keyword = _find_keyword_evidence(content, keywords)
    structured_matches = [
        keyword
        for keyword in matched_keywords
        if keyword.lower() in structured_text.lower()
    ]
    evidence_matched_keywords = list(dict.fromkeys([
        *evidence_by_keyword.keys(),
        *structured_matches,
    ]))

    if evidence_matched_keywords:
        keyword_score = min(35, len(evidence_matched_keywords) * 10)
    else:
        keyword_score = min(10, len(matched_keywords) * 3)

    detail_score = _specificity_score(structured, content)
    material_score = _material_score(corpus)
    qa_score = _qa_unit_quality_score(answer_units or [], keywords)
    stuffing_penalty = _keyword_stuffing_penalty(content, matched_keywords)
    score = max(0, min(100, keyword_score + detail_score + material_score + qa_score - stuffing_penalty))

    if score >= 75:
        feedback = f"{criterion.criterion_name}은 현재 자료에서 근거가 비교적 잘 보입니다."
    elif score >= 55:
        feedback = f"{criterion.criterion_name}은 기본 근거가 있으나 역할, 행동, 결과를 더 구체화하면 좋습니다."
    else:
        feedback = f"{criterion.criterion_name}은 자료에서 확인되는 실행 근거가 부족합니다. 액션 플랜부터 보완해보세요."

    if evidence_matched_keywords:
        feedback += f" 근거가 확인된 키워드: {', '.join(evidence_matched_keywords[:4])}"
    elif matched_keywords:
        feedback += f" 키워드는 있으나 수행 근거 문장이 부족합니다: {', '.join(matched_keywords[:4])}"
    if qa_score < 10:
        feedback += " 자소서 답변은 문제-행동-결과 구조를 더 보완해주세요."
    if stuffing_penalty:
        feedback += " 키워드 반복 나열 가능성이 있어 일부 감점되었습니다."

    return {
        "criterion_id": criterion.id,
        "criterion_name": criterion.criterion_name,
        "description": criterion.description,
        "score": score,
        "rule_score": score,
        "weight": criterion.weight,
        "feedback": feedback,
        "matched_keywords": matched_keywords,
        "evidence_keywords": evidence_matched_keywords,
        "keyword_score": keyword_score,
        "specificity_score": detail_score,
        "material_score": material_score,
        "qa_score": qa_score,
        "keyword_stuffing_penalty": stuffing_penalty,
        "llm_reviewed": False,
    }


_LLM_REVIEW_TEMPLATE = """당신은 채용 담당자이자 커리어 코치입니다.
지원자의 이력서와 자기소개서 답변을 바탕으로 취업 준비도 평가 기준별 점수를 검토하세요.

중요한 원칙:
- 키워드가 많아도 실제 역할, 행동, 문제 해결, 결과 근거가 없으면 낮게 평가하세요.
- 같은 키워드를 반복하거나 나열만 한 경우 is_keyword_stuffed를 true로 표시하세요.
- 자기소개서 질문/답변 단위로 답변이 질문에 맞는지, STAR 구조가 있는지 확인하세요.
- 원문에 없는 경험을 추측하지 마세요.
- 모든 출력은 한국어로 작성하세요.

직무군: {job_group}

평가 기준과 룰 기반 1차 점수:
{criteria}

이력서 요약/원문:
{resume_content}

자기소개서 Q/A:
{cover_letter_items}
"""


class CareerReadinessLLMReviewer:
    def __init__(self, llm: Runnable | None = None):
        self.llm = llm if llm is not None else get_chat_model(
            primary="gemini",
            temperature=0.1,
            max_tokens=3000,
            schema=LLMDiagnosisReview,
        )
        self.chain = ChatPromptTemplate.from_template(_LLM_REVIEW_TEMPLATE) | self.llm

    def review(
        self,
        *,
        job_group: JobGroup,
        criteria_results: list[dict],
        resume_content: str,
        answer_units: list[dict[str, str]],
    ) -> dict[str, dict]:
        criteria_payload = [
            {
                "criterion_name": item["criterion_name"],
                "description": item["description"],
                "rule_score": item["score"],
                "matched_keywords": item.get("matched_keywords", []),
                "evidence_keywords": item.get("evidence_keywords", []),
                "feedback": item["feedback"],
            }
            for item in criteria_results
        ]
        result = self.chain.invoke({
            "job_group": job_group.name,
            "criteria": json.dumps(criteria_payload, ensure_ascii=False),
            "resume_content": resume_content[:6000],
            "cover_letter_items": json.dumps(answer_units, ensure_ascii=False),
        })

        if isinstance(result, BaseModel):
            data = result.model_dump()
        elif isinstance(result, dict):
            data = result
        elif hasattr(result, "content"):
            try:
                data = json.loads(result.content)
            except (TypeError, json.JSONDecodeError):
                return {}
        else:
            return {}

        reviews = data.get("criteria", [])
        if not isinstance(reviews, list):
            return {}

        normalized: dict[str, dict] = {}
        for review in reviews:
            if not isinstance(review, dict):
                continue
            name = str(review.get("criterion_name") or "").strip()
            if not name:
                continue
            try:
                score = max(0, min(100, int(round(float(review.get("score", 0))))))
            except (TypeError, ValueError):
                continue
            normalized[name] = {
                "score": score,
                "feedback": str(review.get("feedback") or "").strip(),
                "evidence_summary": str(review.get("evidence_summary") or "").strip(),
                "is_keyword_stuffed": bool(review.get("is_keyword_stuffed")),
            }
        return normalized


def _run_llm_review(
    job_group: JobGroup,
    criteria_results: list[dict],
    resume_content: str,
    answer_units: list[dict[str, str]],
) -> dict[str, dict]:
    try:
        return CareerReadinessLLMReviewer().review(
            job_group=job_group,
            criteria_results=criteria_results,
            resume_content=resume_content,
            answer_units=answer_units,
        )
    except Exception:
        logger.warning("취업 준비도 LLM 검토 실패 - 룰 기반 점수로 계속 진행합니다.", exc_info=True)
        return {}


def _apply_llm_review(criteria_results: list[dict], llm_reviews: dict[str, dict]) -> list[dict]:
    if not llm_reviews:
        return criteria_results

    adjusted_results = []
    for item in criteria_results:
        review = llm_reviews.get(item["criterion_name"])
        if not review:
            adjusted_results.append(item)
            continue

        rule_score = int(item["score"])
        llm_score = int(review["score"])
        adjusted_score = round(rule_score * 0.75 + llm_score * 0.25)
        if review.get("is_keyword_stuffed"):
            adjusted_score = max(0, adjusted_score - 8)

        updated = {
            **item,
            "score": max(0, min(100, adjusted_score)),
            "llm_score": llm_score,
            "llm_feedback": review.get("feedback", ""),
            "llm_evidence_summary": review.get("evidence_summary", ""),
            "llm_keyword_stuffed": bool(review.get("is_keyword_stuffed")),
            "llm_reviewed": True,
        }
        if updated["llm_feedback"]:
            updated["feedback"] += f" AI 검토: {updated['llm_feedback']}"
        if updated["llm_keyword_stuffed"]:
            updated["feedback"] += " AI 검토에서도 키워드 나열 가능성이 확인되었습니다."
        adjusted_results.append(updated)

    return adjusted_results


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


def create_diagnosis(
    db: Session,
    user_id: int,
    *,
    cover_letter_id: int | None = None,
) -> dict:
    status = resume_service.get_resume_status(db, user_id)
    if not status["ready_for_career_diagnosis"]:
        raise CareerDiagnosisPrerequisiteError("자소서와 이력서를 등록 후 이용하시기 바랍니다.")

    resume = resume_service.get_resume(db, user_id)
    user = db.get(User, user_id)
    if cover_letter_id is None:
        cover_letter = cover_letter_service.get_latest_cover_letter(db, user_id)
    else:
        cover_letter = cover_letter_service.get_cover_letter(db, user_id, cover_letter_id)
        if not cover_letter:
            raise CareerDiagnosisPrerequisiteError("선택한 자소서를 찾을 수 없습니다.")

    if not cover_letter:
        raise CareerDiagnosisPrerequisiteError("자소서와 이력서를 등록 후 이용하시기 바랍니다.")

    cover_letter_text = cover_letter_service.to_analysis_text(cover_letter)
    answer_units = cover_letter_service.split_cover_letter_pairs(cover_letter)
    structured = _structured_to_dict(resume.structured)
    desired_job = user.desired_job if user and user.desired_job else ""
    content = f"{resume.content}\n{cover_letter_text}"
    corpus = f"{desired_job} {content} {_flatten(structured)}"

    groups, criteria_by_group = _load_active_groups_with_criteria(db)
    if cover_letter.job_group and cover_letter.job_group.is_active:
        job_group = cover_letter.job_group
    else:
        job_group = _choose_job_group(groups, criteria_by_group, desired_job, corpus)
        if not job_group:
            raise CareerDiagnosisConfigError("입력 자료에서 직무군을 판단할 수 없습니다. 자소서 직무군을 확인해주세요.")

    criteria = criteria_by_group.get(job_group.id, [])
    if not criteria:
        raise CareerDiagnosisConfigError("선택된 직무군의 진단 기준이 없습니다.")

    criteria_results = [
        _score_criterion(criterion, structured, content, answer_units)
        for criterion in criteria
    ]
    llm_reviews = _run_llm_review(job_group, criteria_results, resume.content or "", answer_units)
    criteria_results = _apply_llm_review(criteria_results, llm_reviews)
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
    strength_names = set(strengths)
    weaknesses = [
        item["criterion_name"]
        for item in sorted_results
        if item["criterion_name"] not in strength_names and item["score"] < 65
    ][:3]
    action_plan = _build_action_plan(db, job_group.id, sorted_results)

    target = desired_job or job_group.name
    strength_sentence = (
        f"{', '.join(strengths)}은 강점으로 보입니다."
        if strengths
        else "아직 뚜렷한 강점은 부족합니다."
    )
    weakness_sentence = (
        f"{', '.join(weaknesses)}은 우선 보완할 항목입니다."
        if weaknesses
        else "뚜렷한 약점은 적지만, 선택한 직무에 맞춘 사례 근거를 계속 보완해보세요."
    )
    summary = (
        f"{target} 기준 종합 취업 준비도는 {total_score}점입니다. "
        f"{_score_label(total_score)} "
        f"{strength_sentence} "
        f"{weakness_sentence}"
    )

    payload = {
        "job_group": {
            "id": job_group.id,
            "name": job_group.name,
            "description": job_group.description,
        },
        "source_cover_letter": {
            "id": cover_letter.id,
            "title": cover_letter.title,
            "company_name": cover_letter.company_name,
            "job_group_id": cover_letter.job_group_id,
        },
        "desired_job": desired_job,
        "total_score": total_score,
        "score_label": _score_label(total_score),
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "criteria_results": criteria_results,
        "action_plan": action_plan,
        "llm_reviewed": bool(llm_reviews),
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

