from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, Text, TIMESTAMP
from sqlalchemy.orm import relationship

from app.repository.database import Base
from app.utils.time_utils import utcnow_naive


class JobGroup(Base):
    __tablename__ = "job_group"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    criteria = relationship(
        "JobReadinessCriteria",
        back_populates="job_group",
        cascade="all, delete-orphan",
        order_by="JobReadinessCriteria.sort_order",
    )
    action_templates = relationship(
        "ActionTemplate",
        back_populates="job_group",
        cascade="all, delete-orphan",
    )
    diagnosis_results = relationship("CareerDiagnosisResult", back_populates="job_group")


class JobReadinessCriteria(Base):
    __tablename__ = "job_readiness_criteria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_group_id = Column(Integer, ForeignKey("job_group.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False)
    keywords = Column(JSON, nullable=True)
    weight = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    job_group = relationship("JobGroup", back_populates="criteria")
    action_templates = relationship(
        "ActionTemplate",
        back_populates="criterion",
        cascade="all, delete-orphan",
    )


class ActionTemplate(Base):
    __tablename__ = "action_template"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_group_id = Column(Integer, ForeignKey("job_group.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_id = Column(
        Integer,
        ForeignKey("job_readiness_criteria.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_title = Column(String(100), nullable=False)
    action_detail = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    job_group = relationship("JobGroup", back_populates="action_templates")
    criterion = relationship("JobReadinessCriteria", back_populates="action_templates")


class CareerDiagnosisResult(Base):
    __tablename__ = "career_diagnosis_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("resume.id", ondelete="CASCADE"), nullable=False, index=True)
    job_group_id = Column(Integer, ForeignKey("job_group.id", ondelete="CASCADE"), nullable=False, index=True)
    desired_job = Column(String(100), nullable=True)
    total_score = Column(Integer, nullable=False)
    result_json = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP, default=utcnow_naive)

    user = relationship("User")
    resume = relationship("Resume")
    job_group = relationship("JobGroup", back_populates="diagnosis_results")

