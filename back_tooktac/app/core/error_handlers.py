"""전역 예외 핸들러.

미처리 예외가 ServerErrorMiddleware까지 올라가면 CORSMiddleware를 우회해
CORS 헤더 없는 500이 되고, 브라우저는 이를 차단해 axios 'Network Error'로 보인다.
여기서 허용된 origin에 한해 CORS 헤더를 직접 붙여 명시적인 500 JSON을 반환한다.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI, allowed_origins: list[str]) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("미처리 예외 (%s %s)", request.method, request.url.path)

        headers = {}
        origin = request.headers.get("origin")
        if origin in allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Vary"] = "Origin"

        return JSONResponse(
            status_code=500,
            content={"detail": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."},
            headers=headers,
        )
