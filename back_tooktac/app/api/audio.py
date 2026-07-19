from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.repository.interview import InterviewQuestion
from app.services.interview.result_store import (
    save_answer as _save_answer,
    save_minimal_result as _save_minimal_result,
    save_result_if_missing,
)
from app.observability import PRACTICE_INTERVIEW, feature
from app.services.interview.session_service import resolve_session
from app.services.speech.answer_pipeline import (
    AnswerAnalysisPipeline,
    AudioConversionError,
    FfmpegNotFoundError,
)
from app.utils.auth_ws import get_user_id_from_websocket
import logging
import tempfile
import os
import asyncio
from app.repository.database import SessionLocal
from app.repository.analysis import EvaluationResult

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/transcript")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    db: Session | None = None
    webm_path = None
    wav_path = None
    # 예외/연결 끊김 처리에서 최소 결과를 남기려면 여기서 선초기화해야 한다
    user_id: int | None = None
    session = None
    question = None

    try:
        # 1) 인증
        user_id = await get_user_id_from_websocket(websocket)

        # 2) 쿼리스트링의 question_id는 실제로 question_order 값
        #    e.g. /ws/transcript?question_id=3  -> 3번째 질문(질문 순서 3)
        qorder_str = websocket.query_params.get("question_id") or websocket.query_params.get("questionId")
        if not qorder_str or not qorder_str.isdigit():
            await websocket.send_json({"error": "question_id(=question_order)가 유효하지 않습니다."})
            return
        question_order = int(qorder_str)

        # 2-1) session_id가 명시되면 해당 세션 사용 (없으면 최신 세션 폴백)
        sid_str = websocket.query_params.get("session_id")
        explicit_session_id = int(sid_str) if sid_str and sid_str.isdigit() else None

        # 3) DB 세션
        db = SessionLocal()

        # 4) 세션 결정 (명시 session_id 우선, 소유권 검증 포함)
        session = resolve_session(db, user_id, explicit_session_id)
        if not session:
            await websocket.send_json({"error": "세션을 찾을 수 없습니다."})
            return

        # 5) 최신 세션 내에서 question_order로 질문 조회
        question = (
            db.query(InterviewQuestion)
            .filter(
                InterviewQuestion.session_id == session.id,
                InterviewQuestion.question_order == question_order
            )
            .first()
        )
        if not question:
            await websocket.send_json({"error": f"세션 {session.id}에서 question_order={question_order} 질문을 찾을 수 없습니다."})
            return

        # 6) 오디오 수신
        data = await websocket.receive_bytes()
        logger.info("오디오 수신 %.0f KB (question_id=%s)", len(data) / 1024, question.id)
        if not data:
            _save_minimal_result(db, user_id, session.id, question, reason="빈 오디오")
            await websocket.send_json({"transcript": "", "feedback": _empty_feedback("오디오 데이터가 없습니다.")})
            return

        # 7) 임시 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
            webm_path = f.name

        wav_path = webm_path.replace(".webm", ".wav")

        pipeline = AnswerAnalysisPipeline()

        # 8) ffmpeg 변환
        try:
            await pipeline.convert_webm_to_wav(webm_path, wav_path)
        except FfmpegNotFoundError:
            logger.error("ffmpeg를 찾을 수 없습니다. 서버에 ffmpeg 설치가 필요합니다 (README 참고).")
            _save_minimal_result(db, user_id, session.id, question, reason="ffmpeg 미설치")
            await websocket.send_json({"transcript": "", "feedback": _empty_feedback("서버 오디오 변환 도구(ffmpeg)가 설치되어 있지 않습니다.")})
            return
        except AudioConversionError:
            _save_minimal_result(db, user_id, session.id, question, reason="ffmpeg 변환 실패")
            await websocket.send_json({"transcript": "", "feedback": _empty_feedback("ffmpeg 변환 실패")})
            return

        # 9) STT (Clova)
        text_clean, clova_raw = await pipeline.transcribe(wav_path)

        if text_clean == "":
            _save_answer(db, session.id, question, user_id, "")
            _save_minimal_result(db, user_id, session.id, question, reason="음성 인식 불가")
            await websocket.send_json({"transcript": "", "feedback": _empty_feedback("음성 인식이 되지 않았습니다.")})
            return

        # 10) 답변 저장 후 Vito STT·pitch 분석·LLM 평가 병렬 실행
        _save_answer(db, session.id, question, user_id, text_clean)

        # 평가 파이프라인은 실전 면접과 공유한다 — 여기서 온 호출만 '연습면접'으로 기록된다.
        with feature(PRACTICE_INTERVIEW):
            sf, ev = await pipeline.analyze_and_evaluate(
                wav_path, clova_raw, text_clean,
                question.question_text, question.question_type,
            )
        labels = sf.get("labels", {}) or {}
        score_detail = sf.get("score_detail", {}) or {}
        total_score = sf.get("total_score", 0) or 0

        # 11) LLM 평가 실패 시 음성 분석 결과만이라도 저장
        if ev is None:
            _save_minimal_result(
                db, user_id, session.id, question,
                reason="LLM 평가 실패",
                speech_scores=score_detail, labels=labels, total_speech=total_score
            )
            await websocket.send_json({"transcript": text_clean, "feedback": sf})
            return

        # 12) 최종 EvaluationResult 저장
        er = EvaluationResult(
            user_id=user_id,
            session_id=session.id,
            question_id=question.id,
            question_order=question.question_order,
            similarity=ev.get("similarity", 0.0),
            intent_score=ev.get("intent_score", 0.0),
            knowledge_score=ev.get("knowledge_score", 0.0),
            final_text_score=ev.get("final_score", 0),
            model_answer=ev.get("model_answer", "") or "",
            strengths="\n".join(ev.get("feedback", {}).get("strengths", [])),
            improvements="\n".join(ev.get("feedback", {}).get("improvements", [])),
            final_feedback=ev.get("feedback", {}).get("final_feedback", "") or "",
            speed_score=score_detail.get("speed"),
            filler_score=score_detail.get("filler"),
            pitch_score=score_detail.get("pitch"),
            final_speech_score=total_score,
            speed_label=labels.get("speed"),
            fluency_label=labels.get("fluency"),
            tone_label=labels.get("tone")
        )
        db.add(er)
        db.commit()

        await websocket.send_json({"transcript": text_clean, "feedback": sf})

    except WebSocketDisconnect as disconnect:
        # 오디오를 다 받기 전에 끊기는 일이 실제로 있다.
        # code=1009는 메시지가 uvicorn의 --ws-max-size(기본 16MB)를 넘었다는 뜻이다.
        # 결과 행을 남기지 않으면 /result/full이 영원히 processing을 반환해 무한 로딩이 된다.
        logger.info("WebSocket disconnected (code=%s, reason=%r)", disconnect.code, disconnect.reason)
        save_result_if_missing(db, user_id, session.id if session else None, question, reason="연결이 끊김")
    except Exception as e:
        logger.exception("음성 답변 처리 중 오류 발생")
        if db is not None:
            db.rollback()
        save_result_if_missing(db, user_id, session.id if session else None, question, reason=f"처리 오류({type(e).__name__})")
        try:
            await websocket.send_json({"error": f"internal_error: {type(e).__name__}"})
        except Exception:
            pass
    finally:
        if db is not None:
            db.close()
        for p in (webm_path, wav_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


def _empty_feedback(msg: str) -> dict:
    return {
        "feedback": msg,
        "score_detail": {"speed": 0, "filler": 0, "pitch": 0},
        "total_score_normalized": 0.0
    }
