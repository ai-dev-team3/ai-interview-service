"""
company_research.py

자기소개서 첨삭 파이프라인(Triage Agent → Specialist Agents) 중
'지원동기' / '직무적합성' 평가 에이전트에 전달할 기업 정보를 조사하는 유틸리티.

흐름:
    1. Gemini의 네이티브 google_search tool로 웹 검색을 수행하면서, 동시에
       response_schema로 구조화 출력(JSON)을 요청 (호출 1번으로 검색+추출 완료)

※ interview.py의 질문 생성과 동일하게 Gemini를 씁니다 (model 통일).
   자소서 첨삭 5개 specialist agent(agents/base.py)는 별도로 OpenAI(gpt-4o-mini)를 씁니다.
   (이전에 쓰던 Tavily 검색은 제거했습니다 — TAVILY_API_KEY 더 이상 필요 없음)

API 키는 config.py 없이 .env → os.getenv()로 직접 읽습니다 (프로젝트 컨벤션).
main.py/conftest.py가 이미 load_dotenv()를 앞단에서 호출해두므로 여기선 별도 호출 안 함.
"""

import json
import logging
import os
from typing import List

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

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
# 메인 함수
# ─────────────────────────────────────────────
async def research_company(company_name: str, job_role: str) -> CompanyResearchResult:
    """
    기업명과 지원 직무(버튼 선택값)를 입력받아 자소서 첨삭(지원동기/직무적합성) 에이전트가
    바로 활용할 수 있는 구조화된 기업 정보를 반환합니다.

    Gemini의 네이티브 google_search tool로 검색과 동시에 구조화(JSON) 출력을 받습니다.

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

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
    )

    # with_structured_output(method="function_calling")은 다른 tool과 같이 못 써서,
    # google_search tool + JSON 스키마 출력을 .bind()로 같이 지정합니다.
    llm_with_search = llm.bind(
        tools=[{"google_search": {}}],
        response_mime_type="application/json",
        response_schema=CompanyResearchResult.model_json_schema(),
    )

    prompt = f"""'{company_name}' 기업에 대한 최신 정보를 웹에서 검색하세요. 지원자는 '{job_role}' 직무에 지원합니다.

검색 결과를 바탕으로 자기소개서 '지원동기'와 '직무적합성' 항목을 평가하는 AI 에이전트가
바로 참고할 수 있도록 아래 항목을 JSON으로 정리해주세요.
- company_name: '{company_name}' 그대로 사용
- overview: 사업영역과 핵심 서비스를 2~3문장으로 요약
- core_values: 인재상/핵심가치를 키워드 형태로 추출 (근거 없으면 빈 리스트)
- recent_issues: 지원동기에 인용 가능한 최근 이슈나 사업 방향 (최대 3개, 각 1문장)
- job_related_keywords: '{job_role}' 직무 기준으로 자격요건/필요역량 키워드 추출 (최대 8개, 근거 없으면 빈 리스트)
- sources: 검색 과정에서 참고한 출처 URL (확인 가능한 만큼만)
검색 결과에 없는 내용은 추측하지 말고 비워두세요."""

    response = await llm_with_search.ainvoke(prompt)

    try:
        data = json.loads(response.content)
        result = CompanyResearchResult(**data)
    except Exception as exc:
        logger.warning(f"[company_research] '{company_name}' 응답 파싱 실패, 빈 정보로 반환: {exc}")
        return CompanyResearchResult(company_name=company_name, overview="검색 결과를 찾을 수 없습니다.")

    return result


# ─────────────────────────────────────────────
# 사용 예시
# ─────────────────────────────────────────────
# async def main():
#     result = await research_company("삼성물산", "IT기획")
#     print(result.model_dump_json(indent=2, ensure_ascii=False))
#
# asyncio.run(main())