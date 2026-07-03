"""이력서 원문 텍스트 → 구조화 JSON 변환 (Gemini).

출력 스키마는 질문 생성기(InterviewQuestionGenerator)가 읽는 필드에 맞춰 고정한다.
"""
import json
import logging

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL_NAME

logger = logging.getLogger(__name__)


class ResumeStructuringError(Exception):
    """Gemini 호출 실패 또는 응답 JSON 파싱 실패"""


# 질문 생성기가 .get()으로 접근하는 키들 — 누락 시 기본값으로 채운다
_DEFAULT_STRUCTURE = {
    "skills": [],
    "education": {},
    "career": {},
    "projects": [],
    "self_introduction": {},
    "desired_position": {},
}

_PROMPT_TEMPLATE = """당신은 이력서/자기소개서 분석 전문가입니다.
아래 이력서 원문에서 정보를 추출해 JSON으로 구조화하세요.

출력 JSON 스키마 (키는 반드시 이 형태를 유지하고, 해당 정보가 없으면 빈 문자열/빈 배열로 두세요):
{{
  "skills": ["기술 스택 문자열"],
  "education": {{"school": "", "major": "", "degree": "", "status": ""}},
  "career": {{"status": "신입 또는 경력", "years": "N년"}},
  "projects": [{{"name": "", "description": "", "tech_stack": [""]}}],
  "self_introduction": {{"motivation": "", "strengths": "", "key_experiences": "", "career_goals": ""}},
  "desired_position": {{"job_type": ""}}
}}

규칙:
- 원문에 없는 내용을 지어내지 마세요
- JSON 외의 다른 텍스트를 출력하지 마세요

이력서 원문:
{content}
"""


def _normalize(data: dict) -> dict:
    """필수 키가 누락된 경우 기본값으로 채워 질문 생성기의 .get() 접근을 보장"""
    normalized = {}
    for key, default in _DEFAULT_STRUCTURE.items():
        value = data.get(key)
        if not isinstance(value, type(default)):
            value = default
        normalized[key] = value
    return normalized


class ResumeStructurer:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = GEMINI_MODEL_NAME

    def structure(self, content: str) -> dict:
        prompt = _PROMPT_TEMPLATE.format(content=content)
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(response.text)
        except Exception as e:
            logger.exception("이력서 구조화 실패")
            raise ResumeStructuringError(str(e)) from e

        if not isinstance(data, dict):
            raise ResumeStructuringError(f"예상하지 못한 응답 형식: {type(data).__name__}")

        return _normalize(data)
