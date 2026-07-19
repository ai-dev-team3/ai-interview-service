from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.observability import CAREER_DIAGNOSIS, feature
from app.repository.database import get_db
from app.services.career import readiness
from app.services.user.dependencies import get_current_user

router = APIRouter(prefix="/career", tags=["career"])


class CareerDiagnosisCreate(BaseModel):
    cover_letter_id: int | None = Field(default=None, ge=1)


@router.get("/job-groups")
def list_job_groups(db: Session = Depends(get_db)):
    return readiness.list_job_groups(db)


@router.post("/diagnosis")
def create_career_diagnosis(
    payload: CareerDiagnosisCreate | None = Body(default=None),
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    try:
        with feature(CAREER_DIAGNOSIS):
            return readiness.create_diagnosis(
                db,
                user_id,
                cover_letter_id=payload.cover_letter_id if payload else None,
            )
    except readiness.CareerDiagnosisPrerequisiteError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except readiness.CareerDiagnosisConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
