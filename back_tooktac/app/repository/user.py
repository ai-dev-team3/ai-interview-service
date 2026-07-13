from sqlalchemy import Column, Integer, BigInteger, String, Date, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from app.repository.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "user"
    

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    nickname = Column(String(100), nullable=False)
    email = Column(String(255), unique=True)
    birthdate = Column(Date, nullable=False)
    desired_job = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True, default=None)

    # 관계 설정 (1:N → User:Resume)
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    evaluation_results = relationship("EvaluationResult", back_populates="user")
    video_results = relationship("VideoEvaluationResult", back_populates="user")
    final_reports = relationship("FinalReportSummary", back_populates="user")
    sessions = relationship("InterviewSession", back_populates="user")
    cover_letters = relationship("CoverLetter", back_populates="user", cascade="all, delete-orphan")
    
    interview_schedules = relationship(
    "InterviewSchedule",
    back_populates="user",
    cascade="all, delete-orphan"
    )
    
class InterviewSchedule(Base):
    __tablename__ = "interview_schedule"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    user_id = Column(
        String(50, collation="utf8mb4_0900_ai_ci"),
        ForeignKey(
            "user.username",
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False
    )

    scheduled_at = Column("interview_schedule", DateTime, nullable=False)
    description = Column(String(255), nullable=True)

    user = relationship("User", back_populates="interview_schedules")

    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
