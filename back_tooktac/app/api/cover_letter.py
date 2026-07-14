from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.repository.database import get_db
from app.services.cover_letter import cover_letter_service
from app.services.user.dependencies import get_current_user

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])


def _serialize_cover_letter(cover_letter) -> dict:
    return {
        "id": cover_letter.id,
        "user_id": cover_letter.user_id,
        "company_name": cover_letter.company_name,
        "job_group_id": cover_letter.job_group_id,
        "title": cover_letter.title,
        "question_text": cover_letter.question_text,
        "answer_text": cover_letter.answer_text,
        "items": cover_letter_service.split_cover_letter_pairs(cover_letter),
        "created_at": cover_letter.created_at.isoformat() if cover_letter.created_at else None,
    }


@router.get("")
def list_cover_letters(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    rows = cover_letter_service.list_cover_letters(db, user_id)
    return [_serialize_cover_letter(row) for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_cover_letter(
    question_text: list[str] = Form(...),
    answer_text: list[str] = Form(...),
    job_group_id: int = Form(...),
    title: str | None = Form(None),
    company_name: str | None = Form(None),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    try:
        cover_letter = cover_letter_service.create_cover_letter(
            db,
            user_id,
            question_texts=question_text,
            answer_texts=answer_text,
            job_group_id=job_group_id,
            title=title,
            company_name=company_name,
        )
    except cover_letter_service.CoverLetterValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_cover_letter(cover_letter)


@router.patch("/{cover_letter_id}")
def update_cover_letter(
    cover_letter_id: int,
    question_text: list[str] = Form(...),
    answer_text: list[str] = Form(...),
    job_group_id: int = Form(...),
    title: str | None = Form(None),
    company_name: str | None = Form(None),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    try:
        cover_letter = cover_letter_service.update_cover_letter(
            db,
            user_id,
            cover_letter_id,
            question_texts=question_text,
            answer_texts=answer_text,
            job_group_id=job_group_id,
            title=title,
            company_name=company_name,
        )
    except cover_letter_service.CoverLetterNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except cover_letter_service.CoverLetterValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_cover_letter(cover_letter)


@router.delete("/{cover_letter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cover_letter(
    cover_letter_id: int,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    try:
        cover_letter_service.delete_cover_letter(db, user_id, cover_letter_id)
    except cover_letter_service.CoverLetterNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
