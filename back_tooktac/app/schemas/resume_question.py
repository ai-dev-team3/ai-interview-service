"""이력서 질문 풀 API 스키마."""
from pydantic import BaseModel, ConfigDict, Field


class ResumeQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_text: str
    question_type: str
    is_default: bool
    sort_order: int


class ResumeQuestionListResponse(BaseModel):
    resume_id: int
    questions: list[ResumeQuestionOut] = []


class ResumeQuestionCreate(BaseModel):
    question_text: str = Field(min_length=1, max_length=1000)
