# app/api/result.py
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.repository.database import get_db
from app.repository.analysis import EvaluationResult, VideoEvaluationResult
from app.repository.interview import InterviewSession, InterviewQuestion, InterviewAnswer
from app.schemas.result import FullResultResponse, SpeechLabels, VideoSummary
from app.services.user.dependencies import get_current_user
from app.services.score.scoring import QuestionTypeWeights

logger = logging.getLogger(__name__)

router = APIRouter(tags=["result"])


@router.get("/result/full/latest", response_model=FullResultResponse)
def get_full_latest_result(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    logger.debug("/result/full/latest user_id=%s", user_id)
    # 1. 가장 최근 세션 가져오기
    latest_session = (
        db.query(InterviewSession)
        .filter_by(user_id=user_id)
        .order_by(InterviewSession.started_at.desc())
        .first()
    )
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

    question_analysis = {
        "type": latest_question.question_type,
        "detailAnalysis": {
            "text": {"score": (text_result.final_text_score or 0) if text_result else 0},
            "voice": {"score": (text_result.final_speech_score or 0) if text_result else 0},
            "emotion": {"score": (video_result.emotion_score or 0) if video_result else 0},
            "video": {"score": (video_result.final_video_score or 0) if video_result else 0}
        }
    }

    weighted_score = QuestionTypeWeights.calculate_weighted_score(question_analysis)

    return FullResultResponse(
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
        best_emotion=(video_result.emotion_best or "") if video_result else "",
        weighted_score=weighted_score,
    )
