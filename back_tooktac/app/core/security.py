from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.config import JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = "HS256"

def create_access_token(user_id: int, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + expires_delta
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("user_id not found in token")
        return int(user_id)
    except JWTError:
        raise ValueError("Invalid JWT token")
