# app/api/resume.py
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.repository.database import get_db
from app.repository.resume import ResumeQuestion
from app.schemas.resume_question import (
    ResumeQuestionCreate,
    ResumeQuestionListResponse,
    ResumeQuestionOut,
)
from app.services.interview.question_generator import QuestionTypeClassifier
from app.services.user.dependencies import get_current_user
from app.services.resume import resume_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _serialize_resume(resume) -> dict:
    return {
        "id": resume.id,
        "user_id": resume.user_id,
        "filename": resume.filename,
        "content": resume.content,
        "structured": resume.structured,
        "questions_generated": resume.questions_generated,
    }


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
    structured = resume_service.try_structure(db, resume)
    # 구조화가 됐으면 이어서 질문도 만들어 둔다. 실패하면 첫 조회 때 재시도한다.
    questions_generated = (
        resume_service.try_generate_questions(db, resume) if structured else False
    )
    resume_status = resume_service.get_resume_status(db, user_id)
    logger.info(
        "이력서 저장 완료 (user_id=%s, resume_id=%s, structured=%s, questions=%s)",
        user_id, resume.id, structured, questions_generated,
    )
    return {
        "message": "이력서가 등록되었습니다.",
        "resume_id": resume.id,
        "structured": structured,
        "questions_generated": questions_generated,
        **resume_status,
    }


@router.get("/resume")
def get_resume(db: Session = Depends(get_db), user_id=Depends(get_current_user)):
    resume = resume_service.get_resume(db, user_id)
    if not resume or not resume.content:
        raise HTTPException(status_code=404, detail="등록된 이력서가 없습니다.")
    return _serialize_resume(resume)


@router.patch("/resume")
def update_resume(
    resume_text: str = Form(...),
    filename: str = Form(None),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    text = (resume_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="이력서 텍스트가 비어 있습니다.")

    if not resume_service.has_resume(db, user_id):
        raise HTTPException(status_code=404, detail="등록된 이력서가 없습니다.")

    resume = resume_service.upsert_resume(db, user_id, content=text, filename=filename)
    structured = resume_service.try_structure(db, resume)
    questions_generated = (
        resume_service.try_generate_questions(db, resume) if structured else False
    )
    return {
        "message": "이력서가 수정되었습니다.",
        "resume_id": resume.id,
        "structured": structured,
        "questions_generated": questions_generated,
        **resume_service.get_resume_status(db, user_id),
        "resume": _serialize_resume(resume),
    }


@router.delete("/resume", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(db: Session = Depends(get_db), user_id=Depends(get_current_user)):
    try:
        resume_service.delete_resume(db, user_id)
    except resume_service.ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/resume/status")
def resume_status(db: Session = Depends(get_db), user_id=Depends(get_current_user)):
    return resume_service.get_resume_status(db, user_id)


# ---------- 질문 풀 CRUD ----------

def _get_owned_question(db: Session, user_id: int, question_id: int) -> ResumeQuestion:
    """요청자의 이력서에 속한 질문만 돌려준다. 아니면 404."""
    resume = resume_service.get_resume(db, user_id)
    question = (
        db.query(ResumeQuestion)
        .filter(ResumeQuestion.id == question_id)
        .first()
        if resume else None
    )
    if not question or question.resume_id != resume.id:
        raise HTTPException(status_code=404, detail="질문을 찾을 수 없습니다.")
    return question


def _reject_default(question: ResumeQuestion) -> None:
    if question.is_default:
        raise HTTPException(status_code=400, detail="기본 자기소개 질문은 수정하거나 삭제할 수 없습니다.")


@router.get("/resume/questions", response_model=ResumeQuestionListResponse)
def list_resume_questions(db: Session = Depends(get_db), user_id=Depends(get_current_user)):
    """이력서에 저장된 질문 목록. 아직 생성 전이면 이 시점에 생성한다."""
    try:
        questions = resume_service.ensure_questions(db, user_id)
    except resume_service.ResumeNotFoundError:
        raise HTTPException(status_code=400, detail="이력서를 먼저 등록해주세요.")

    resume = resume_service.get_resume(db, user_id)
    return ResumeQuestionListResponse(
        resume_id=resume.id,
        questions=[ResumeQuestionOut.model_validate(q) for q in questions],
    )


@router.post("/resume/questions", response_model=ResumeQuestionOut, status_code=status.HTTP_201_CREATED)
def create_resume_question(
    payload: ResumeQuestionCreate,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    """사용자가 직접 쓴 질문을 풀에 추가한다. 유형은 LLM이 분류한다.

    의미가 겹치는지는 검사하지 않는다 (중복 판정은 LLM 생성 경로에서만 한다).
    """
    resume = resume_service.get_resume(db, user_id)
    if not resume or not resume.content:
        raise HTTPException(status_code=400, detail="이력서를 먼저 등록해주세요.")

    text = payload.question_text.strip()
    question = ResumeQuestion(
        resume_id=resume.id,
        question_text=text,
        question_type=QuestionTypeClassifier().classify(text),
        is_default=False,
        sort_order=max((q.sort_order for q in resume.questions), default=0) + 1,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return ResumeQuestionOut.model_validate(question)


@router.patch("/resume/questions/{question_id}", response_model=ResumeQuestionOut)
def update_resume_question(
    question_id: int,
    payload: ResumeQuestionCreate,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    """질문 내용을 고친다. 내용이 바뀌었으므로 유형도 다시 분류한다."""
    question = _get_owned_question(db, user_id, question_id)
    _reject_default(question)

    text = payload.question_text.strip()
    question.question_text = text
    question.question_type = QuestionTypeClassifier().classify(text)
    db.commit()
    db.refresh(question)
    return ResumeQuestionOut.model_validate(question)


@router.delete("/resume/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume_question(
    question_id: int,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    """질문을 풀에서 영구 삭제한다."""
    question = _get_owned_question(db, user_id, question_id)
    _reject_default(question)
    db.delete(question)
    db.commit()
