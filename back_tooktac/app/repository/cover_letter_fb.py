# app/repository/cover_letter.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from app.repository.database import Base
from datetime import datetime, timezone


class CoverLetterFeedback(Base):
    __tablename__ = "cover_letter_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    company_name = Column(String(100), nullable=False)
    job_role = Column(String(100), nullable=False)
    question_type = Column(String(50), nullable=False)
    question_text = Column(Text, nullable=False)
    existing_answer = Column(Text, nullable=False)
    revised_answer = Column(Text, nullable=False)

    agent_used = Column(String(50), nullable=False)
    feedback = Column(Text, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    # 관계 설정
    user = relationship("User", back_populates="cover_letter_feedbacks")