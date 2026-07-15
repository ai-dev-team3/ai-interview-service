# app/agents/motivation_agent.py
from app.agents.base import BaseSpecialistAgent


class MotivationAgent(BaseSpecialistAgent):
    """지원동기 항목 평가 담당."""

    @property
    def question_type(self) -> str:
        return "지원동기"

    @property
    def instruction_prompt(self) -> str:
        return """\
[평가 기준: 지원동기]
위 기업 정보와 기존 답변을 참고해서 다음 기준으로 답변을 개선하세요.
1. 기업의 최근 이슈/사업 방향과 지원동기가 실제로 연결되도록
2. 다른 기업에도 그대로 쓸 수 있는 뻔한 문장은 없애고
3. 인재상 키워드와 지원자 경험이 자연스럽게 연결되도록
"""