"""실전 면접 진행 규칙.

연습 면접과 다른 점:
  - 질문을 미리 만들어두지 않는다. 이력서와 지금까지의 대화를 보고 매번 새로 만든다.
    같은 이력서라도 대화 흐름에 따라 다른 질문이 나온다.
  - 문항 수가 아니라 '시간'이 기준이다. 짧게 답하면 문항이 늘고, 길게 답하면 준다.
    어느 쪽이든 12분 안팎에서 끝난다.
  - 마지막은 "하고 싶은 말"로 마무리한다. 이건 채점하지 않으므로 질문 행으로도
    만들지 않는다 (interview_session.closing_remark 에 전사만 남긴다).

상태를 따로 저장하지 않는다.
  진행 상황은 이미 DB 에 있는 질문·답변 행에서 매번 다시 읽으면 된다.
  서버가 재시작해도 면접이 깨지지 않는다.
"""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.repository.interview import InterviewAnswer, InterviewQuestion, InterviewSession
from app.services.interview.plan import (
    REAL_MAX_QUESTIONS,
    REAL_TIME_BUDGET_SECONDS,
)
from app.utils.time_utils import utcnow_naive

logger = logging.getLogger(__name__)


def asked_questions(db: Session, session_id: int) -> list[InterviewQuestion]:
    return (
        db.query(InterviewQuestion)
        .filter_by(session_id=session_id)
        .order_by(InterviewQuestion.question_order.asc())
        .all()
    )


def conversation(db: Session, session_id: int) -> list[tuple[str, str]]:
    """[(질문, 답변), ...] 순서대로. 다음 질문을 만들 때 통째로 LLM 에 넣는다."""
    questions = asked_questions(db, session_id)
    answers = {
        a.question_id: (a.answer_text or "")
        for a in db.query(InterviewAnswer).filter_by(session_id=session_id).all()
    }
    return [(q.question_text, answers.get(q.id, "")) for q in questions]


def elapsed_seconds(session: InterviewSession, now: datetime | None = None) -> int:
    started = session.started_at or utcnow_naive()
    return int(((now or utcnow_naive()) - started).total_seconds())


def remaining_seconds(session: InterviewSession) -> int:
    return max(0, REAL_TIME_BUDGET_SECONDS - elapsed_seconds(session))


def should_close(db: Session, session: InterviewSession) -> bool:
    """이제 마무리 질문으로 갈 때인가.

    시간이 다 됐거나, 안전 상한에 닿았으면 끝낸다. 상한은 답변이 계속 무음으로
    끝나 시간이 거의 안 흐르는 경우를 위한 것이다.
    """
    if elapsed_seconds(session) >= REAL_TIME_BUDGET_SECONDS:
        return True
    return len(asked_questions(db, session.id)) >= REAL_MAX_QUESTIONS


def add_question(
    db: Session,
    session: InterviewSession,
    text: str,
    qtype: str,
    is_follow_up: bool = False,
) -> InterviewQuestion:
    """다음 순번으로 질문 행을 만든다."""
    order = len(asked_questions(db, session.id)) + 1

    question = InterviewQuestion(
        session_id=session.id,
        question_order=order,
        question_text=text,
        question_type=qtype,
        is_follow_up=is_follow_up,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question
