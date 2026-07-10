"""연습 면접 시작/조회 API 스키마."""
from pydantic import BaseModel, ConfigDict


class InterviewStartRequest(BaseModel):
    # 배열의 순서가 곧 출제 순서다. 기본 자기소개 질문은 서버가 맨 앞에 넣으므로
    # 여기 포함하지 않아도 된다.
    # 개수 상한은 라우터에서 검증한다 (초과 시 안내 문구가 담긴 400을 주기 위해).
    question_ids: list[int] = []


class InterviewQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_order: int
    question_text: str
    question_type: str


class InterviewStartResponse(BaseModel):
    session_id: int
    total_questions: int
    questions: list[InterviewQuestionOut] = []
