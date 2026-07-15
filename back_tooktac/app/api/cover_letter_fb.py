import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.repository.database import get_db
from app.repository.cover_letter_fb import CoverLetterFeedback
from app.services.user.dependencies import get_current_user
from app.services.cover_letter.feedback_service import run_cover_letter_feedback_batch
from app.schemas.cover_letter_fb import (
    CoverLetterFeedbackRequest,
    CoverLetterFeedbackResponse,
    CoverLetterFeedbackUpdateRequest,
    CoverLetterFeedbackHistoryOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cover-letter/feedback", tags=["cover-letter-feedback"])


@router.post("/", response_model=CoverLetterFeedbackResponse)
async def create_feedback(
    request: CoverLetterFeedbackRequest,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    logger.info(
        "자소서 첨삭 시작: user_id=%s, company=%s, 문항 수=%d",
        user_id, request.company_name, len(request.entries),
    )

    # 1) 기업 리서치(1회) + 문항별 트리아지 분류 + specialist agent 첨삭 (병렬)
    results = await run_cover_letter_feedback_batch(
        company_name=request.company_name,
        job_role=request.job_role,
        entries=[entry.model_dump() for entry in request.entries],
    )

    # 2) 문항마다 DB row 저장 (existing_answer는 원본, revised_answer는 AI 재작성본)
    saved_rows = []
    for result in results:
        row = CoverLetterFeedback(
            user_id=user_id,
            company_name=request.company_name,
            job_role=request.job_role,
            question_type=result["question_type"],
            question_text=result["question_text"],
            existing_answer=result["existing_answer"],
            revised_answer=result["revised_answer"],
            agent_used=result["agent_used"],
            feedback=result["feedback"],
        )
        db.add(row)
        saved_rows.append(row)

    db.commit()
    for row in saved_rows:
        db.refresh(row)

    logger.info("자소서 첨삭 완료: user_id=%s, 처리 문항 수=%d", user_id, len(saved_rows))

    return {"items": saved_rows}


@router.patch("/", response_model=CoverLetterFeedbackResponse)
def update_feedback(
    request: CoverLetterFeedbackUpdateRequest,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    """사용자가 결과 화면에서 답변을 더 수정한 뒤 '저장'을 눌렀을 때 revised_answer를 갱신합니다."""
    updated_rows = []
    for item in request.items:
        row = (
            db.query(CoverLetterFeedback)
            .filter(
                CoverLetterFeedback.id == item.id,
                CoverLetterFeedback.user_id == user_id,
            )
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail=f"id={item.id} 항목을 찾을 수 없습니다.")
        row.revised_answer = item.revised_answer
        updated_rows.append(row)

    db.commit()
    for row in updated_rows:
        db.refresh(row)

    logger.info("자소서 답변 저장 완료: user_id=%s, 수정 문항 수=%d", user_id, len(updated_rows))

    return {"items": updated_rows}


@router.get("/me", response_model=list[CoverLetterFeedbackHistoryOut])
def my_feedback_history(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    rows = (
        db.query(CoverLetterFeedback)
        .filter(CoverLetterFeedback.user_id == user_id)
        .order_by(CoverLetterFeedback.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows