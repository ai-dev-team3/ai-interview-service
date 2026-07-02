from fastapi import APIRouter, Form, Depends, HTTPException, Response, Query, Request
from sqlalchemy.orm import Session
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.repository.database import get_db
from app.services.user.login_service import authenticate_user
from app.services.user.dependencies import get_current_user
from app.repository.user import User

router = APIRouter()

def _set_access_cookie(response: Response, origin: str, value: str, max_age: int):
    """login/logout이 같은 속성으로 쿠키를 굽도록 통일 (속성이 다르면 삭제가 안 됨)"""
    if "tooktac.shop" in origin:
        # production (tooktac.shop)
        response.set_cookie(
            key="access_token",
            value=value,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            domain=".tooktac.shop",
            max_age=max_age,
        )
    else:
        # local development (localhost)
        response.set_cookie(
            key="access_token",
            value=value,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
            max_age=max_age,
        )

@router.post("/login")
def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    token_data = authenticate_user(db=db, username=username, password=password)
    if not token_data:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    origin = request.headers.get("origin", "")
    _set_access_cookie(
        response, origin,
        value=token_data["access_token"],
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return {"message": "로그인 성공"}

@router.post("/logout")
def logout(request: Request, response: Response):
    origin = request.headers.get("origin", "")
    _set_access_cookie(response, origin, value="", max_age=0)
    return {"message": "로그아웃 완료"}

@router.get("/me")
def get_me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    user_obj = db.query(User).filter(User.id == user).first()
    return {
        "user_id": user_obj.id,
        "nickname": user_obj.nickname,
        "desired_job": user_obj.desired_job,
        "status": "authenticated"
    }

@router.get("/check-username")
def check_username(username: str = Query(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()
    return {"available": existing_user is None}