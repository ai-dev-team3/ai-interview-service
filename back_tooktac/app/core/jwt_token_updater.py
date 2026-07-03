"""VITO(리턴제로) JWT 토큰 발급/캐시.

기존에는 토큰을 app/vito_jwt_token.json 파일에 저장했는데,
컨테이너·다중 인스턴스 배포에서 파일 경합/유실 문제가 있어
프로세스 메모리 캐시로 전환했다. 만료 60초 전에 자동 재발급한다.
"""
import logging
import os
import threading
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

_AUTH_URL = "https://openapi.vito.ai/v1/authenticate"
# 만료 직전 요청이 실패하지 않도록 여유를 두고 갱신
_REFRESH_MARGIN = timedelta(seconds=60)


class JwtTokenManager:
    """프로세스 전역 토큰 캐시 (스레드 안전)"""

    _cached_token: str | None = None
    _expires_at: datetime | None = None
    _lock = threading.Lock()

    def __init__(self):
        self.client_id = os.getenv("VITO_CLIENT_ID")
        self.client_secret = os.getenv("VITO_CLIENT_SECRET")

    def get_token(self) -> str:
        """유효한 토큰 반환 (만료 임박 시 재발급)"""
        cls = type(self)
        with cls._lock:
            if cls._cached_token and cls._expires_at and datetime.now() < cls._expires_at - _REFRESH_MARGIN:
                return cls._cached_token

            token_data = self._fetch_token()
            cls._cached_token = token_data["access_token"]
            cls._expires_at = self._resolve_expiry(token_data)
            logger.info("VITO JWT 토큰 발급 완료 (만료: %s)", cls._expires_at)
            return cls._cached_token

    def _fetch_token(self) -> dict:
        """API를 통해 새 JWT 토큰을 요청하고 반환"""
        if not self.client_id or not self.client_secret:
            raise RuntimeError("VITO_CLIENT_ID/VITO_CLIENT_SECRET 환경변수가 설정되지 않았습니다.")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {"Accept": "application/json"}
        logger.info("VITO JWT 토큰 요청 중...")
        response = requests.post(_AUTH_URL, data=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _resolve_expiry(token_data: dict) -> datetime:
        """응답의 expire_at(unix epoch)을 우선 사용, 없으면 6시간 가정"""
        expire_at = token_data.get("expire_at")
        if expire_at:
            try:
                return datetime.fromtimestamp(int(expire_at))
            except (TypeError, ValueError, OSError):
                logger.warning("expire_at 파싱 실패 — 6시간 만료로 가정: %r", expire_at)
        return datetime.now() + timedelta(hours=6)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    print("토큰:", JwtTokenManager().get_token()[:30], "...")
