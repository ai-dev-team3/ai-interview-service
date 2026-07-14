from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, JSON, String, Text, TIMESTAMP, text
from sqlalchemy.orm import relationship

from app.repository.database import Base


class JobGroup(Base):
    __tablename__ = "job_group"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("1"), default=True)

    criteria = relationship("JobReadinessCriteria", back_populates="job_group")
    action_templates = relationship("ActionTemplate", back_populates="job_group")
    diagnosis_results = relationship("CareerDiagnosisResult", back_populates="job_group")
    cover_letters = relationship("CoverLetter", back_populates="job_group")

    __table_args__ = (
        Index("name", "name", unique=True),
    )


class JobReadinessCriteria(Base):
    __tablename__ = "job_readiness_criteria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_group_id = Column(
        Integer,
        ForeignKey("job_group.id", name="job_readiness_criteria_ibfk_1", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion_name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False)
    keywords = Column(JSON, nullable=True)
    weight = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False, server_default=text("0"), default=0)

    job_group = relationship("JobGroup", back_populates="criteria")
    action_templates = relationship("ActionTemplate", back_populates="criterion")


class ActionTemplate(Base):
    __tablename__ = "action_template"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_group_id = Column(
        Integer,
        ForeignKey("job_group.id", name="action_template_ibfk_2", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion_id = Column(
        Integer,
        ForeignKey("job_readiness_criteria.id", name="action_template_ibfk_1", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_title = Column(String(100), nullable=False)
    action_detail = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, server_default=text("0"), default=0)

    job_group = relationship("JobGroup", back_populates="action_templates")
    criterion = relationship("JobReadinessCriteria", back_populates="action_templates")


class CareerDiagnosisResult(Base):
    __tablename__ = "career_diagnosis_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(
        Integer,
        ForeignKey("resume.id", name="fk_career_result_resume", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    job_group_id = Column(
        Integer,
        ForeignKey("job_group.id", name="fk_career_result_job_group", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    desired_job = Column(String(100), nullable=True)
    total_score = Column(Integer, nullable=False)
    result_json = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    user_id = Column(
        Integer,
        ForeignKey("user.id", name="fk_career_result_user_id", ondelete="CASCADE"),
        nullable=False,
    )

    user = relationship("User")
    resume = relationship("Resume")
    job_group = relationship("JobGroup", back_populates="diagnosis_results")

    __table_args__ = (
        Index("fk_career_result_job_group", "job_group_id"),
        Index("fk_career_result_resume", "resume_id"),
        Index("fk_career_result_user_id", "user_id"),
    )


class CoverLetter(Base):
    __tablename__ = "cover_letter"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("user.id", name="fk_cover_letter_user", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    company_name = Column(String(100), nullable=True)
    job_group_id = Column(
        Integer,
        ForeignKey("job_group.id", name="fk_cover_letter_job_group", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    title = Column(String(100), nullable=False)
    question_text = Column(Text, nullable=True)
    answer_text = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    user = relationship("User", back_populates="cover_letters")
    job_group = relationship("JobGroup", back_populates="cover_letters")

    __table_args__ = (
        Index("fk_cover_letter_job_group", "job_group_id"),
        Index("fk_cover_letter_user", "user_id"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )
