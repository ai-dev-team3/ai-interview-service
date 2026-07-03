"""비밀번호 해싱/검증 (bcrypt).

기존 DB에 평문으로 저장된 비밀번호는 로그인 성공 시점에
bcrypt 해시로 자동 마이그레이션한다 (login_service 참고).
"""
import bcrypt

# bcrypt는 72바이트까지만 사용하므로 초과분은 잘라서 일관성 유지
_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode()[:_MAX_BYTES], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:_MAX_BYTES], hashed.encode())
    except ValueError:
        # 저장된 값이 bcrypt 해시 형식이 아님
        return False


def is_bcrypt_hash(value: str) -> bool:
    """DB에 저장된 값이 bcrypt 해시인지 (평문 마이그레이션 판별용)"""
    return value.startswith(("$2a$", "$2b$", "$2y$"))
