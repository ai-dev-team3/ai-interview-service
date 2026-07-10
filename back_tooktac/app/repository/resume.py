from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.orm import relationship
from app.repository.database import Base
from app.utils.time_utils import utcnow_naive

class Resume(Base):
    __tablename__ = "resume"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255))
    content = Column(Text)
    structured = Column(JSON)
    # 질문 생성을 이미 마쳤는지. 사용자가 생성된 질문을 모두 지워도
    # 다음 조회 때 되살아나지 않도록 하는 표시다.
    questions_generated = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="resumes")
    questions = relationship(
        "ResumeQuestion",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeQuestion.sort_order",
    )


class ResumeQuestion(Base):
    """이력서에 연결된 예상 면접 질문 풀.

    면접 세션의 interview_question은 이 행을 참조하지 않고 텍스트를 복사한다.
    이력서를 다시 올리면 이 풀은 통째로 갈아엎히지만, 과거 면접 기록은 보존된다.
    """

    __tablename__ = "resume_question"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resume.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # plan.QUESTION_TYPES 중 하나
    is_default = Column(Boolean, nullable=False, default=False)  # "1분 자기소개" 질문
    sort_order = Column(Integer, nullable=False, default=0)  # 풀의 표시 순서
    created_at = Column(TIMESTAMP, default=utcnow_naive)

    resume = relationship("Resume", back_populates="questions")
