# app/services/cover_letter/feedback_service.py
"""
자소서 첨삭 오케스트레이션.

router(api/routes/cover_letter.py)에서 바로 호출할 수 있도록 동기 함수로 노출합니다.
company_research.py는 Tavily 병렬 검색 때문에 async로 작성돼 있어, 이 함수 내부에서
asyncio.run()으로 브릿지합니다. (프로젝트 전체가 sync 라우터 기반이라 여기서만 경계를 둡니다)
"""

import asyncio

from app.tools.company_research import research_company
from app.agents.motivation_agent import MotivationAgent
from app.agents.job_fit_agent import JobFitAgent
# from app.agents.challenge_agent import ChallengeAgent
# from app.agents.creativity_agent import CreativityAgent
# from app.agents.culture_fit_agent import CultureFitAgent

# question_type(버튼/입력값) → 담당 agent 매핑. LLM 판단 없이 바로 라우팅합니다.
_AGENT_MAP = {
    "지원동기": MotivationAgent,
    # "직무적합성": JobFitAgent,
    # "도전및목표달성": ChallengeAgent,
    # "창의성및문제해결": CreativityAgent,
    # "조직적합성과인성": CultureFitAgent,
}


def run_cover_letter_feedback(
    *,
    company_name: str,
    job_role: str,
    question_type: str,
    question_text: str,
    existing_answer: str,
) -> dict | None:
    """
    기업 리서치 → 질문유형에 맞는 specialist agent 실행까지 한 번에 처리합니다.

    Returns:
        {"agent_used": str, "feedback": str} 또는
        question_type이 5개 유형에 없으면 None (호출부에서 400 처리)
    """
    agent_cls = _AGENT_MAP.get(question_type)
    if agent_cls is None:
        return None

    print(f"[cover_letter] 기업 리서치 시작: {company_name} / {job_role}")
    company_info = asyncio.run(research_company(company_name, job_role))
    print("[cover_letter] 기업 리서치 완료")

    print(f"[cover_letter] {agent_cls.__name__} 첨삭 시작")
    agent = agent_cls()
    result = agent.run(
        company_name=company_name,
        job_role=job_role,
        company_info=company_info,
        question_text=question_text,
        existing_answer=existing_answer,
    )
    print("[cover_letter] 첨삭 완료")

    return result