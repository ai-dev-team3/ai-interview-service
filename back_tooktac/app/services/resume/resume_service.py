"""이력서 저장/조회 서비스.

마이페이지 업로드, (향후) 구조화 파이프라인 등 어느 진입점에서든
재사용할 수 있도록 라우터와 분리된 독립 모듈로 유지한다.
"""
from sqlalchemy.orm import Session

from app.repository.resume import Resume


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
