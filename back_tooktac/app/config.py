"""
프로젝트 전역 설정값 모음.

이 파일을 import해서 쓰면, 모델 이름이나 환경변수 키 이름이 바뀔 때
이 파일 하나만 수정하면 됨 (각 서비스 클래스마다 따로 수정할 필요 없음).
"""

import os

# --- Gemini 관련 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = "gemini-2.5-flash"


def validate_settings() -> None:
    """필수 환경변수가 비어있으면 앱 시작 시점에 바로 에러를 내고 싶을 때 사용."""
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")

    if missing:
        raise RuntimeError(
            f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing)}. "
            f".env 파일을 확인하세요."
        )