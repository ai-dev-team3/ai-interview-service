from sqlalchemy.orm import Session
from app.repository.user import User
from app.core.password import hash_password, is_bcrypt_hash, verify_password
from app.core.security import create_access_token
from datetime import datetime, timezone

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None

    if is_bcrypt_hash(user.password):
        if not verify_password(password, user.password):
            return None
    else:
        # 레거시 평문 비밀번호 — 일치하면 이번 로그인에서 해시로 마이그레이션
        if user.password != password:
            return None
        user.password = hash_password(password)

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(user_id=user.id)
    return {
        "access_token": access_token,
        "user_id": user.id
    }
