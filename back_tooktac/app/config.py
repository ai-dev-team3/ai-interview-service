"""
프로젝트 전역 설정값 모음.

이 파일을 import해서 쓰면, 모델 이름이나 환경변수 키 이름이 바뀔 때
이 파일 하나만 수정하면 됨 (각 서비스 클래스마다 따로 수정할 필요 없음).
"""

import os

# --- LLM 관련 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# gpt-4-turbo → gpt-4o: 동급 품질에 더 저렴하고 빠름
OPENAI_MODEL_NAME = "gpt-4o"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = "gemini-2.5-flash"

# --- 인증 관련 ---
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
# JWT 만료와 쿠키 max_age가 함께 쓰는 단일 기준값 (기존 쿠키 수명 2시간 유지)
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# --- CORS / 쿠키 관련 ---
# 브라우저가 접속하는 프론트 origin 목록 (쉼표 구분).
# 주의: origin은 스킴+호스트(+포트)까지만 유효. path(/api 등)가 붙으면 매칭되지 않음
# 예: CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

# access_token 쿠키 속성.
# 운영(HTTPS): COOKIE_DOMAIN=.example.com, COOKIE_SECURE=true, COOKIE_SAMESITE=none
# 로컬 개발(HTTP): COOKIE_DOMAIN 미설정, COOKIE_SECURE=false, COOKIE_SAMESITE=lax
# .env에 키만 있고 값이 빈 경우("COOKIE_SECURE=")도 미설정으로 취급한다
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "").strip() or None
COOKIE_SECURE = (os.getenv("COOKIE_SECURE", "").strip().lower() or "false") == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "").strip().lower() or "lax"

_VALID_SAMESITE = ("lax", "strict", "none")


def validate_settings() -> None:
    """필수 환경변수가 비어있으면 앱 시작 시점에 바로 에러를 내고 싶을 때 사용."""
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not JWT_SECRET_KEY:
        missing.append("JWT_SECRET_KEY")
    if not CORS_ALLOWED_ORIGINS:
        missing.append("CORS_ALLOWED_ORIGINS")

    if missing:
        raise RuntimeError(
            f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing)}. "
            f".env 파일을 확인하세요."
        )

    if COOKIE_SAMESITE not in _VALID_SAMESITE:
        raise RuntimeError(
            f"COOKIE_SAMESITE는 {_VALID_SAMESITE} 중 하나여야 합니다: {COOKIE_SAMESITE!r}"
        )

    # SameSite=None 쿠키는 Secure가 없으면 브라우저가 조용히 버린다 (로그인 안 됨)
    if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
        raise RuntimeError(
            "COOKIE_SAMESITE=none 은 COOKIE_SECURE=true 와 함께 설정해야 합니다."
        )