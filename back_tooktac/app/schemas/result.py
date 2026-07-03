"""결과 조회 API 응답 스키마.

None 방어를 스키마 기본값으로 처리해 라우터의 조건문을 줄이고,
OpenAPI 문서에 응답 형태가 정확히 드러나도록 한다.
"""
from pydantic import BaseModel


class SpeechLabels(BaseModel):
    speed: str = ""
    fluency: str = ""
    tone: str = ""


class VideoSummary(BaseModel):
    gaze_score: int = 0
    shoulder_warning: int = 0
    hand_warning: int = 0


class FullResultResponse(BaseModel):
    session_id: int
    question_order: int
    question: str = ""
    user_answer: str = ""
    model_answer: str = ""
    strengths: list[str] = []
    improvements: list[str] = []
    final_feedback: str = ""
    labels: SpeechLabels = SpeechLabels()
    video: VideoSummary = VideoSummary()
    best_emotion: str = ""
    weighted_score: float = 0.0
