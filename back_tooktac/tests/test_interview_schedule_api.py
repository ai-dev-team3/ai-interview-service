"""면접 일정 API 테스트"""
from datetime import date, datetime, time, timedelta

from app.repository.user import InterviewSchedule, User


def _create_other_user(db_session) -> User:
    user = User(
        username="other-user",
        password="pw1234",
        name="다른 사용자",
        nickname="다른",
        email="other@example.com",
        birthdate=date(2000, 1, 1),
        desired_job="백엔드 개발자",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_interview_schedule_requires_auth(client):
    res = client.post(
        "/interview-schedules",
        json={"scheduled_at": "2026-07-20", "description": "면접"},
    )
    assert res.status_code == 401


def test_create_interview_schedule_persists_for_current_user(auth_client, db_session, test_user):
    scheduled_date = date.today() + timedelta(days=7)

    res = auth_client.post(
        "/interview-schedules",
        json={
            "scheduled_at": scheduled_date.strftime("%Y-%m-%d"),
            "description": "  우수성과 공유 컨퍼런스  ",
        },
    )

    assert res.status_code == 201
    body = res.json()["data"]
    assert body["scheduled_at"] == f"{scheduled_date.isoformat()}T00:00:00"
    assert body["description"] == "우수성과 공유 컨퍼런스"

    schedule = db_session.query(InterviewSchedule).one()
    assert schedule.user_id == test_user.username
    assert schedule.scheduled_at == datetime.combine(scheduled_date, time.min)
    assert schedule.description == "우수성과 공유 컨퍼런스"


def test_create_interview_schedule_rejects_invalid_date(auth_client):
    res = auth_client.post(
        "/interview-schedules",
        json={"scheduled_at": "not-a-date", "description": "면접"},
    )
    assert res.status_code == 400
    assert "날짜" in res.json()["detail"]


def test_list_interview_schedules_orders_future_and_excludes_past(
    auth_client,
    db_session,
    test_user,
):
    today = date.today()
    schedules = [
        InterviewSchedule(
            user_id=test_user.username,
            scheduled_at=datetime.combine(today - timedelta(days=1), time(hour=10)),
            description="지난 일정",
        ),
        InterviewSchedule(
            user_id=test_user.username,
            scheduled_at=datetime.combine(today + timedelta(days=2), time(hour=10)),
            description="두 번째 일정",
        ),
        InterviewSchedule(
            user_id=test_user.username,
            scheduled_at=datetime.combine(today, time(hour=9)),
            description="첫 번째 일정",
        ),
    ]
    db_session.add_all(schedules)
    db_session.commit()

    res = auth_client.get("/interview-schedules")

    assert res.status_code == 200
    data = res.json()["data"]
    assert [item["description"] for item in data] == ["첫 번째 일정", "두 번째 일정"]

    res = auth_client.get("/interview-schedules", params={"include_past": True})

    assert res.status_code == 200
    data = res.json()["data"]
    assert [item["description"] for item in data] == ["지난 일정", "첫 번째 일정", "두 번째 일정"]


def test_update_interview_schedule_for_current_user(auth_client, db_session, test_user):
    schedule = InterviewSchedule(
        user_id=test_user.username,
        scheduled_at=datetime.combine(date.today() + timedelta(days=3), time(hour=9)),
        description="기존 일정",
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    new_date = date.today() + timedelta(days=10)
    res = auth_client.patch(
        f"/interview-schedules/{schedule.id}",
        json={
            "scheduled_at": new_date.strftime("%Y-%m-%d"),
            "description": "  최종 면접  ",
        },
    )

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["scheduled_at"] == f"{new_date.isoformat()}T00:00:00"
    assert body["description"] == "최종 면접"

    db_session.refresh(schedule)
    assert schedule.scheduled_at == datetime.combine(new_date, time.min)
    assert schedule.description == "최종 면접"


def test_update_interview_schedule_requires_auth(client):
    res = client.patch(
        "/interview-schedules/1",
        json={"scheduled_at": "2026-07-20", "description": "면접"},
    )

    assert res.status_code == 401


def test_update_interview_schedule_rejects_invalid_date(auth_client, db_session, test_user):
    original_at = datetime.combine(date.today() + timedelta(days=3), time(hour=9))
    schedule = InterviewSchedule(
        user_id=test_user.username,
        scheduled_at=original_at,
        description="기존 일정",
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    res = auth_client.patch(
        f"/interview-schedules/{schedule.id}",
        json={"scheduled_at": "not-a-date", "description": "수정 시도"},
    )

    assert res.status_code == 400
    assert "날짜" in res.json()["detail"]

    db_session.refresh(schedule)
    assert schedule.scheduled_at == original_at
    assert schedule.description == "기존 일정"


def test_update_interview_schedule_rejects_other_user_schedule(auth_client, db_session):
    other_user = _create_other_user(db_session)
    schedule = InterviewSchedule(
        user_id=other_user.username,
        scheduled_at=datetime.combine(date.today() + timedelta(days=3), time(hour=9)),
        description="다른 사람 일정",
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    res = auth_client.patch(
        f"/interview-schedules/{schedule.id}",
        json={"description": "바꿀 수 없음"},
    )

    assert res.status_code == 404


def test_delete_interview_schedule_for_current_user(auth_client, db_session, test_user):
    schedule = InterviewSchedule(
        user_id=test_user.username,
        scheduled_at=datetime.combine(date.today() + timedelta(days=3), time(hour=9)),
        description="삭제할 일정",
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)
    schedule_id = schedule.id

    res = auth_client.delete(f"/interview-schedules/{schedule_id}")

    assert res.status_code == 204
    assert (
        db_session.query(InterviewSchedule)
        .filter(InterviewSchedule.id == schedule_id)
        .first()
        is None
    )


def test_delete_interview_schedule_requires_auth(client):
    res = client.delete("/interview-schedules/1")

    assert res.status_code == 401


def test_delete_interview_schedule_returns_404_for_missing_schedule(auth_client):
    res = auth_client.delete("/interview-schedules/999999")

    assert res.status_code == 404


def test_delete_interview_schedule_rejects_other_user_schedule(auth_client, db_session):
    other_user = _create_other_user(db_session)
    schedule = InterviewSchedule(
        user_id=other_user.username,
        scheduled_at=datetime.combine(date.today() + timedelta(days=3), time(hour=9)),
        description="다른 사람 일정",
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    res = auth_client.delete(f"/interview-schedules/{schedule.id}")

    assert res.status_code == 404
    assert (
        db_session.query(InterviewSchedule)
        .filter(InterviewSchedule.id == schedule.id)
        .first()
        is not None
    )
