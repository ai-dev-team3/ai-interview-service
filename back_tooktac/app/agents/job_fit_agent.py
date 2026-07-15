# app/agents/job_fit_agent.py
from app.agents.base import BaseSpecialistAgent


class JobFitAgent(BaseSpecialistAgent):
    """직무적합성 항목 평가 담당."""

    @property
    def question_type(self) -> str:
        return "직무적합성"

    @property
    def instruction_prompt(self) -> str:
        return """\
[평가 기준: 직무적합성]
위 기업 정보(특히 직무 관련 키워드)와 기존 답변을 참고해서 다음 기준으로 답변을 개선하세요.
1. 지원 직무에서 요구하는 역량/키워드와 지원자의 경험이 구체적으로 매칭되도록
2. "열심히 했다", "잘한다" 같은 추상적 표현 대신 구체적인 행동과 결과(가능하면 수치)로 표현되도록
3. 직무와 무관한 경험이나 장황한 설명은 덜어내고 직무 연관성이 높은 내용 위주로 구성되도록
"""
