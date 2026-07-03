"""services/interview/session_service.py — 세션 결정 로직 테스트"""
from datetime import date

from app.repository.interview import InterviewSession
from app.repository.user import User
from app.services.interview.session_service import resolve_session


def _make_session(db, user_id):
    session = InterviewSession(user_id=user_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def test_resolve_latest_when_no_session_id(db_session, test_user):
    first = _make_session(db_session, test_user.id)
    second = _make_session(db_session, test_user.id)

    resolved = resolve_session(db_session, test_user.id)
    # 같은 초에 생성돼도 id 내림차순 타이브레이커로 최신 세션 보장
    assert resolved.id == second.id


def test_resolve_explicit_session_id(db_session, test_user):
    first = _make_session(db_session, test_user.id)
    _make_session(db_session, test_user.id)  # 더 최신 세션이 있어도

    resolved = resolve_session(db_session, test_user.id, session_id=first.id)
    assert resolved.id == first.id


def test_resolve_rejects_other_users_session(db_session, test_user):
    other = User(
        username="other", password="pw", name="다른유저", nickname="남",
        email="other@example.com", birthdate=date(2000, 1, 1), desired_job="기획",
    )
    db_session.add(other)
    db_session.commit()
    others_session = _make_session(db_session, other.id)
    _make_session(db_session, test_user.id)

    # 명시된 세션이 남의 것이면 최신 세션으로 폴백하지 않고 None
    assert resolve_session(db_session, test_user.id, session_id=others_session.id) is None


def test_resolve_none_when_no_sessions(db_session, test_user):
    assert resolve_session(db_session, test_user.id) is None
