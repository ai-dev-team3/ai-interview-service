from fastapi import APIRouter, Form, Depends, HTTPException, Response, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app import config
from app.core.password import hash_password, is_bcrypt_hash, verify_password
from app.repository.database import get_db
from app.repository.analysis import EvaluationResult, VideoEvaluationResult
from app.repository.interview import InterviewAnswer, InterviewQuestion, InterviewSession
from app.repository.report import (
    FinalReportSummary,
    ReportAreaScore,
    ReportImprovement,
    ReportQuestionScore,
    ReportStrength,
)
from app.repository.resume import Resume
from app.services.user.login_service import authenticate_user
from app.services.user.dependencies import get_current_user
from app.repository.user import InterviewSchedule, User

router = APIRouter()


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=72)

def _set_access_cookie(response: Response, value: str, max_age: int):
    """login/logout이 같은 속성으로 쿠키를 굽도록 통일 (속성이 다르면 삭제가 안 됨)"""
    response.set_cookie(
        key="access_token",
        value=value,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite=config.COOKIE_SAMESITE,
        path="/",
        domain=config.COOKIE_DOMAIN,
        max_age=max_age,
    )


def _is_valid_password(user: User, password: str) -> bool:
    if is_bcrypt_hash(user.password):
        return verify_password(password, user.password)
    return user.password == password


def _delete_user_related_data(db: Session, user: User) -> None:
    session_ids = [
        row[0]
        for row in db.query(InterviewSession.id)
        .filter(InterviewSession.user_id == user.id)
        .all()
    ]
    question_ids = []
    report_ids = []

    if session_ids:
        question_ids = [
            row[0]
            for row in db.query(InterviewQuestion.id)
            .filter(InterviewQuestion.session_id.in_(session_ids))
            .all()
        ]

    report_ids = [
        row[0]
        for row in db.query(FinalReportSummary.id)
        .filter(FinalReportSummary.user_id == user.id)
        .all()
    ]

    if report_ids:
        for model in (ReportStrength, ReportImprovement, ReportAreaScore, ReportQuestionScore):
            db.query(model).filter(model.report_id.in_(report_ids)).delete(synchronize_session=False)

    db.query(FinalReportSummary).filter(FinalReportSummary.user_id == user.id).delete(synchronize_session=False)
    db.query(EvaluationResult).filter(EvaluationResult.user_id == user.id).delete(synchronize_session=False)
    db.query(VideoEvaluationResult).filter(VideoEvaluationResult.user_id == user.id).delete(synchronize_session=False)
    db.query(InterviewAnswer).filter(InterviewAnswer.user_id == user.id).delete(synchronize_session=False)

    if question_ids:
        db.query(InterviewQuestion).filter(InterviewQuestion.id.in_(question_ids)).delete(synchronize_session=False)

    if session_ids:
        db.query(InterviewSession).filter(InterviewSession.id.in_(session_ids)).delete(synchronize_session=False)

    db.query(Resume).filter(Resume.user_id == user.id).delete(synchronize_session=False)
    db.query(InterviewSchedule).filter(InterviewSchedule.user_id == user.username).delete(synchronize_session=False)

@router.post("/login")
def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    token_data = authenticate_user(db=db, username=username, password=password)
    if not token_data:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    _set_access_cookie(
        response,
        value=token_data["access_token"],
        max_age=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return {"message": "로그인 성공"}

@router.post("/logout")
def logout(response: Response):
    _set_access_cookie(response, value="", max_age=0)
    return {"message": "로그아웃 완료"}

@router.get("/me")
def get_me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    user_obj = db.query(User).filter(User.id == user).first()
    if user_obj is None:
        # 토큰은 유효하지만 사용자가 삭제된 경우
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return {
        "user_id": user_obj.id,
        "username": user_obj.username,
        "nickname": user_obj.nickname,
        "desired_job": user_obj.desired_job,
        "status": "authenticated"
    }

@router.get("/check-username")
def check_username(username: str = Query(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()
    return {"available": existing_user is None}


@router.get("/account")
def get_account(user=Depends(get_current_user), db: Session = Depends(get_db)):
    user_obj = db.query(User).filter(User.id == user).first()
    if user_obj is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

    return {
        "user_id": user_obj.id,
        "username": user_obj.username,
        "nickname": user_obj.nickname,
        "email": user_obj.email,
        "desired_job": user_obj.desired_job,
    }


@router.patch("/account/password")
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    user_obj = db.query(User).filter(User.id == user).first()
    if user_obj is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

    if not _is_valid_password(user_obj, payload.current_password):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다.")

    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="새 비밀번호는 현재 비밀번호와 달라야 합니다.")

    user_obj.password = hash_password(payload.new_password)
    db.commit()
    return {"message": "비밀번호가 변경되었습니다."}


@router.delete("/account")
def delete_account(
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    user_obj = db.query(User).filter(User.id == user).first()
    if user_obj is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

    try:
        _delete_user_related_data(db, user_obj)
        db.delete(user_obj)
        db.commit()
    except Exception:
        db.rollback()
        raise

    _set_access_cookie(response, value="", max_age=0)
    return {"message": "회원 탈퇴가 완료되었습니다."}
