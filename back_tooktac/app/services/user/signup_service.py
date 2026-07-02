# services/signup_service.py

from datetime import datetime

from sqlalchemy.orm import Session
from app.repository.user import User


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
    user = User(
        username=username,
        password=password,
        name=name,
        nickname=nickname,
        email=email,
        birthdate=datetime.strptime(birthdate, "%Y-%m-%d").date(),
        desired_job=desired_job
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user
