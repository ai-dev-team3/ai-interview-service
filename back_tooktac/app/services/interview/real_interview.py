"""실전 면접 진행 규칙.

연습 면접과 다른 점:
  - 서버가 질문을 고른다. 사용자는 미리 보지 못한다.
  - 답변마다 꼬리질문이 붙을 수 있다. 꼬리질문이 붙으면 그만큼 기본 질문을
    덜 묻게 된다 (총 문항 수는 MAX_INTERVIEW_QUESTIONS 를 넘지 않는다).
  - 그래서 질문 행을 시작 시점에 다 만들 수 없다. 진행하면서 하나씩 만든다.

출제 계획을 어디에도 저장하지 않는다.
  "아직 안 물어본 풀 질문 중에서 하나 뽑는다"로 매번 다시 계산하면 되기 때문이다.
  미리 뽑아 두면 그 목록을 컬럼이나 서버 메모리에 들고 있어야 하고, 서버가
  재시작하면 진행 중인 면접이 깨진다. 상태가 없으면 깨질 것도 없다.

질문 행을 미리 다 만들지 않는 것은 오히려 안전하다. 예전 무한 로딩 버그가
'시작 시 N개를 다 만들어서 결과 조회가 항상 마지막 질문을 보던' 데서 나왔다.
"""
import logging
import random

from sqlalchemy.orm import Session

from app.repository.interview import InterviewQuestion, InterviewSession
from app.repository.resume import ResumeQuestion
from app.services.interview.plan import MAX_INTERVIEW_QUESTIONS

logger = logging.getLogger(__name__)


def asked_questions(db: Session, session_id: int) -> list[InterviewQuestion]:
    return (
        db.query(InterviewQuestion)
        .filter_by(session_id=session_id)
        .order_by(InterviewQuestion.question_order.asc())
        .all()
    )


def next_pool_question(
    db: Session, session_id: int, pool: list[ResumeQuestion]
) -> ResumeQuestion | None:
    """아직 안 물어본 풀 질문 중 하나. 없으면 None.

    자기소개(is_default)는 항상 첫 질문이다. 나머지는 무작위로 뽑는다 —
    같은 이력서로 다시 봐도 매번 같은 면접이 되지 않도록.

    이미 물어본 질문은 텍스트로 판별한다. 꼬리질문은 풀에 없는 텍스트이므로
    자연히 풀 질문을 밀어내지 않는다 — 다만 총 문항 수는 함께 센다.
    """
    asked = {q.question_text for q in asked_questions(db, session_id)}

    default = next((q for q in pool if q.is_default), None)
    if default is not None and default.question_text not in asked:
        return default

    remaining = [q for q in pool if not q.is_default and q.question_text not in asked]
    if not remaining:
        return None
    return random.choice(remaining)


def is_finished(db: Session, session_id: int, next_question: object | None) -> bool:
    """더 물을 게 없으면 면접이 끝난다.

    문항 상한에 닿았거나, 물어볼 질문이 남지 않았으면 끝이다.
    """
    if next_question is None:
        return True
    return len(asked_questions(db, session_id)) >= MAX_INTERVIEW_QUESTIONS


def add_question(
    db: Session, session: InterviewSession, text: str, qtype: str
) -> InterviewQuestion:
    """다음 순번으로 질문 행을 만든다."""
    order = len(asked_questions(db, session.id)) + 1

    question = InterviewQuestion(
        session_id=session.id,
        question_order=order,
        question_text=text,
        question_type=qtype,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question
