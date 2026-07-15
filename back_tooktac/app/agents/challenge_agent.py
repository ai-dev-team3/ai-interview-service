# app/agents/challenge_agent.py
from app.agents.base import BaseSpecialistAgent


class ChallengeAgent(BaseSpecialistAgent):
    """도전및목표달성 항목 평가 담당."""

    @property
    def question_type(self) -> str:
        return "도전및목표달성"

    @property
    def instruction_prompt(self) -> str:
        return """\
[평가 기준: 도전및목표달성]
위 기존 답변을 참고해서 다음 기준으로 답변을 개선하세요.
1. 어떤 목표를 왜 세웠는지, 목표가 도전적이었던 이유가 명확히 드러나도록
2. 목표 달성을 가로막은 구체적인 어려움과, 그걸 극복하기 위해 실제로 취한 행동이 드러나도록
3. 결과를 가능하면 구체적인 수치나 사실로 표현하고, 그 경험에서 얻은 배움이나 다음 도전에 어떻게 이어지는지 드러나도록
"""
