# app/api/routes/interview.py
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.repository.database import get_db
from app.repository.interview import InterviewQuestion, InterviewSession
from app.repository.resume import ResumeQuestion
from app.schemas.interview import (
    InterviewQuestionOut,
    InterviewStartRequest,
    InterviewStartResponse,
)
from app.services.interview.plan import MAX_INTERVIEW_QUESTIONS
from app.services.interview.session_service import resolve_session
from app.services.resume import resume_service
from app.services.user.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["interview"])


def _ordered_pool_questions(
    resume_questions: list[ResumeQuestion], question_ids: list[int]
) -> list[ResumeQuestion]:
    """요청된 id 순서대로 질문을 늘어놓는다. 기본 자기소개 질문은 항상 맨 앞에 온다.

    id가 풀에 없으면(=남의 질문이거나 삭제됨) 400.
    """
    by_id = {q.id: q for q in resume_questions}
    default = next((q for q in resume_questions if q.is_default), None)

    selected: list[ResumeQuestion] = []
    for qid in question_ids:
        question = by_id.get(qid)
        if question is None:
            raise HTTPException(status_code=400, detail=f"질문 {qid}을(를) 찾을 수 없습니다.")
        if question.is_default:
            continue  # 아래에서 맨 앞에 넣는다
        if question in selected:
            raise HTTPException(status_code=400, detail=f"질문 {qid}이(가) 중복 선택되었습니다.")
        selected.append(question)

    if default is not None:
        selected.insert(0, default)

    if not selected:
        raise HTTPException(status_code=400, detail="질문을 하나 이상 선택해주세요.")
    if len(selected) > MAX_INTERVIEW_QUESTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"질문은 최대 {MAX_INTERVIEW_QUESTIONS}개까지 선택할 수 있습니다.",
        )
    return selected


@router.post("/start-interview", response_model=InterviewStartResponse)
def start_interview(
    payload: InterviewStartRequest,
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    """선택된 질문으로 연습 면접 세션을 만든다.

    질문 텍스트와 유형을 interview_question에 복사해 둔다. 이후 이력서를 다시
    올려 질문 풀이 갈아엎혀도 이 세션의 기록은 그대로 남는다.
    """
    try:
        pool = resume_service.ensure_questions(db, user_id)
    except resume_service.ResumeNotFoundError:
        raise HTTPException(status_code=400, detail="이력서를 먼저 등록해주세요.")

    selected = _ordered_pool_questions(pool, payload.question_ids)

    session = InterviewSession(user_id=user_id)
    db.add(session)
    db.flush()  # session.id 확보

    for order, question in enumerate(selected, start=1):
        db.add(InterviewQuestion(
            session_id=session.id,
            question_order=order,
            question_text=question.question_text,
            question_type=question.question_type,
        ))
    db.commit()

    logger.info("면접 시작 (user_id=%s, session_id=%s, questions=%d)",
                user_id, session.id, len(selected))

    return InterviewStartResponse(
        session_id=session.id,
        total_questions=len(selected),
        questions=[
            InterviewQuestionOut(
                question_order=order,
                question_text=q.question_text,
                question_type=q.question_type,
            )
            for order, q in enumerate(selected, start=1)
        ],
    )


@router.get("/interview/questions", response_model=InterviewStartResponse)
def get_session_questions(
    session_id: int | None = Query(None, description="명시하면 해당 세션, 없으면 최신 세션"),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    """세션의 질문 목록. 새로고침으로 클라이언트 상태를 잃었을 때 복구용."""
    session = resolve_session(db, user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션 없음")

    questions = (
        db.query(InterviewQuestion)
        .filter_by(session_id=session.id)
        .order_by(InterviewQuestion.question_order.asc())
        .all()
    )
    return InterviewStartResponse(
        session_id=session.id,
        total_questions=len(questions),
        questions=[InterviewQuestionOut.model_validate(q) for q in questions],
    )
