# app/api/report.py
"""최종 리포트 생성/조회 엔드포인트.

랭킹(/rank/*)은 rank.py, 훈련 통계(/training/*)는 training_page.py로 분리됨.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.repository.database import get_db
from app.services.interview.session_service import resolve_session
from app.services.user.dependencies import get_current_user
from app.repository.interview import InterviewSession
from app.repository.report import (
    FinalReportSummary, ReportStrength, ReportImprovement,
    ReportAreaScore, ReportQuestionScore
)
from app.services.report.final_report_processor import FinalEvaluationGenerator
from app.services.report.interview_data_formatter import generate_interview_json_from_session
from app.services.report.score_utils import find_area_score
from app.utils.time_utils import kst_day_utc_range

router = APIRouter(tags=["report"])


@router.post("/report/final")
def generate_final_report(
        session_id: int | None = Query(None, description="명시하면 해당 세션 기준, 없으면 최신 세션"),
        db: Session = Depends(get_db),
        user_id: int = Depends(get_current_user)
):
    # 1) 세션 결정 (명시 session_id 우선, 소유권 검증 포함)
    session = resolve_session(db, user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="면접 세션이 없습니다")

    parsed_data = generate_interview_json_from_session(db, session.id)

    generator = FinalEvaluationGenerator()
    report = generator.generate_final_report_from_json(parsed_data)

    # 기존 보고서 제거 후 갱신
    existing_summary = db.query(FinalReportSummary).filter_by(
        user_id=user_id, session_id=session.id
    ).first()
    if existing_summary:
        db.query(ReportStrength).filter_by(report_id=existing_summary.id).delete()
        db.query(ReportImprovement).filter_by(report_id=existing_summary.id).delete()
        db.query(ReportAreaScore).filter_by(report_id=existing_summary.id).delete()
        db.query(ReportQuestionScore).filter_by(report_id=existing_summary.id).delete()
        db.delete(existing_summary)
        db.flush()

    summary = FinalReportSummary(
        user_id=user_id,
        session_id=session.id,
        total_score=report["total_evaluation"]["total_score"],
        rank=report["total_evaluation"]["rank"],
        grade=report["total_evaluation"]["grade"],
        grade_message=report["total_evaluation"]["grade_message"],
        personalized_advice=report["ai_advice"]["personalized_message"]
    )
    db.add(summary)
    db.flush()

    for s in report["ai_advice"]["top_strengths"]:
        db.add(ReportStrength(
            report_id=summary.id,
            title=s.get("title", ""),
            description=s.get("description", ""),
            score=s.get("score", 0)
        ))

    for i in report["ai_advice"]["improvements"]:
        db.add(ReportImprovement(
            report_id=summary.id,
            priority=i.get("priority", 1),
            title=i.get("title", ""),
            description=i.get("description", ""),
            score=i.get("score", 0)
        ))

    for area_name, area_score in report["area_scores"].items():
        db.add(ReportAreaScore(
            report_id=summary.id,
            area_name=area_name,
            score=area_score
        ))

    for idx, q in enumerate(report["question_scores"]):
        summary_data = q.get("summary", "")
        summary_value = summary_data if isinstance(summary_data, (dict, list, str)) else str(summary_data)
        db.add(ReportQuestionScore(
            report_id=summary.id,
            question_order=idx + 1,
            question_name=q.get("name", ""),
            question_type=q.get("type", ""),
            question_text=q.get("question", ""),
            user_answer=q.get("my_answer", ""),
            model_answer=q.get("model_answer", ""),
            score=q.get("score", 0),
            summary=summary_value
        ))

    db.commit()

    return {
        "evaluationData": {
            "totalScore": report["total_evaluation"]["total_score"],
            "rank": report["total_evaluation"]["rank"],
            "grade": report["total_evaluation"]["grade"],
            "gradeMessage": report["total_evaluation"]["grade_message"],
            "areaScores": report["area_scores"],
            "questionScores": [
                {
                    "name": q.get("name", ""),
                    "score": q.get("score", 0),
                    "type": q.get("type", ""),
                    "question": q.get("question", ""),
                    "myAnswer": q.get("my_answer", ""),
                    "modelAnswer": q.get("model_answer", ""),
                    "summary": q.get("summary", "")
                }
                for q in report["question_scores"]
            ]
        },
        "aiAdvice": {
            "personalizedMessage": report["ai_advice"]["personalized_message"],
            "topStrengths": report["ai_advice"]["top_strengths"],
            "improvements": report["ai_advice"]["improvements"]
        }
    }


# ---------------------------------------------------
# 날짜별 상세 리포트: areas 숫자만 보장하도록 보정 (응답 포맷 유지)
# ---------------------------------------------------
@router.get("/report/date/{date}")
def get_report_by_date(
        date: str,
        db: Session = Depends(get_db),
        user_id: int = Depends(get_current_user)
):
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요.")

    # started_at은 UTC 저장이므로 KST 하루 구간을 UTC로 환산해 조회
    day_start, day_end = kst_day_utc_range(target_date)
    session = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.user_id == user_id,
            InterviewSession.started_at >= day_start,
            InterviewSession.started_at < day_end,
        )
        .order_by(InterviewSession.started_at.desc())
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="해당 날짜의 면접 기록이 없습니다.")

    summary = db.query(FinalReportSummary).filter_by(
        user_id=user_id, session_id=session.id
    ).first()
    if not summary:
        raise HTTPException(status_code=404, detail="해당 세션의 보고서를 찾을 수 없습니다.")

    strengths = db.query(ReportStrength).filter_by(report_id=summary.id).all()
    improvements = db.query(ReportImprovement).filter_by(report_id=summary.id).all()
    area_scores = db.query(ReportAreaScore).filter_by(report_id=summary.id).all()

    return {
        "success": True,
        "data": {
            "totalScore": summary.total_score,
            "rank": summary.rank,
            "areas": {
                "text": find_area_score(area_scores, "text"),
                "voice": find_area_score(area_scores, "voice"),
                "video": find_area_score(area_scores, "video"),
                "emotion": find_area_score(area_scores, "emotion"),
            },
            "topStrengths": [s.description for s in strengths],
            "improvements": [i.description for i in improvements],
            "aiAdvice": summary.personalized_advice
        }
    }
