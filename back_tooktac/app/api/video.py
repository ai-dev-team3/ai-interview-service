import asyncio
import logging

import cv2  # 폴백 경로의 JPEG 디코딩
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.repository.analysis import VideoEvaluationResult
from app.repository.database import get_db
from app.repository.interview import InterviewQuestion
from app.services.interview.session_service import resolve_session
from app.services.vision.payload import (
    KIND_JPEG,
    KIND_LANDMARKS,
    PayloadError,
    parse_landmarks,
    payload_kind,
)
from app.services.vision.posture_analyzer import (
    PostureCoreModel,
    PostureSessionState,
    to_feedback,
)
from app.services.vision.posture_rules import score_landmarks
from app.utils.auth_ws import get_user_id_from_websocket

logger = logging.getLogger(__name__)

router = APIRouter()

# 전역 MediaPipe 인스턴스는 두지 않는다.
# MediaPipe의 solution 객체는 스레드 안전하지 않고 프레임 간 추적 상태를 갖는다.
# 여러 연결이 공유하면 사용자끼리 결과가 섞인다. 폴백 연결만 자기 인스턴스를 만든다.


def _save_video_result(
    db: Session,
    user_id: int,
    question_order: int,
    posture_state: "PostureSessionState",
    explicit_session_id: int | None = None,
) -> None:
    """질문 종료 시점의 누적 상태를 VideoEvaluationResult로 저장 (세션/질문 없으면 스킵)"""
    final_video = posture_state.finalize()  # 포즈 최종 점수 계산

    # 세션 결정 (명시 session_id 우선, 소유권 검증 포함 / 없으면 최신 세션 폴백)
    session = resolve_session(db, user_id, explicit_session_id)
    if not session:
        return  # 세션 없으면 저장 스킵

    # 해당 세션의 question_order에 해당하는 질문 조회
    # (아이스브레이킹은 question_order=0 이라 여기서 걸러진다 — 저장하지 않는다)
    question = (
        db.query(InterviewQuestion)
        .filter_by(session_id=session.id, question_order=question_order)
        .first()
    )
    if not question:
        return  # 질문 없으면 저장 스킵

    video_result = VideoEvaluationResult(
        user_id=user_id,
        session_id=session.id,
        question_id=question.id,
        question_order=question_order,
        gaze_score=final_video["gaze_rate_score"],
        shoulder_warning=final_video["shoulder_posture_warning_count"],
        hand_warning=final_video["hand_posture_warning_count"],
        posture_score=final_video["shoulder_hand_score"],
        final_video_score=final_video["video_score"],
    )
    db.add(video_result)
    db.commit()


def _analyze_jpeg(core: PostureCoreModel, jpeg: bytes):
    """폴백 경로: 서버가 프레임에서 랜드마크를 뽑아 판정한다."""
    frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise PayloadError("JPEG 디코딩 실패")
    return core.infer_once(frame)


@router.websocket("/ws/expression")
async def expression_socket(websocket: WebSocket):
    await websocket.accept()

    posture_state = PostureSessionState()  # 이 질문 동안만 유지되는 누적 상태
    core: PostureCoreModel | None = None  # 폴백 경로에서만 만든다

    # 인증/파라미터 파싱 전에 예외가 나도 except 블록에서 참조 가능하도록 선초기화
    user_id: int | None = None
    question_order: int | None = None
    explicit_session_id: int | None = None
    frames = 0
    landmark_frames = 0
    jpeg_frames = 0

    db: Session = next(get_db())
    try:
        user_id = await get_user_id_from_websocket(websocket)

        order_str = websocket.query_params.get("question_id")
        if not order_str or not order_str.isdigit():
            await websocket.send_json({"error": "question_order가 유효하지 않습니다."})
            return

        question_order = int(order_str)

        sid_str = websocket.query_params.get("session_id")
        if sid_str and sid_str.isdigit():
            explicit_session_id = int(sid_str)

        while True:
            data = await websocket.receive_bytes()

            try:
                kind = payload_kind(data)
                frames += 1
                # 경로는 도중에 바뀔 수 있다(브라우저가 모델을 올리는 동안은 JPEG).
                # 첫 프레임만 보고 판단하면 오해한다 — 종료 시 둘 다 센 값을 남긴다.
                if kind == KIND_LANDMARKS:
                    landmark_frames += 1
                elif kind == KIND_JPEG:
                    jpeg_frames += 1

                if kind == KIND_LANDMARKS:
                    # 기본 경로: 브라우저가 이미 추론을 끝냈다. 판정만 한다(수 마이크로초).
                    face, pose = parse_landmarks(data)
                    step = score_landmarks(face, pose)
                elif kind == KIND_JPEG:
                    # 폴백 경로: 이 연결 전용 MediaPipe 인스턴스를 늦게 만든다.
                    if core is None:
                        core = PostureCoreModel()
                        logger.info("폴백 경로 진입 — MediaPipe 인스턴스 생성 (user_id=%s)", user_id)
                    # MediaPipe 추론은 동기 CPU 연산 → 이벤트 루프가 멈추지 않도록 워커 스레드로
                    step = await asyncio.to_thread(_analyze_jpeg, core, data[1:])
                else:
                    raise PayloadError(f"알 수 없는 페이로드 종류: {kind}")
            except PayloadError as e:
                await websocket.send_json({"expression": f"프레임 분석 실패: {e}"})
                continue
            except Exception:
                logger.exception("프레임 분석 실패")
                await websocket.send_json({"expression": "프레임 분석 실패"})
                continue

            posture_state.update(step)
            await websocket.send_json({"expression": to_feedback(step)})

    except WebSocketDisconnect:
        logger.info(
            "영상 소켓 종료 (question_order=%s, 프레임 %d개 = 랜드마크 %d + JPEG %d)",
            question_order, frames, landmark_frames, jpeg_frames,
        )
        # 연결 종료 시 이 질문의 최종 결과 저장 (인증/파라미터 확보 전이면 스킵)
        if user_id is not None and question_order is not None:
            _save_video_result(db, user_id, question_order, posture_state, explicit_session_id)

    except Exception:
        logger.exception("영상 분석 중 오류")
        if user_id is not None and question_order is not None:
            _save_video_result(db, user_id, question_order, posture_state, explicit_session_id)

        try:
            await websocket.send_json({"expression": "분석 중 오류 발생"})
        except Exception:
            pass  # 소켓이 이미 닫힌 경우 무시

    finally:
        if core is not None:
            core.close()  # MediaPipe 그래프 해제 (약 57MB)
        try:
            db.close()
        except Exception:
            pass
