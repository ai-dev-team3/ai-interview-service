"""면접 세션 조회 헬퍼.

기존에는 모든 진입점(audio/video/result/report)이 '사용자의 최신 세션'을
암묵적으로 추정해 탭 2개·면접 재시작 시 답변이 엉뚱한 세션에 붙을 수 있었다.
session_id가 명시되면 소유권 검증 후 해당 세션을, 없으면 최신 세션을 반환한다.
"""
from sqlalchemy.orm import Session

from app.repository.interview import InterviewSession


def resolve_session(db: Session, user_id: int, session_id: int | None = None) -> InterviewSession | None:
    """session_id가 있으면 본인 소유 세션을 조회, 없으면 최신 세션 폴백.

    명시된 session_id가 본인 것이 아니거나 없으면 None (폴백하지 않음 —
    잘못된 세션에 데이터가 붙는 것을 방지).
    """
    if session_id is not None:
        return (
            db.query(InterviewSession)
            .filter(InterviewSession.id == session_id, InterviewSession.user_id == user_id)
            .first()
        )
    return (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id)
        # started_at이 초 단위라 같은 초에 생성된 세션은 id로 순서 보장
        .order_by(InterviewSession.started_at.desc(), InterviewSession.id.desc())
        .first()
    )
