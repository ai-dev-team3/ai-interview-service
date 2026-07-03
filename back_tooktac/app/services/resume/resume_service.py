"""이력서 저장/조회/구조화 서비스.

마이페이지 업로드, 면접 질문 생성 등 어느 진입점에서든
재사용할 수 있도록 라우터와 분리된 독립 모듈로 유지한다.
"""
import json
import logging

from sqlalchemy.orm import Session

from app.repository.resume import Resume
from app.services.resume.structurer import ResumeStructurer, ResumeStructuringError

logger = logging.getLogger(__name__)


class ResumeNotFoundError(Exception):
    """등록된 이력서(원문)가 없음"""


def get_resume(db: Session, user_id: int) -> Resume | None:
    return db.query(Resume).filter(Resume.user_id == user_id).first()


def has_resume(db: Session, user_id: int) -> bool:
    """이력서 원문(content)이 등록되어 있는지 여부"""
    resume = get_resume(db, user_id)
    return bool(resume and resume.content)


def upsert_resume(db: Session, user_id: int, content: str, filename: str | None = None) -> Resume:
    """이력서 원문 텍스트를 저장한다. 이미 있으면 갱신(업서트).

    원문이 바뀌면 기존 구조화 데이터(structured)는 더 이상 유효하지 않으므로 초기화한다.
    """
    resume = get_resume(db, user_id)
    if resume:
        resume.content = content
        resume.filename = filename
        resume.structured = None
    else:
        resume = Resume(user_id=user_id, filename=filename, content=content, structured=None)
        db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def try_structure(db: Session, resume: Resume) -> bool:
    """이력서 원문을 구조화해 저장한다. 실패해도 예외를 전파하지 않는다.

    업로드 시점의 베스트에포트 처리용 — 실패 시 면접 시작 시점에
    ensure_structured()가 재시도한다.
    """
    try:
        resume.structured = ResumeStructurer().structure(resume.content)
    except ResumeStructuringError:
        logger.warning("이력서 구조화 실패 — 면접 시작 시 재시도 (resume_id=%s)", resume.id)
        return False
    db.commit()
    return True


def ensure_structured(db: Session, user_id: int) -> dict:
    """구조화된 이력서를 반환한다. 없으면 원문으로부터 생성·저장 후 반환.

    Raises:
        ResumeNotFoundError: 이력서 원문 자체가 없음
        ResumeStructuringError: 구조화(Gemini) 실패
    """
    resume = get_resume(db, user_id)
    if not resume or not resume.content:
        raise ResumeNotFoundError("등록된 이력서가 없습니다.")

    if not resume.structured:
        resume.structured = ResumeStructurer().structure(resume.content)
        db.commit()
        db.refresh(resume)

    structured = resume.structured
    if isinstance(structured, str):
        structured = json.loads(structured)
    return structured
