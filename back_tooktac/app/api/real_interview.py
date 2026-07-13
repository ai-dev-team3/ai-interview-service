"""실전 면접 API.

핵심은 답변 처리를 두 갈래로 나누는 것이다.

  빠른 길 (사용자를 기다리게 한다 — 준비 시간 10초 예산)
      SenseVoice STT      90초 답변에 약 1초 (실측)
      꼬리질문 판단·생성   2~4초
      -> 다음 질문을 응답으로 바로 준다

  느린 길 (백그라운드, 사용자는 모른다)
      pitch 분석 · LLM 평가(약 17초) -> EvaluationResult 저장

연습 면접은 이 둘을 한 소켓 안에서 직렬로 돌아 문항마다 20초씩 멈춘다.
실전에서는 그러면 안 된다.
"""
import asyncio
import logging
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.services.interview.result_store import (
    save_answer,
    save_minimal_result,
    save_result_if_missing,
)
from app.repository.analysis import EvaluationResult
from app.repository.database import SessionLocal, get_db
from app.repository.interview import InterviewQuestion, InterviewSession
from app.schemas.interview import (
    AnalysisStatusResponse,
    InterviewQuestionOut,
    RealAnswerResponse,
    RealInterviewStartResponse,
)
from app.services.interview import real_interview
from app.services.interview.followup import FollowUpQuestionAgent
from app.services.interview.plan import (
    MAX_INTERVIEW_QUESTIONS,
    MODE_REAL,
    REAL_ANSWER_SECONDS,
    REAL_PREPARE_SECONDS,
)
from app.services.resume import resume_service
from app.services.speech.answer_pipeline import (
    AnswerAnalysisPipeline,
    AudioConversionError,
    FfmpegNotFoundError,
)
from app.services.user.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/real-interview", tags=["real-interview"])


def _load_session(db: Session, user_id: int, session_id: int) -> InterviewSession:
    session = (
        db.query(InterviewSession)
        .filter_by(id=session_id, user_id=user_id, mode=MODE_REAL)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="실전 면접 세션을 찾을 수 없습니다.")
    return session


