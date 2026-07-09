# app/api/result.py
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.repository.database import get_db
from app.repository.analysis import EvaluationResult, VideoEvaluationResult
from app.repository.interview import InterviewQuestion, InterviewAnswer
from app.schemas.result import FullResultResponse, SpeechLabels, VideoSummary
from app.services.interview.session_service import resolve_session
from app.services.user.dependencies import get_current_user
from app.services.score.scoring import QuestionTypeWeights

logger = logging.getLogger(__name__)

router = APIRouter(tags=["result"])


@router.get("/result/full/latest", response_model=FullResultResponse)
def get_full_latest_result(
    session_id: int | None = Query(None, description="명시하면 해당 세션 기준, 없으면 최신 세션"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    logger.debug("/result/full/latest user_id=%s session_id=%s", user_id, session_id)
    # 1. 세션 결정 (명시 session_id 우선, 소유권 검증 포함)
    latest_session = resolve_session(db, user_id, session_id)
    if not latest_session:
        raise HTTPException(status_code=404, detail="latest_session 없음")

    # 2. 가장 마지막 질문 가져오기
    latest_question = (
        db.query(InterviewQuestion)
        .filter_by(session_id=latest_session.id)
        .order_by(InterviewQuestion.question_order.desc())
        .first()
    )
    if not latest_question:
        raise HTTPException(status_code=404, detail="latest_question 질문 없음")

    # 3. 해당 질문의 답변 (아직 없을 수 있음 — 스키마 기본값으로 방어)
    latest_answer = (
        db.query(InterviewAnswer)
        .filter_by(question_id=latest_question.id)
        .first()
    )

    # 4. 텍스트/음성 평가 결과
    text_result = (
        db.query(EvaluationResult)
        .filter_by(question_id=latest_question.id)
        .order_by(EvaluationResult.created_at.desc())
        .first()
    )

    # 5. 영상 평가 결과
    video_result = (
        db.query(VideoEvaluationResult)
        .filter_by(question_id=latest_question.id)
        .order_by(VideoEvaluationResult.created_at.desc())
        .first()
    )

    # 처리 상태: 평가 행이 없으면 아직 분석 중, 있는데 model_answer가 비면 실패(최소 기록)
    if text_result is None:
        status = "processing"
    elif text_result.model_answer:
        status = "done"
    else:
        status = "failed"

    question_analysis = {
        "type": latest_question.question_type,
        "detailAnalysis": {
            "text": {"score": (text_result.final_text_score or 0) if text_result else 0},
            "voice": {"score": (text_result.final_speech_score or 0) if text_result else 0},
            "video": {"score": (video_result.final_video_score or 0) if video_result else 0}
        }
    }

    weighted_score = QuestionTypeWeights.calculate_weighted_score(question_analysis)

    return FullResultResponse(
        status=status,  # processing | done | failed — 프론트 폴링 종료 판단용
        session_id=latest_session.id,
        question_order=latest_question.question_order,
        question=latest_question.question_text or "",
        user_answer=(latest_answer.answer_text or "") if latest_answer else "",
        model_answer=(text_result.model_answer or "") if text_result else "",
        strengths=text_result.strengths.split("\n") if text_result and text_result.strengths else [],
        improvements=text_result.improvements.split("\n") if text_result and text_result.improvements else [],
        final_feedback=(text_result.final_feedback or "") if text_result else "",
        labels=SpeechLabels(
            speed=(text_result.speed_label or "") if text_result else "",
            fluency=(text_result.fluency_label or "") if text_result else "",
            tone=(text_result.tone_label or "") if text_result else "",
        ),
        video=VideoSummary(
            gaze_score=(video_result.gaze_score or 0) if video_result else 0,
            shoulder_warning=(video_result.shoulder_warning or 0) if video_result else 0,
            hand_warning=(video_result.hand_warning or 0) if video_result else 0,
        ),
        weighted_score=weighted_score,
    )
