# app/api/signup.py

from fastapi import APIRouter, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.repository.database import get_db
from app.services.user.signup_service import (
    DuplicateUserError,
    InvalidSignupInputError,
    register_user,
)

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
    try:
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
    except InvalidSignupInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateUserError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"message": f"{username}님 가입 완료!", "user_id": user.id}
