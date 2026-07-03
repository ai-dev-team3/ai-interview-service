# services/signup_service.py

from datetime import datetime

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.password import hash_password
from app.repository.user import User


class DuplicateUserError(Exception):
    """username 또는 email이 이미 사용 중"""


class InvalidSignupInputError(Exception):
    """이메일/생년월일 등 입력 형식 오류"""


def register_user(
    db: Session,
    username: str,
    password: str,
    name: str,
    nickname: str,
    email: str,
    birthdate: str,
    desired_job: str,
) -> User:
    # 1) 입력 형식 검증
    try:
        email = validate_email(email, check_deliverability=False).normalized
    except EmailNotValidError:
        raise InvalidSignupInputError("이메일 형식이 올바르지 않습니다.")

    try:
        birthdate_parsed = datetime.strptime(birthdate, "%Y-%m-%d").date()
    except ValueError:
        raise InvalidSignupInputError("생년월일 형식이 올바르지 않습니다. (YYYY-MM-DD)")

    # 2) 중복 검사 (레이스는 아래 IntegrityError로 재차 방어)
    if db.query(User).filter(User.username == username).first():
        raise DuplicateUserError("이미 사용 중인 아이디입니다.")
    if db.query(User).filter(User.email == email).first():
        raise DuplicateUserError("이미 사용 중인 이메일입니다.")

    user = User(
        username=username,
        password=hash_password(password),
        name=name,
        nickname=nickname,
        email=email,
        birthdate=birthdate_parsed,
        desired_job=desired_job
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateUserError("이미 사용 중인 아이디 또는 이메일입니다.")
    db.refresh(user)

    return user
