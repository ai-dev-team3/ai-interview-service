# app/agents/creativity_agent.py
from app.agents.base import BaseSpecialistAgent


class CreativityAgent(BaseSpecialistAgent):
    """창의성및문제해결 항목 평가 담당."""

    @property
    def question_type(self) -> str:
        return "창의성및문제해결"

    @property
    def instruction_prompt(self) -> str:
        return """\
[평가 기준: 창의성및문제해결]
위 기존 답변을 참고해서 다음 기준으로 답변을 개선하세요.
1. 어떤 문제 상황이었는지 배경과 원인이 명확히 드러나도록
2. 기존 방식과 다르게 시도한 지원자만의 접근 방식이 구체적으로 드러나도록 (일반적이고 뻔한 해결책은 지양)
3. 그 시도가 실제로 만든 변화나 결과가 구체적으로 드러나도록
"""
