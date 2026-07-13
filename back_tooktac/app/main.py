import logging
import threading
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)

from app.config import CORS_ALLOWED_ORIGINS, validate_settings

validate_settings()

from app.api import audio_router
from app.api import video_router
from app.api import signup_router
from app.api import user_router
from app.api import resume_router
from app.api import interview_router
from app.api import real_interview_router
from app.api import result_router
from app.api import report_router
from app.api import training_page_router
from app.api import rank_router
from app.api import interview_schedule_router
import app.repository.model_registry


def _warm_up_embedding_models() -> None:
    """답변 평가에 쓰는 임베딩 모델 2개를 미리 올린다.

    로드에 6초쯤 걸리는데, 이걸 첫 답변 제출 때 하면 그 사용자가 비용을 뒤집어쓴다.
    서버를 막지 않도록 백그라운드 스레드에서 올린다. 사용자는 준비 30초 +
    답변 90초를 거친 뒤에야 이 모델을 쓰므로 그 전에 끝난다.
    """
    import time

    from app.services.speech.answer_pipeline import get_orchestrator_singleton

    started = time.perf_counter()
    try:
        get_orchestrator_singleton()
    except Exception:
        logger.warning("임베딩 모델 워밍업 실패 — 첫 답변 때 다시 로드한다", exc_info=True)
        return
    logger.info("임베딩 모델 워밍업 완료 (%.1f초)", time.perf_counter() - started)


def _warm_up_sensevoice() -> None:
    """실전 면접의 STT 모델을 미리 올린다 (첫 실행이면 내려받기까지).

    실전에서는 꼬리질문이 직전 답변의 STT를 기다린다. 첫 사용자가 모델 로딩(+다운로드)
    까지 뒤집어쓰면 준비 시간 10초를 한참 넘긴다. GPU가 없으면 CPU로 떨어지므로
    실패해도 서버는 뜬다.
    """
    from app.services.stt.sensevoice import warm_up

    warm_up()


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_warm_up_embedding_models, name="model-warmup", daemon=True).start()
    threading.Thread(target=_warm_up_sensevoice, name="sensevoice-warmup", daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)

origins = CORS_ALLOWED_ORIGINS

# ✅ CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 미처리 예외를 CORS 헤더 붙은 명시적 500으로 변환 (Network Error 방지)
from app.core.error_handlers import register_exception_handlers

register_exception_handlers(app, origins)

# WebSocket 라우터 포함
app.include_router(audio_router)
app.include_router(video_router)
app.include_router(signup_router)
app.include_router(user_router)
app.include_router(resume_router)
app.include_router(interview_router)
app.include_router(real_interview_router)
app.include_router(result_router)
app.include_router(report_router)
app.include_router(training_page_router)
app.include_router(rank_router)
app.include_router(interview_schedule_router)
