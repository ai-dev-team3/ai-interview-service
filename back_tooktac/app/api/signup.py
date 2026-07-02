# app/api/signup.py

from fastapi import APIRouter, Form, Depends
from sqlalchemy.orm import Session
from app.repository.database import get_db
from app.services.user.signup_service import register_user

router = APIRouter()

@router.post("/signup")
async def signup(
    username: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    nickname: str = Form(...),
    email: str = Form(...),
    birthdate: str = Form(...),
    desiredJob: str = Form(...),
    db: Session = Depends(get_db)
):
    user = register_user(
        db=db,
        username=username,
        password=password,
        name=name,
        nickname=nickname,
        email=email,
        birthdate=birthdate,
        desired_job=desiredJob,
    )

    return {"message": f"{username}님 가입 완료!", "user_id": user.id}
