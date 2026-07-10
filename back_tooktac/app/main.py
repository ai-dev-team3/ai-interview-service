import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

from app.config import CORS_ALLOWED_ORIGINS, validate_settings

validate_settings()

from app.api import audio_router
from app.api import video_router
from app.api import signup_router
from app.api import user_router
from app.api import resume_router
from app.api import interview_router
from app.api import result_router
from app.api import report_router
from app.api import training_page_router
from app.api import rank_router
from app.api import interview_schedule_router
import app.repository.model_registry


app = FastAPI()

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
app.include_router(result_router)
app.include_router(report_router)
app.include_router(training_page_router)
app.include_router(rank_router)
app.include_router(interview_schedule_router)
