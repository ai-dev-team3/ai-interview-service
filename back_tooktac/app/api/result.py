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


@router.get("/result/full", response_model=FullResultResponse)
def get_full_result(
    question_order: int = Query(..., ge=1, description="조회할 질문 순번 (1부터)"),
    session_id: int | None = Query(None, description="명시하면 해당 세션 기준, 없으면 최신 세션"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """특정 질문 하나의 분석 결과.

    세션의 모든 질문은 면접 시작 시점에 한꺼번에 만들어진다. 따라서 "가장 마지막
    질문"이 아니라 방금 답한 질문을 명시해야 한다. 그러지 않으면 1번을 답해도
    마지막 질문의 결과(=아직 없음)를 보게 되어 프론트가 영원히 폴링한다.
    """
    logger.debug("/result/full user_id=%s session_id=%s order=%s",
                 user_id, session_id, question_order)
    # 1. 세션 결정 (명시 session_id 우선, 소유권 검증 포함)
    latest_session = resolve_session(db, user_id, session_id)
    if not latest_session:
        raise HTTPException(status_code=404, detail="latest_session 없음")

    # 2. 요청된 순번의 질문 (같은 order가 여럿이면 최신 것)
    latest_question = (
        db.query(InterviewQuestion)
        .filter_by(session_id=latest_session.id, question_order=question_order)
        .order_by(InterviewQuestion.id.desc())
        .first()
    )
    if not latest_question:
        raise HTTPException(status_code=404, detail=f"{question_order}번 질문 없음")

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
