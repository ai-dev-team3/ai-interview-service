# app/agents/triage_agent.py
"""
자소서 문항을 5개 유형 중 하나로 분류하는 트리아지 에이전트.

specialist agent(base.py)와 동일하게 OpenAI(gpt-4o-mini)를 사용합니다.
분류가 애매하거나 LLM 호출이 실패하면 '지원동기'로 기본값 처리합니다.
"""

import logging
import os
from typing import Literal

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

QuestionType = Literal[
    "지원동기", "직무적합성", "도전및목표달성", "창의성및문제해결", "조직적합성과인성"
]

DEFAULT_QUESTION_TYPE: QuestionType = "지원동기"


class TriageResult(BaseModel):
    question_type: QuestionType = Field(description="문항이 속하는 유형")


_TRIAGE_PROMPT = """\
다음 자기소개서 문항과 기존 답변을 읽고, 아래 5개 유형 중 가장 적합한 하나를 고르세요.

- 지원동기: 왜 이 회사/직무에 지원했는지
- 직무적합성: 직무에 필요한 역량/경험을 갖췄는지
- 도전및목표달성: 목표를 세우고 어려움을 극복해 달성한 경험
- 창의성및문제해결: 새로운 방식으로 문제를 해결한 경험
- 조직적합성과인성: 협업, 조직 문화 적응, 인성 관련 경험

[문항]
{question_text}

[기존 답변]
{existing_answer}

애매해서 판단이 어려우면 '지원동기'를 선택하세요.
"""


async def classify_question_type(*, question_text: str, existing_answer: str) -> QuestionType:
    """문항 텍스트와 기존 답변을 보고 5개 유형 중 하나를 반환합니다. 실패 시 기본값(지원동기)."""
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0,
        )
        structured_llm = llm.with_structured_output(TriageResult)
        prompt = _TRIAGE_PROMPT.format(
            question_text=question_text, existing_answer=existing_answer
        )
        result: TriageResult = await structured_llm.ainvoke(prompt)
        return result.question_type
    except Exception as exc:
        logger.warning(
            "문항 유형 분류 실패, 기본값(%s)으로 처리: %s", DEFAULT_QUESTION_TYPE, exc
        )
        return DEFAULT_QUESTION_TYPE
