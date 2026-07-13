# app/models/interview.py

from sqlalchemy import Column, Integer, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from app.repository.database import Base
from app.utils.time_utils import utcnow_naive

class InterviewSession(Base):
    __tablename__ = "interview_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    started_at = Column(TIMESTAMP, default=utcnow_naive)

    # practice: 사용자가 질문을 고르고, 문항마다 결과를 본다
    # real    : 서버가 질문을 정하고, 분석은 백그라운드로 돌며 끝나야 리포트를 본다
    #           꼬리질문이 붙을 수 있어 질문 행이 진행 중에 하나씩 생긴다
    mode = Column(String(20), nullable=False, default="practice", server_default="practice")

    user = relationship("User", back_populates="sessions")

    questions = relationship("InterviewQuestion", back_populates="session")
    evaluation_results = relationship("EvaluationResult", back_populates="session")
    video_results = relationship("VideoEvaluationResult", back_populates="session")
    final_report = relationship("FinalReportSummary", back_populates="session", uselist=False)

class InterviewQuestion(Base):
    __tablename__ = "interview_question"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("interview_session.id"), nullable=False)
    question_order = Column(Integer, nullable=False)  # 1부터, 세션 내에서 연속
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, default=utcnow_naive)

    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship("InterviewAnswer", uselist=False, back_populates="question")
    evaluation_result = relationship("EvaluationResult", back_populates="question", uselist=False)
    video_result = relationship("VideoEvaluationResult", back_populates="question", uselist=False)

class InterviewAnswer(Base):
    __tablename__ = "interview_answer"

    id = Column(Integer, primary_key=True, autoincrement=True)

    session_id = Column(Integer, ForeignKey("interview_session.id"), nullable=False)  # ✅ 세션 ID 추가
    question_id = Column(Integer, ForeignKey("interview_question.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    question_order = Column(Integer, nullable=False)
    answer_text = Column(Text)
    created_at = Column(TIMESTAMP, default=utcnow_naive)

    # 관계 설정
    question = relationship("InterviewQuestion", back_populates="answer")
    session = relationship("InterviewSession", backref="answers")  # ✅ 역참조 관계 추가
