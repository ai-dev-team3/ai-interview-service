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


# --- 실전 면접 ---
# 질문을 미리 다 내려주지 않는다. 사용자가 다음 질문을 알면 실전이 아니고,
# 꼬리질문 때문에 애초에 다음 질문이 정해져 있지도 않다.


class RealInterviewStartResponse(BaseModel):
    session_id: int
    max_questions: int          # 상한. 꼬리질문이 붙으면 기본 질문이 그만큼 줄어든다
    prepare_seconds: int
    answer_seconds: int
    question: InterviewQuestionOut   # 첫 질문 하나만


class RealAnswerResponse(BaseModel):
    """답변 접수 결과. 다음 질문을 바로 준다 (분석은 백그라운드에서 계속된다)."""

    transcript: str
    finished: bool
    is_follow_up: bool = False
    question: InterviewQuestionOut | None = None   # finished 면 None


class AnalysisStatusResponse(BaseModel):
    """마지막 대기 화면용 진행률."""

    session_id: int
    total: int
    done: int
    finished: bool
