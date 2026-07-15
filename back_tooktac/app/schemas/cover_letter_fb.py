"""자소서 첨삭 요청/조회 API 스키마."""
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class CoverLetterFeedbackRequest(BaseModel):
    company_name: str = Field(max_length=100)
    job_role: str
    # 5개 유형 중 하나여야 한다. 유효하지 않으면 라우터/서비스에서 400을 반환한다.
    # ("지원동기" | "직무적합성" | "도전및목표달성" | "창의성및문제해결" | "조직적합성과인성")
    question_type: Literal["지원동기", "직무적합성", "도전및목표달성", "창의성및문제해결", "조직적합성과인성"]
    question_text: str
    existing_answer: str


class CoverLetterFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    job_role: str
    question_type: str
    agent_used: str
    feedback: str
    created_at: datetime


class CoverLetterFeedbackHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    job_role: str
    question_type: str
    agent_used: str
    feedback: str
    created_at: datetime


class CoverLetterHistoryListResponse(BaseModel):
    items: List[CoverLetterFeedbackHistoryOut]
    total: int
    page: int
    size: int