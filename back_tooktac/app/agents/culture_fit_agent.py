# app/agents/culture_fit_agent.py
from app.agents.base import BaseSpecialistAgent


class CultureFitAgent(BaseSpecialistAgent):
    """조직적합성과인성 항목 평가 담당."""

    @property
    def question_type(self) -> str:
        return "조직적합성과인성"

    @property
    def instruction_prompt(self) -> str:
        return """\
[평가 기준: 조직적합성과인성]
위 기업 정보(특히 인재상/핵심가치)와 기존 답변을 참고해서 다음 기준으로 답변을 개선하세요.
1. 협업, 갈등 해결, 조직 적응 등 실제 경험 속 구체적인 행동과 태도가 드러나도록
2. 기업의 인재상/핵심가치와 지원자의 경험이 자연스럽게 연결되도록 (억지로 끼워맞춘 느낌은 지양)
3. "책임감이 강하다", "성실하다" 같은 자기 평가성 표현보다, 그렇게 판단할 수 있는 구체적 사례 중심으로 표현되도록
"""
