# app/api/routes/interview.py
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.services.text.make_question import InterviewQuestionGenerator
from app.repository.interview import InterviewSession, InterviewQuestion
from app.services.interview.session_service import resolve_session
from app.repository.database import get_db
from app.services.interview.plan import QUESTION_FLOW
from app.services.user.dependencies import get_current_user
from app.services.resume import resume_service
from app.services.resume.resume_service import ResumeNotFoundError
from app.services.resume.structurer import ResumeStructuringError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["interview"])


def _load_parsed_resume(db, user_id) -> dict:
    """구조화 이력서를 로드(필요 시 생성)해 질문 생성기 입력 형태로 반환"""
    try:
        structured = resume_service.ensure_structured(db, user_id)
    except ResumeNotFoundError:
        raise HTTPException(status_code=400, detail="이력서를 먼저 등록해주세요.")
    except ResumeStructuringError:
        raise HTTPException(status_code=500, detail="이력서 분석에 실패했습니다. 잠시 후 다시 시도해주세요.")
    return {"structured_content": structured}


def _generate_question(db, generator, parsed, session_id: int, order: int) -> dict:
    """QUESTION_FLOW 설정에 따라 order에 맞는 질문을 생성"""
    flow = QUESTION_FLOW.get(order)
    if not flow:
        raise HTTPException(status_code=400, detail="지원하지 않는 질문 순서")

    method = getattr(generator, flow["method"])
    refs = flow["refs"]
    if refs is None:
        return method(parsed)

    # 꼬리물기: 참조 질문·답변을 함께 전달
    ref_args = []
    for ref_order in refs:
        ref_q = db.query(InterviewQuestion).filter_by(
            session_id=session_id, question_order=ref_order
        ).first()
        if not ref_q:
            raise HTTPException(
                status_code=400,
                detail=f"꼬리물기 질문에 필요한 {ref_order}번 질문이 없습니다."
            )
        ref_a = ref_q.answer.answer_text if ref_q.answer else ""
        ref_args.extend([ref_q.question_text, ref_a])
    return method(parsed, *ref_args)


@router.post("/start-interview")
def start_interview(db: Session = Depends(get_db), user_id=Depends(get_current_user)):
    logger.info("질문 생성 시작 (user_id=%s)", user_id)
    # 인터뷰 세션 생성
    session = InterviewSession(user_id=user_id)
    db.add(session)
    db.flush()  # session.id 사용 가능

    # 질문 생성기
    parsed = _load_parsed_resume(db, user_id)
    generator = InterviewQuestionGenerator()
    q1 = _generate_question(db, generator, parsed, session.id, order=1)
    logger.info("질문 생성 완료: %s", q1)
    # DB 저장
    db.add(InterviewQuestion(
        session_id=session.id,
        question_order=1,
        question_text=q1["question"],
        question_type=q1["question_type"]
    ))
    db.commit()

    return {
        "session_id": session.id,
        "question": q1["question"]
    }


@router.post("/generate-question/{order}")
def generate_next_question(
    order: int,
    session_id: int | None = Query(None, description="명시하면 해당 세션에 질문 추가, 없으면 최신 세션"),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    # 세션 결정 (명시 session_id 우선, 소유권 검증 포함)
    session = resolve_session(db, user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션 없음")

    if order == 1:
        raise HTTPException(status_code=400, detail="1번 질문은 /start-interview로 생성하세요.")

    parsed = _load_parsed_resume(db, user_id)
    generator = InterviewQuestionGenerator()
    q = _generate_question(db, generator, parsed, session.id, order)

    # DB에 질문 저장
    db.add(InterviewQuestion(
        session_id=session.id,
        question_order=order,
        question_text=q["question"],
        question_type=q["question_type"]
    ))
    db.commit()

    return {
        "session_id": session.id,
        "question": q["question"]
    }
