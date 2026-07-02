"""최종 리포트 도메인 데이터 모델"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class UserInfo:
    user_id: str
    user_nickname: str
    interview_id: str
    interview_date: str
    interview_duration: int


@dataclass
class QuestionAnalysis:
    question_id: str
    name: str
    type: str
    final_score: int
    question: str
    my_answer: str
    model_answer: str
    detail_analysis: Dict[str, Dict[str, float]]  # text, voice, video, emotion
    feedback: str
    strengths: List[str]
    improvements: List[str]
