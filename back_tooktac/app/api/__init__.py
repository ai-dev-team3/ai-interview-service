"""API 라우터 패키지.

라우터를 lazy 로딩(PEP 562)으로 노출한다.
- `from app.api import audio_router` 형태의 기존 사용법은 그대로 동작
- 테스트 등에서 개별 라우터만 import할 때 video/audio의 무거운 ML 모델
  (YOLO, MediaPipe, torch)이 불필요하게 로드되는 것을 방지
"""
import importlib

_ROUTER_MODULES = {
    "audio_router": ".audio",
    "video_router": ".video",
    "signup_router": ".signup",
    "user_router": ".user",
    "resume_router": ".resume",
    "interview_router": ".interview",
    "result_router": ".result",
    "report_router": ".report",
    "training_page_router": ".training_page",
}

__all__ = list(_ROUTER_MODULES)


def __getattr__(name):
    if name in _ROUTER_MODULES:
        module = importlib.import_module(_ROUTER_MODULES[name], __name__)
        return module.router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