@router.post("/start", response_model=RealInterviewStartResponse)
def start_real_interview(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    """실전 면접을 시작하고 첫 질문만 돌려준다.

    질문은 서버가 이력서 풀에서 고른다. 다음 질문은 답변을 받은 뒤에야 정해진다
    (꼬리질문이 붙을 수 있으므로).
    """
    try:
        pool = resume_service.ensure_questions(db, user_id)
    except resume_service.ResumeNotFoundError:
        raise HTTPException(status_code=400, detail="이력서를 먼저 등록해주세요.")

    session = InterviewSession(user_id=user_id, mode=MODE_REAL)
    db.add(session)
    db.flush()

    first = real_interview.next_pool_question(db, session.id, pool)
    if first is None:
        raise HTTPException(status_code=400, detail="면접에 쓸 질문이 없습니다.")

    question = real_interview.add_question(
        db, session, first.question_text, first.question_type
    )

    logger.info("실전 면접 시작 (user_id=%s, session_id=%s, 풀=%d개)",
                user_id, session.id, len(pool))

    return RealInterviewStartResponse(
        session_id=session.id,
        max_questions=MAX_INTERVIEW_QUESTIONS,
        prepare_seconds=REAL_PREPARE_SECONDS,
        answer_seconds=REAL_ANSWER_SECONDS,
        question=InterviewQuestionOut.model_validate(question),
    )


@router.post("/answer", response_model=RealAnswerResponse)
async def submit_answer(
    session_id: int = Query(...),
    question_order: int = Query(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    """답변을 받아 다음 질문을 즉시 돌려준다. 무거운 분석은 백그라운드로 넘긴다."""
    session = _load_session(db, user_id, session_id)
    question = (
        db.query(InterviewQuestion)
        .filter_by(session_id=session.id, question_order=question_order)
        .first()
    )
    if not question:
        raise HTTPException(status_code=404, detail="질문을 찾을 수 없습니다.")

    data = await audio.read()
    webm_path, wav_path = _temp_paths(data)

    pipeline = AnswerAnalysisPipeline.for_real_interview()

    try:
        await pipeline.convert_webm_to_wav(webm_path, wav_path)
    except (FfmpegNotFoundError, AudioConversionError) as e:
        logger.error("실전 면접 오디오 변환 실패: %s", e)
        _cleanup(webm_path, wav_path)
        save_minimal_result(db, user_id, session.id, question, reason="오디오 변환 실패")
        return await _advance(db, session, user_id, transcript="")

    # --- 빠른 길: 사용자를 기다리게 하는 구간 ---
    text, stt_raw = await pipeline.transcribe(wav_path)
    if text:
        save_answer(db, session.id, question, user_id, text)

    # --- 느린 길: 사용자는 이미 다음 질문을 받는다 ---
    asyncio.create_task(
        _analyze_in_background(
            pipeline, wav_path, webm_path, stt_raw, text,
            question.question_text, question.question_type,
            user_id, session.id, question.id, question.question_order,
        )
    )

    return await _advance(db, session, user_id, transcript=text, question=question)


async def _advance(
    db: Session,
    session: InterviewSession,
    user_id: int,
    transcript: str,
    question: InterviewQuestion | None = None,
) -> RealAnswerResponse:
    """다음 질문을 정한다. 꼬리질문이 먼저, 없으면 풀에서 하나."""
    asked = len(real_interview.asked_questions(db, session.id))
    if asked >= MAX_INTERVIEW_QUESTIONS:
        return RealAnswerResponse(transcript=transcript, finished=True)

    # 1) 꼬리질문을 물을 가치가 있는가
    if question is not None and transcript:
        follow_up = await asyncio.to_thread(
            FollowUpQuestionAgent().generate, question.question_text, transcript
        )
        if follow_up is not None:
            created = real_interview.add_question(
                db, session, follow_up.question_text, follow_up.question_type
            )
            return RealAnswerResponse(
                transcript=transcript,
                finished=False,
                is_follow_up=True,
                question=InterviewQuestionOut.model_validate(created),
            )

    # 2) 풀에서 다음 질문
    pool = resume_service.ensure_questions(db, user_id)
    nxt = real_interview.next_pool_question(db, session.id, pool)
    if nxt is None:
        return RealAnswerResponse(transcript=transcript, finished=True)

    created = real_interview.add_question(db, session, nxt.question_text, nxt.question_type)
    return RealAnswerResponse(
        transcript=transcript,
        finished=False,
        question=InterviewQuestionOut.model_validate(created),
    )


async def _analyze_in_background(
    pipeline: AnswerAnalysisPipeline,
    wav_path: str,
    webm_path: str,
    stt_raw: dict,
    text: str,
    question_text: str,
    question_type: str,
    user_id: int,
    session_id: int,
    question_id: int,
    question_order: int,
) -> None:
    """면접이 진행되는 동안 뒤에서 도는 분석.

    여기서 실패해도 면접은 멈추지 않는다. 다만 결과 행을 남기지 않으면 마지막
    대기 화면이 영원히 끝나지 않으므로, 어떤 경우에도 행 하나는 남긴다.
    """
    db = SessionLocal()
    try:
        question = db.query(InterviewQuestion).filter_by(id=question_id).first()
        if question is None:
            return

        if not text:
            save_minimal_result(db, user_id, session_id, question, reason="음성 인식 불가")
            return

        feedback, evaluation = await pipeline.analyze_and_evaluate(
            wav_path, stt_raw, text, question_text, question_type
        )
        labels = feedback.get("labels", {}) or {}
        score_detail = feedback.get("score_detail", {}) or {}
        total_speech = feedback.get("total_score", 0) or 0

        if evaluation is None:
            save_minimal_result(
                db, user_id, session_id, question,
                reason="LLM 평가 실패",
                speech_scores=score_detail, labels=labels, total_speech=total_speech,
            )
            return

        db.add(EvaluationResult(
            user_id=user_id,
            session_id=session_id,
            question_id=question_id,
            question_order=question_order,
            similarity=evaluation.get("similarity", 0.0),
            intent_score=evaluation.get("intent_score", 0.0),
            knowledge_score=evaluation.get("knowledge_score", 0.0),
            final_text_score=evaluation.get("final_score", 0),
            model_answer=evaluation.get("model_answer", "") or "",
            strengths="\n".join(evaluation.get("feedback", {}).get("strengths", [])),
            improvements="\n".join(evaluation.get("feedback", {}).get("improvements", [])),
            final_feedback=evaluation.get("feedback", {}).get("final_feedback", "") or "",
            speed_score=score_detail.get("speed"),
            filler_score=score_detail.get("filler"),
            pitch_score=score_detail.get("pitch"),
            final_speech_score=total_speech,
            speed_label=labels.get("speed"),
            fluency_label=labels.get("fluency"),
            tone_label=labels.get("tone"),
        ))
        db.commit()
        logger.info("백그라운드 분석 완료 (session_id=%s, order=%s)", session_id, question_order)

    except Exception:
        logger.exception("백그라운드 분석 실패 (session_id=%s, order=%s)", session_id, question_order)
        db.rollback()
        question = db.query(InterviewQuestion).filter_by(id=question_id).first()
        _save_result_if_missing(db, user_id, _Ref(session_id), question, reason="분석 오류")
    finally:
        db.close()
        _cleanup(wav_path, webm_path)


@router.get("/analysis-status", response_model=AnalysisStatusResponse)
def analysis_status(
    session_id: int = Query(...),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    """마지막 대기 화면용. 몇 문항의 분석이 끝났는지."""
    session = _load_session(db, user_id, session_id)

    total = len(real_interview.asked_questions(db, session.id))
    done = db.query(EvaluationResult).filter_by(session_id=session.id).count()

    return AnalysisStatusResponse(
        session_id=session.id,
        total=total,
        done=done,
        finished=done >= total,
    )


def _temp_paths(data: bytes) -> tuple[str, str]:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
        webm_path = f.name
    return webm_path, webm_path.replace(".webm", ".wav")


def _cleanup(*paths: str) -> None:
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
