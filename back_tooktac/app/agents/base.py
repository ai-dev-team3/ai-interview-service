# app/agents/base.py
"""
자소서 첨삭 전용 Specialist Agent들의 공통 베이스.

※ interview.py의 질문 생성 기능은 Gemini(google.generativeai)를 직접 호출하는 방식이지만,
   이 자소서 첨삭 5개 agent는 LangChain + OpenAI(gpt-4o-mini) 기반입니다.
   기업 리서치(app/tools/company_research.py)는 구조화 출력 때문에 계속 Claude를 씁니다 —
   같은 기능 안에서도 단계별로 다른 모델을 쓰는 의도적인 선택입니다.
"""

from abc import ABC, abstractmethod
import os
from langchain_openai import ChatOpenAI

from app.tools.company_research import CompanyResearchResult


SHARED_CONTEXT_TEMPLATE = """\
[기업 정보]
- 기업명: {company_name}
- 지원 직무: {job_role}
- 기업 개요: {overview}
- 인재상/핵심가치: {core_values}
- 최근 이슈: {recent_issues}
- 직무 관련 키워드: {job_keywords}

[자소서 문항]
{question_text}

[기존 작성 답변]
{existing_answer}
"""


class BaseSpecialistAgent(ABC):
    """5개 specialist agent(motivation, job_fit, challenge, creativity, culture_fit)의 공통 부모."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.3,
        )

    @property
    @abstractmethod
    def question_type(self) -> str:
        """이 agent가 담당하는 질문 유형 (예: '지원동기'). 라우팅 매핑 키로도 사용됩니다."""
        ...

    @property
    @abstractmethod
    def instruction_prompt(self) -> str:
        """각 specialist 고유의 평가 기준/지시문. 하위 클래스에서 정의합니다."""
        ...

    def _build_shared_context(
        self,
        *,
        company_name: str,
        job_role: str,
        company_info: CompanyResearchResult,
        question_text: str,
        existing_answer: str,
    ) -> str:
        return SHARED_CONTEXT_TEMPLATE.format(
            company_name=company_name,
            job_role=job_role,
            overview=company_info.overview,
            core_values=", ".join(company_info.core_values) or "정보 없음",
            recent_issues="\n".join(f"- {i}" for i in company_info.recent_issues) or "정보 없음",
            job_keywords=", ".join(company_info.job_related_keywords) or "정보 없음",
            question_text=question_text,
            existing_answer=existing_answer,
        )

    def run(
        self,
        *,
        company_name: str,
        job_role: str,
        company_info: CompanyResearchResult,
        question_text: str,
        existing_answer: str,
    ) -> dict:
        """
        interview.py의 generator.generate_xxx(parsed_data) 호출 패턴과 맞춰
        동기 함수로 노출합니다 (router에서 바로 호출 가능).
        """
        shared_context = self._build_shared_context(
            company_name=company_name,
            job_role=job_role,
            company_info=company_info,
            question_text=question_text,
            existing_answer=existing_answer,
        )
        full_prompt = shared_context + "\n\n" + self.instruction_prompt

        response = self.llm.invoke(full_prompt)

        return {
            "agent_used": self.__class__.__name__,
            "feedback": response.content.strip(),
        }