# app/utils/auth_ws.py
import logging

from fastapi import WebSocket
from app.core.security import SECRET_KEY
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# 시크릿은 core.security와 단일 소스 공유 (fallback 금지)
SECRET = SECRET_KEY
ALGS = ["HS256"]

async def get_user_id_from_websocket(ws: WebSocket) -> int:
    # 1) 쿠키 우선
    token = ws.cookies.get("access_token")

    # 2) Authorization: Bearer xxx
    if not token:
        auth = ws.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()

    # 주의: 쿼리스트링(?token=) 방식은 토큰이 액세스 로그에 남으므로 지원하지 않는다

    if not token:
        raise ValueError("Access token missing")

    try:
        payload = jwt.decode(token, SECRET, algorithms=ALGS)
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")

    sub = payload.get("sub")
    if sub is None:
        raise ValueError("Invalid token payload: sub missing")

    return int(sub)
