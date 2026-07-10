# app/api/routes/cover_letter.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.repository.database import SessionLocal
from app.repository.cover_letter import CoverLetterFeedback
from app.services.user.dependencies import get_current_user

# ⚠️ 아직 만들지 않은 모듈입니다. make_question.py의 InterviewQuestionGenerator처럼
#    클래스 기반으로 만들지, 함수로 만들지는 agents/service 설계할 때 다시 확인해요.
from app.services.cover_letter.feedback_service import run_cover_letter_feedback

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CoverLetterFeedbackRequest(BaseModel):
    company_name: str
    job_role: str
    question_type: str
    question_text: str
    existing_answer: str


@router.post("/cover-letter/feedback")
def create_feedback(
    request: CoverLetterFeedbackRequest,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    print("자소서 첨삭 시작")

    # 1) 기업 리서치 + 질문유형별 agent 실행 (make_question.py의 Generator처럼 서비스에 위임)
    result = run_cover_letter_feedback(
        company_name=request.company_name,
        job_role=request.job_role,
        question_type=request.question_type,
        question_text=request.question_text,
        existing_answer=request.existing_answer,
    )

    if result is None:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 질문 유형입니다: {request.question_type}")

    print("첨삭 완료")
    print("-" * 50)
    print(result["feedback"])

    # 2) DB 저장 (interview.py와 동일하게 router에서 직접 처리)
    row = CoverLetterFeedback(
        user_id=user_id,
        company_name=request.company_name,
        job_role=request.job_role,
        question_type=request.question_type,
        question_text=request.question_text,
        existing_answer=request.existing_answer,
        agent_used=result["agent_used"],
        feedback=result["feedback"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "company_name": row.company_name,
        "question_type": row.question_type,
        "agent_used": row.agent_used,
        "feedback": row.feedback,
    }


@router.get("/cover-letter/feedback/me")
def my_feedback_history(db: Session = Depends(get_db), user_id=Depends(get_current_user)):
    rows = (
        db.query(CoverLetterFeedback)
        .filter(CoverLetterFeedback.user_id == user_id)
        .order_by(CoverLetterFeedback.created_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "company_name": r.company_name,
            "question_type": r.question_type,
            "agent_used": r.agent_used,
            "feedback": r.feedback,
            "created_at": r.created_at,
        }
        for r in rows
    ]