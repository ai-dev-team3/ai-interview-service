from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.repository.database import get_db
from app.services.career import readiness
from app.services.user.dependencies import get_current_user

router = APIRouter(prefix="/career", tags=["career"])


@router.get("/job-groups")
def list_job_groups(db: Session = Depends(get_db)):
    return readiness.list_job_groups(db)


@router.post("/diagnosis")
def create_career_diagnosis(
    db: Session = Depends(get_db),
    user_id=Depends(get_current_user),
):
    try:
        return readiness.create_diagnosis(db, user_id)
    except readiness.CareerDiagnosisPrerequisiteError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except readiness.CareerDiagnosisConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
