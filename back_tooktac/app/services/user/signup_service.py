# services/signup_service.py

from sqlalchemy.orm import Session
from fastapi import UploadFile
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
    resume: UploadFile = None,
    skip_structure: bool = False
) -> User:
    from app.repository.user import User
    from app.repository.resume import Resume
    from datetime import datetime

    resume_text = ""
    structured_data = None

    if resume:
        resume.file.seek(0)
        resume_text = resume.file.read().decode(errors="ignore")[:2000]  # 임시로 텍스트 일부 저장
        resume.file.seek(0)  # 포인터 복원

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

    if resume:
        resume_entry = Resume(
            user_id=user.id,
            filename=resume.filename,
            # content=resume_text,
            content = "개인정보",
            structured=None if skip_structure else structured_data
        )
        db.add(resume_entry)
        db.commit()

    return user
