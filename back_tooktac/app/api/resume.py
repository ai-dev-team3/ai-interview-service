# app/api/resume.py
import logging

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.repository.database import get_db
from app.services.user.dependencies import get_current_user
from app.services.resume import resume_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/resume")
def upload_resume(
    resume_text: str = Form(...),
    filename: str = Form(None),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    text = (resume_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="이력서 텍스트가 비어 있습니다.")

    resume = resume_service.upsert_resume(db, user_id, content=text, filename=filename)
    logger.info("이력서 저장 완료 (user_id=%s, resume_id=%s)", user_id, resume.id)
    return {"message": "이력서가 등록되었습니다.", "resume_id": resume.id}


@router.get("/resume/status")
def resume_status(db: Session = Depends(get_db), user_id=Depends(get_current_user)):
    return {"has_resume": resume_service.has_resume(db, user_id)}
