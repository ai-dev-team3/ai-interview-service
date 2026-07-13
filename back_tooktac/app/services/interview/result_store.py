"""답변·평가 결과 저장.

연습(웹소켓)과 실전(REST)이 같이 쓴다.

결과 행이 없으면 프론트는 그것을 "아직 분석 중"으로 읽고 계속 기다린다.
그래서 분석이 어떤 이유로 끝나지 못했더라도 행 하나는 반드시 남긴다.
안 그러면 무한 로딩이 된다 — 실제로 겪은 버그다.
"""
import logging

from sqlalchemy.orm import Session

from app.repository.analysis import EvaluationResult
from app.repository.interview import InterviewAnswer

logger = logging.getLogger(__name__)


def save_answer(db: Session, session_id: int, question, user_id: int, text: str) -> None:
    db.add(InterviewAnswer(
        session_id=session_id,
        question_id=question.id,
        question_order=question.question_order,
        user_id=user_id,
        answer_text=text,
    ))
    db.commit()


def save_minimal_result(
    db: Session,
    user_id: int,
    session_id: int,
    question,
    reason: str,
    speech_scores: dict | None = None,
    labels: dict | None = None,
    total_speech: int | None = None,
) -> None:
    """분석이 끝나지 못했을 때 남기는 최소 결과. status가 failed로 보이게 된다."""
    speech_scores = speech_scores or {}
    labels = labels or {}
    db.add(EvaluationResult(
        user_id=user_id,
        session_id=session_id,
        question_id=question.id,
        question_order=question.question_order,
        similarity=0.0,
        intent_score=0.0,
        knowledge_score=0.0,
        final_text_score=0,
        model_answer="",
        strengths=f"{reason} - 강점 파악 불가",
        improvements=f"{reason} - 개선점 파악 불가",
        final_feedback=f"{reason}로 인해 텍스트 평가가 수행되지 않았습니다.",
        speed_score=speech_scores.get("speed", 0),
        filler_score=speech_scores.get("filler", 0),
        pitch_score=speech_scores.get("pitch", 0),
        final_speech_score=total_speech if total_speech is not None else 0,
        speed_label=labels.get("speed", "없음"),
        fluency_label=labels.get("fluency", "없음"),
        tone_label=labels.get("tone", "없음"),
    ))
    db.commit()


def save_result_if_missing(
    db: Session | None, user_id, session_id, question, reason: str
) -> None:
    """이미 결과가 있으면 덮어쓰지 않는다. 질문을 특정하기 전에 실패했다면 남길 곳이 없다."""
    if db is None or user_id is None or session_id is None or question is None:
        return

    try:
        exists = db.query(EvaluationResult).filter_by(question_id=question.id).first()
        if exists is not None:
            return
        save_minimal_result(db, user_id, session_id, question, reason=reason)
        logger.info("최소 결과 저장 (question_id=%s, reason=%s)", question.id, reason)
    except Exception:
        logger.exception("최소 결과 저장 실패 (question_id=%s)", question.id)
        db.rollback()
