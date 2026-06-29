from fastapi import Request, HTTPException
from app.core.security import decode_access_token

def get_current_user(request: Request) -> int:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")

    try:
        return decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="토큰 유효성 실패")
