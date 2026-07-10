"""면접 일정 API 테스트"""
from datetime import date, datetime, time, timedelta

from app.repository.user import InterviewSchedule


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
