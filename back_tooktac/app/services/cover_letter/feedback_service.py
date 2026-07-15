# app/services/cover_letter/feedback_service.py
"""
자소서 첨삭 오케스트레이션.

흐름:
    1. 기업 리서치는 요청당 한 번만 실행 (company_name, job_role 기준)
    2. 문항마다: 트리아지로 유형 분류 → 해당 specialist agent 실행 (revised_answer + feedback 반환)
    3. 문항 리스트는 asyncio.gather로 병렬 처리

router(api/routes/cover_letter.py)는 이제 async def이므로, 여기서는 asyncio.run() 브릿지가
필요 없고 바로 await하면 됩니다.
"""

import asyncio
import logging

from app.tools.company_research import research_company, CompanyResearchResult
from app.agents.triage_agent import classify_question_type
from app.agents.motivation_agent import MotivationAgent
from app.agents.job_fit_agent import JobFitAgent
from app.agents.challenge_agent import ChallengeAgent
from app.agents.creativity_agent import CreativityAgent
from app.agents.culture_fit_agent import CultureFitAgent

logger = logging.getLogger(__name__)

_AGENT_CLASSES = [
    MotivationAgent,
    JobFitAgent,
    ChallengeAgent,
    CreativityAgent,
    CultureFitAgent,
]
_AGENT_MAP = {cls().question_type: cls for cls in _AGENT_CLASSES}


async def _process_single_entry(
    *,
    company_name: str,
    job_role: str,
    company_info: CompanyResearchResult,
    question_text: str,
    existing_answer: str,
) -> dict:
    question_type = await classify_question_type(
        question_text=question_text, existing_answer=existing_answer
    )
    agent_cls = _AGENT_MAP[question_type]
    agent = agent_cls()

    logger.info("%s 첨삭 시작: company=%s, type=%s", agent_cls.__name__, company_name, question_type)

    # agent.run()은 동기 함수(llm.invoke)라서 이벤트 루프를 막지 않도록 스레드에서 실행합니다.
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: agent.run(
            company_name=company_name,
            job_role=job_role,
            company_info=company_info,
            question_text=question_text,
            existing_answer=existing_answer,
        ),
    )

    logger.info(
        "%s 첨삭 완료: type=%s, revised_answer_length=%d",
        agent_cls.__name__, question_type, len(result.get("revised_answer", "")),
    )

    return {
        "question_text": question_text,
        "existing_answer": existing_answer,
        "question_type": question_type,
        "agent_used": result["agent_used"],
        "revised_answer": result["revised_answer"],
        "feedback": result["feedback"],
    }


async def run_cover_letter_feedback_batch(
    *,
    company_name: str,
    job_role: str,
    entries: list[dict],  # [{"question_text": str, "existing_answer": str}, ...]
) -> list[dict]:
    """
    기업 리서치를 한 번 수행한 뒤, 문항별로 트리아지→specialist agent 첨삭을 병렬 실행합니다.

    Returns:
        문항마다 {"question_text", "existing_answer", "question_type", "agent_used",
                  "revised_answer", "feedback"}
    """
    logger.info("기업 리서치 시작: company=%s, job_role=%s, 문항 수=%d", company_name, job_role, len(entries))
    company_info = await research_company(company_name, job_role)
    logger.debug("기업 리서치 완료: company=%s", company_name)

    tasks = [
        _process_single_entry(
            company_name=company_name,
            job_role=job_role,
            company_info=company_info,
            question_text=entry["question_text"],
            existing_answer=entry["existing_answer"],
        )
        for entry in entries
    ]
    results = await asyncio.gather(*tasks)
    return results