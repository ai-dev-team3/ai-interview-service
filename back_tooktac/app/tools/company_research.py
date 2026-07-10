"""
company_research.py

자기소개서 첨삭 파이프라인(Triage Agent → Specialist Agents) 중
'지원동기' / '직무적합성' 평가 에이전트에 전달할 기업 정보를 조사하는 유틸리티.

흐름:
    1. Tavily로 기업 관련 검색 쿼리 3종을 병렬 실행 (개요 / 인재상·핵심가치 / 최근 이슈)
    2. 검색 결과(스니펫)를 하나의 컨텍스트로 정리
    3. LLM(ChatAnthropic)에게 구조화 출력(Pydantic)을 요청해 평가에 필요한 필드만 추출

ADR-001에 따라 API 키 등은 전부 app.core.config.settings에서 가져온다고 가정합니다.
프로젝트 구조에 맞게 import 경로만 조정해서 사용하세요.
"""

import asyncio
import logging
from typing import List

from pydantic import BaseModel, Field
from tavily import TavilyClient
from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 출력 스키마 — 지원동기 / 직무적합성 에이전트가 바로 소비할 수 있는 형태
# ─────────────────────────────────────────────
class CompanyResearchResult(BaseModel):
    company_name: str = Field(description="기업명")
    overview: str = Field(description="기업 개요 (사업 영역, 주요 서비스/제품 요약, 2~3문장)")
    core_values: List[str] = Field(
        default_factory=list,
        description="인재상 또는 핵심가치 키워드 리스트 (예: '도전', '고객 중심')",
    )
    recent_issues: List[str] = Field(
        default_factory=list,
        description="자소서 지원동기에 인용할 만한 최근 이슈/사업 방향 (각 1문장, 최대 3개)",
    )
    job_related_keywords: List[str] = Field(
        default_factory=list,
        description="직무적합성 평가 시 매칭할 만한 기술/역량 키워드 (최대 8개)",
    )
    sources: List[str] = Field(default_factory=list, description="참고한 출처 URL")


# ─────────────────────────────────────────────
# 내부 헬퍼: Tavily 검색
# ─────────────────────────────────────────────
def _search_sync(client: TavilyClient, query: str, max_results: int = 3) -> dict:
    """Tavily는 동기 클라이언트만 제공하므로 스레드에서 실행합니다."""
    return client.search(query=query, search_depth="advanced", max_results=max_results)


async def _run_searches(company_name: str, job_role: str) -> dict[str, dict]:
    tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)

    queries = {
        "overview": f"{company_name} 기업 개요 사업영역",
        "values": f"{company_name} 인재상 핵심가치 채용",
        "issues": f"{company_name} 최근 뉴스 사업 방향 2026",
        # 🆕 job_role(버튼 선택값)을 반영한 직무 전용 검색 — job_related_keywords 정확도의 핵심
        "job_fit": f"{company_name} {job_role} 직무 자격요건 필요역량",
    }

    loop = asyncio.get_running_loop()
    tasks = {
        key: loop.run_in_executor(None, _search_sync, tavily, query)
        for key, query in queries.items()
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return dict(zip(tasks.keys(), results))


def _build_context(search_results: dict[str, dict]) -> tuple[str, List[str]]:
    """검색 결과를 LLM 입력용 텍스트 블록과 출처 URL 리스트로 정리."""
    context_blocks: List[str] = []
    sources: List[str] = []

    for section, result in search_results.items():
        if isinstance(result, Exception):
            logger.warning(f"[company_research] '{section}' 검색 실패: {result}")
            continue

        for item in result.get("results", []):
            context_blocks.append(f"- ({section}) {item.get('title', '')}: {item.get('content', '')}")
            if item.get("url"):
                sources.append(item["url"])

    return "\n".join(context_blocks), sources


# ─────────────────────────────────────────────
# 메인 함수
# ─────────────────────────────────────────────
async def research_company(company_name: str, job_role: str) -> CompanyResearchResult:
    """
    기업명과 지원 직무(버튼 선택값)를 입력받아 자소서 첨삭(지원동기/직무적합성) 에이전트가
    바로 활용할 수 있는 구조화된 기업 정보를 반환합니다.

    Args:
        company_name: 조사할 기업명 (예: "삼성물산")
        job_role: 지원자가 버튼으로 선택한 직무 (예: "IT기획", "백엔드 개발")

    Returns:
        CompanyResearchResult: 개요, 인재상, 최근 이슈, 직무 키워드, 출처가 담긴 구조화 결과

    Raises:
        ValueError: company_name 또는 job_role이 비어있는 경우
    """
    if not company_name or not company_name.strip():
        raise ValueError("company_name은 비어있을 수 없습니다.")
    if not job_role or not job_role.strip():
        raise ValueError("job_role은 비어있을 수 없습니다.")

    company_name = company_name.strip()
    job_role = job_role.strip()

    search_results = await _run_searches(company_name, job_role)
    context, sources = _build_context(search_results)

    if not context:
        logger.warning(f"[company_research] '{company_name}' 검색 결과가 없어 빈 정보로 반환합니다.")
        return CompanyResearchResult(company_name=company_name, overview="검색 결과를 찾을 수 없습니다.")

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=0,
    )
    structured_llm = llm.with_structured_output(CompanyResearchResult)

    prompt = f"""다음은 '{company_name}'에 대한 웹 검색 결과입니다. 지원자는 '{job_role}' 직무에 지원합니다.

{context}

위 정보를 바탕으로 자기소개서 '지원동기'와 '직무적합성' 항목을 평가하는 AI 에이전트가
바로 참고할 수 있도록 기업 정보를 정리해주세요.
- overview: 사업영역과 핵심 서비스를 2~3문장으로 요약
- core_values: 인재상/핵심가치를 키워드 형태로 추출 (근거 없으면 빈 리스트)
- recent_issues: 지원동기에 인용 가능한 최근 이슈나 사업 방향 (최대 3개, 각 1문장)
- job_related_keywords: '{job_role}' 직무 기준으로 자격요건/필요역량 키워드 추출 (최대 8개, 근거 없으면 빈 리스트)
- company_name: '{company_name}' 그대로 사용
검색 결과에 없는 내용은 추측하지 말고 비워두세요."""

    result: CompanyResearchResult = await structured_llm.ainvoke(prompt)
    result.sources = list(dict.fromkeys(sources))[:5]  # 중복 제거 후 상위 5개만
    return result


# ─────────────────────────────────────────────
# 사용 예시
# ─────────────────────────────────────────────
# async def main():
#     result = await research_company("삼성물산", "IT기획")
#     print(result.model_dump_json(indent=2, ensure_ascii=False))
#
# asyncio.run(main())