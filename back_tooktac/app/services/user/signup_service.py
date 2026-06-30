# services/signup_service.py

from sqlalchemy.orm import Session
from app.repository.user import User

def register_user_with_resume(
    db: Session,
    username: str,
    password: str,
    name: str,
    nickname: str,
    email: str,
    birthdate: str,
    desired_job: str,
    resume_text: str = None,
) -> User:
    from app.repository.resume import Resume
    from datetime import datetime

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

    if resume_text:
        resume_entry = Resume(
            user_id=user.id,
            filename=None,
            content=resume_text,
            structured=None,
        )
        db.add(resume_entry)
        db.commit()

    return user
