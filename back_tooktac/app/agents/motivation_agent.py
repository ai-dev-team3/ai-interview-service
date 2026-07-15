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
위 기업 정보와 기존 답변을 비교해서 다음을 평가하세요.
1. 기업의 최근 이슈/사업 방향과 지원동기가 실제로 연결되는지
2. 다른 기업에도 그대로 쓸 수 있는 뻔한 문장은 없는지
3. 인재상 키워드와 지원자 경험이 자연스럽게 연결되는지

강점 2가지, 개선점 2가지, 수정 제안 문장 1개를 제시하세요.
출력 어디에도 별표(*)나 마크다운 글머리표 없이, 순수한 문장 형태로만 작성하세요.
"""