"""자소서 첨삭 요청/조회 API 스키마."""
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field


class CoverLetterEntryRequest(BaseModel):
    question_text: str
    existing_answer: str


class CoverLetterFeedbackRequest(BaseModel):
    company_name: str = Field(max_length=100)
    job_role: str
    entries: List[CoverLetterEntryRequest]


class CoverLetterFeedbackItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    job_role: str
    question_type: str
    question_text: str
    existing_answer: str
    revised_answer: str
    agent_used: str
    feedback: str
    created_at: datetime


class CoverLetterFeedbackResponse(BaseModel):
    items: List[CoverLetterFeedbackItem]


class CoverLetterFeedbackUpdateItem(BaseModel):
    id: int
    revised_answer: str


class CoverLetterFeedbackUpdateRequest(BaseModel):
    items: List[CoverLetterFeedbackUpdateItem]


class CoverLetterFeedbackHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    job_role: str
    question_type: str
    agent_used: str
    revised_answer: str
    feedback: str
    created_at: datetime


class CoverLetterHistoryListResponse(BaseModel):
    items: List[CoverLetterFeedbackHistoryOut]
    total: int
    page: int
    size: int