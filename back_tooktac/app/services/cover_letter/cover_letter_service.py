from sqlalchemy.orm import Session
from app.repository.cover_letter import CoverLetterFeedback

# def save_feedback(db: Session, ...) -> CoverLetterFeedback:
#     row = CoverLetterFeedback(...)
#     db.add(row)
#     db.commit()
#     db.refresh(row)
#     return row

def get_feedbacks_by_user(db: Session, user_id: int) -> list[CoverLetterFeedback]:
    return (
        db.query(CoverLetterFeedback)
        .filter(CoverLetterFeedback.user_id == user_id)
        .order_by(CoverLetterFeedback.created_at.desc())
        .all()
    )