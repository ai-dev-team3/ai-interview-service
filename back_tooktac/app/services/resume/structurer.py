"""이력서 원문 텍스트 → 구조화 JSON 변환 (LCEL 체인).

출력 스키마는 질문 생성기(ResumeQuestionGenerator)가 읽는 필드에 맞춰 고정한다.
"""
import logging
from typing import Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.observability import RESUME_STRUCTURING, feature
from app.services.llm import get_chat_model

logger = logging.getLogger(__name__)


class ResumeStructuringError(Exception):
    """LLM 호출 실패 또는 응답 JSON 파싱 실패"""


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
    def __init__(self, llm: Optional[Runnable] = None):
        self.llm = llm if llm is not None else get_chat_model(primary="gemini", temperature=0.2)
        self.chain = (
            ChatPromptTemplate.from_template(_PROMPT_TEMPLATE)
            | self.llm
            | JsonOutputParser()
        )

    def structure(self, content: str) -> dict:
        # 면접 시작 중에 불려도 이 호출은 '이력서 구조화'로 집계한다.
        try:
            with feature(RESUME_STRUCTURING):
                data = self.chain.invoke({"content": content})
        except Exception as e:
            logger.exception("이력서 구조화 실패")
            raise ResumeStructuringError(str(e)) from e

        if not isinstance(data, dict):
            raise ResumeStructuringError(f"예상하지 못한 응답 형식: {type(data).__name__}")

        return _normalize(data)
