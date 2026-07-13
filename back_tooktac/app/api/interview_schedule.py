from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.repository.database import get_db
from app.repository.user import InterviewSchedule, User
from app.services.user.dependencies import get_current_user


router = APIRouter(tags=["interview-schedule"])


class InterviewScheduleCreate(BaseModel):
    scheduled_at: str = Field(..., description="YYYY-MM-DD or ISO datetime")
    description: str | None = Field(default=None, max_length=255)


class InterviewScheduleUpdate(BaseModel):
    scheduled_at: str | None = Field(default=None, description="YYYY-MM-DD or ISO datetime")
    description: str | None = Field(default=None, max_length=255)


def _parse_scheduled_at(value: str) -> datetime:
    raw = value.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="면접 날짜를 입력해주세요.")

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다.")


def _get_current_user_obj(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user


def _get_schedule_for_user(db: Session, schedule_id: int, username: str) -> InterviewSchedule:
    schedule = (
        db.query(InterviewSchedule)
        .filter(
            InterviewSchedule.id == schedule_id,
            InterviewSchedule.user_id == username,
        )
        .first()
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="면접 일정을 찾을 수 없습니다.")
    return schedule


def _serialize_schedule(schedule: InterviewSchedule) -> dict:
    return {
        "id": int(schedule.id),
        "scheduled_at": schedule.scheduled_at.isoformat(),
        "description": schedule.description,
    }


@router.get("/interview-schedules")
def list_interview_schedules(
    include_past: bool = Query(False),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    user = _get_current_user_obj(db, user_id)
    query = db.query(InterviewSchedule).filter(InterviewSchedule.user_id == user.username)

    if not include_past:
        today_start = datetime.combine(date.today(), time.min)
        query = query.filter(InterviewSchedule.scheduled_at >= today_start)

    schedules = query.order_by(InterviewSchedule.scheduled_at.asc()).all()
    return {"data": [_serialize_schedule(schedule) for schedule in schedules]}


@router.post("/interview-schedules", status_code=201)
def create_interview_schedule(
    payload: InterviewScheduleCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    user = _get_current_user_obj(db, user_id)
    description = payload.description.strip() if payload.description else None
    scheduled_at = _parse_scheduled_at(payload.scheduled_at)

    schedule = InterviewSchedule(
        user_id=user.username,
        scheduled_at=scheduled_at,
        description=description or None,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return {"data": _serialize_schedule(schedule)}


@router.patch("/interview-schedules/{schedule_id}")
def update_interview_schedule(
    schedule_id: int,
    payload: InterviewScheduleUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    user = _get_current_user_obj(db, user_id)
    schedule = _get_schedule_for_user(db, schedule_id, user.username)
    changes = payload.model_dump(exclude_unset=True)

    if "scheduled_at" in changes:
        if payload.scheduled_at is None:
            raise HTTPException(status_code=400, detail="면접 날짜를 입력해주세요.")
        schedule.scheduled_at = _parse_scheduled_at(payload.scheduled_at)

    if "description" in changes:
        description = payload.description.strip() if payload.description else None
        schedule.description = description or None

    db.commit()
    db.refresh(schedule)

    return {"data": _serialize_schedule(schedule)}


@router.delete("/interview-schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    user = _get_current_user_obj(db, user_id)
    schedule = _get_schedule_for_user(db, schedule_id, user.username)

    db.delete(schedule)
    db.commit()
