"""DB-backed career readiness diagnosis service."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.repository.career import (
    ActionTemplate,
    CareerDiagnosisResult,
    JobGroup,
    JobReadinessCriteria,
)
from app.repository.user import User
from app.services.cover_letter import cover_letter_service
from app.services.llm import get_chat_model
from app.services.resume import resume_service

logger = logging.getLogger(__name__)


class CareerDiagnosisPrerequisiteError(Exception):
    """Resume and cover letter are required before running career diagnosis."""


class CareerDiagnosisConfigError(Exception):
    """Career criteria seed data is missing or invalid."""


class LLMCriterionReview(BaseModel):
    criterion_name: str
    score: int = Field(ge=0, le=100)
    feedback: str
    evidence_summary: str = ""
    is_keyword_stuffed: bool = False


class LLMDiagnosisReview(BaseModel):
    criteria: list[LLMCriterionReview]
    overall_comment: str = ""


DEFAULT_JOB_GROUPS = [
    {
        "id": 1,
        "name": "백엔드 개발",
        "description": "서버, API, 데이터베이스, 배포를 중심으로 하는 개발 직무",
        "keywords": [
            "백엔드", "서버", "api", "rest", "fastapi", "spring", "mysql",
            "postgresql", "erd", "docker", "nginx", "배포", "트러블슈팅",
        ],
    },
    {
        "id": 2,
        "name": "프론트엔드 개발",
        "description": "웹 UI 구현, 상태 관리, API 연동, 사용자 경험 개선 직무",
        "keywords": [
            "프론트엔드", "react", "next", "vue", "typescript", "ui",
            "컴포넌트", "상태관리", "axios", "figma", "vercel", "ux",
        ],
    },
    {
        "id": 3,
        "name": "데이터/AI",
        "description": "데이터 처리, 분석, 머신러닝·AI 모델 활용 직무",
        "keywords": [
            "데이터", "python", "pandas", "sql", "머신러닝", "딥러닝",
            "모델", "분석", "전처리", "시각화", "지표", "llm",
        ],
    },
    {
        "id": 4,
        "name": "서비스기획/PM",
        "description": "문제 정의, 요구사항, 정책, UX, 일정 조율을 담당하는 기획 직무",
        "keywords": [
            "서비스기획", "pm", "po", "문제 정의", "요구사항", "prd", "정책",
            "ux", "figma", "지표", "kpi", "협업", "일정",
        ],
    },
    {
        "id": 5,
        "name": "마케팅",
        "description": "콘텐츠, 캠페인, 채널 운영, 성과 분석 중심의 마케팅 직무",
        "keywords": [
            "마케팅", "콘텐츠", "캠페인", "sns", "고객", "타깃", "시장조사",
            "조회수", "전환율", "ga4", "광고관리자", "브랜딩",
        ],
    },
    {
        "id": 6,
        "name": "인사/총무",
        "description": "채용, 온보딩, 조직 운영, 총무 지원 직무",
        "keywords": [
            "인사", "총무", "채용", "온보딩", "지원자", "조직", "비품",
            "자산", "규정", "계약", "개인정보", "복리후생",
        ],
    },
    {
        "id": 7,
        "name": "회계/재무",
        "description": "회계 처리, 정산, 전표, 재무 자료 관리 직무",
        "keywords": [
            "회계", "재무", "전표", "정산", "마감", "비용", "세금계산서",
            "부가세", "erp", "더존", "계정", "예산",
        ],
    },
    {
        "id": 8,
        "name": "사무행정",
        "description": "문서 작성, OA, 일정 관리, 행정 지원 직무",
        "keywords": [
            "사무", "행정", "문서", "보고서", "회의록", "excel", "엑셀",
            "word", "ppt", "일정", "업무관리", "응대", "정확성",
        ],
    },
    {
        "id": 9,
        "name": "영업/영업지원",
        "description": "고객 발굴, 제안, 상담, 영업 자료와 실적 관리 직무",
        "keywords": [
            "영업", "영업지원", "고객", "제안", "상담", "견적", "계약",
            "crm", "매출", "실적", "목표", "고객관리",
        ],
    },
    {
        "id": 10,
        "name": "고객상담/CS",
        "description": "고객 문의 응대, 문제 해결, 서비스 운영 지원 직무",
        "keywords": [
            "cs", "고객상담", "문의", "응대", "상담", "클레임", "불만",
            "서비스", "faq", "매뉴얼", "기록", "이관",
        ],
    },
    {
        "id": 11,
        "name": "디자인",
        "description": "UI/UX, 그래픽, 브랜딩, 콘텐츠 디자인 직무",
        "keywords": [
            "디자인", "figma", "photoshop", "illustrator", "포트폴리오",
            "ui", "ux", "브랜딩", "그래픽", "시안", "프로토타입",
        ],
    },
    {
        "id": 12,
        "name": "생산/물류",
        "description": "생산관리, 품질관리, 구매·자재, 물류관리 직무",
        "keywords": [
            "생산", "물류", "공정", "품질", "재고", "입고", "출고",
            "창고", "자재", "안전", "현장", "납기",
        ],
    },
]


JOB_GROUP_EVALUATION_RUBRICS = {
    "백엔드 개발": {
        "direct": [
            "API/서버 기능을 본인이 설계·구현한 기능명, 요청/응답, 인증·인가, 예외 처리 근거",
            "DB 테이블·관계·쿼리·트랜잭션·인덱스 등 데이터 설계와 사용 근거",
            "장애, 오류, 성능 문제를 원인 분석부터 해결 결과까지 설명한 사례",
            "Docker, Nginx, AWS, CI/CD 등 배포·운영 흐름을 직접 다룬 근거",
        ],
        "weak": [
            "Python, Java, Spring 같은 기술명만 나열하고 어떤 기능에 썼는지 없는 경우",
            "프론트 화면 구현이나 디자인 경험만 있고 서버/API 역할이 없는 경우",
            "팀 프로젝트라고만 쓰고 본인의 백엔드 책임 범위가 불분명한 경우",
        ],
        "cap": [
            "서버/API 직접 구현 근거가 없으면 40점 이하로 제한하세요.",
            "기술명만 반복되고 역할·문제·결과가 없으면 25점 이하로 제한하세요.",
        ],
    },
    "프론트엔드 개발": {
        "direct": [
            "React, Next, Vue 등으로 구현한 화면·컴포넌트·상태 관리 구조 근거",
            "API 연동, 로딩·에러 처리, 인증 상태 처리 등 사용자 흐름 구현 근거",
            "반응형, 접근성, 렌더링 성능, UX 개선 전후가 드러나는 사례",
            "Figma 협업, PR, 배포 링크, 화면 캡처처럼 결과물을 확인할 수 있는 근거",
        ],
        "weak": [
            "HTML/CSS 또는 React 이름만 있고 구현 화면이나 컴포넌트 역할이 없는 경우",
            "백엔드 API 개발 경험만 있고 프론트 UI 구현 근거가 없는 경우",
            "디자인 시안만 있고 실제 웹 구현·상호작용 처리 근거가 없는 경우",
        ],
        "cap": [
            "사용자가 보는 화면 구현 근거가 없으면 40점 이하로 제한하세요.",
            "단순 퍼블리싱 언급만 있고 상태/API/UX 근거가 없으면 고득점을 주지 마세요.",
        ],
    },
    "데이터/AI": {
        "direct": [
            "데이터 수집·정제·전처리 규칙과 사용한 데이터 규모·형태 근거",
            "SQL, Pandas, 모델링, LLM 활용 등 분석·모델 구현 과정 근거",
            "Accuracy, F1, RMSE, AUC 등 평가 지표와 결과 해석 근거",
            "분석 결과가 의사결정, 서비스 개선, 보고서, 대시보드로 이어진 근거",
        ],
        "weak": [
            "Python만 언급하고 데이터 처리·분석·모델링 흐름이 없는 경우",
            "AI라는 단어만 있고 입력 데이터, 모델, 평가 기준이 없는 경우",
            "시각화 이미지만 있고 인사이트나 지표 해석이 없는 경우",
        ],
        "cap": [
            "데이터를 실제로 다룬 근거가 없으면 40점 이하로 제한하세요.",
            "모델·분석 결과를 검증한 지표가 전혀 없으면 모델링 항목은 고득점을 주지 마세요.",
        ],
    },
    "서비스기획/PM": {
        "direct": [
            "사용자 문제, 타깃, 가설, 목표를 근거와 함께 정의한 사례",
            "PRD, 요구사항, 정책, 유저스토리, 수용 기준 등 문서화 근거",
            "사용자 흐름, 와이어프레임, 화면 설계, 우선순위 조율 근거",
            "KPI, 퍼널, 전환율, 리텐션 등 지표로 기획 결과를 검토한 근거",
        ],
        "weak": [
            "아이디어 제안만 있고 문제 정의나 사용자 근거가 없는 경우",
            "개발 참여 경험만 있고 요구사항·정책·조율 역할이 없는 경우",
            "Figma 화면만 있고 기획 의도나 정책 결정 근거가 없는 경우",
        ],
        "cap": [
            "문제 정의와 요구사항 정리 근거가 없으면 40점 이하로 제한하세요.",
            "단순 아이디어 나열은 실행 기획 경험으로 높게 인정하지 마세요.",
        ],
    },
    "마케팅": {
        "direct": [
            "캠페인 목표, 타깃, 채널, 메시지, 콘텐츠 실행 과정 근거",
            "조회수, 클릭률, 전환율, ROAS, 참여율 등 성과 지표와 해석 근거",
            "고객·시장·경쟁사 분석을 바탕으로 메시지나 채널을 선택한 근거",
            "A/B 테스트, 소재 개선, 카피 개선 등 실험과 개선 전후 근거",
        ],
        "weak": [
            "SNS 운영이라고만 쓰고 목표·타깃·성과 수치가 없는 경우",
            "디자인 콘텐츠 제작만 있고 마케팅 목표나 지표가 없는 경우",
            "브랜딩, 홍보 같은 단어만 있고 실행 채널과 결과가 없는 경우",
        ],
        "cap": [
            "성과 지표나 고객/타깃 근거가 없으면 55점 이상을 주지 마세요.",
            "콘텐츠 제작만 있고 캠페인 목적·결과가 없으면 고득점을 주지 마세요.",
        ],
    },
    "인사/총무": {
        "direct": [
            "채용 일정, 지원자 관리, 면접 조율, 온보딩 지원 등 HR 운영 근거",
            "비품, 자산, 계약, 행사, 복리후생 등 총무 운영 절차 근거",
            "개인정보, 규정, 증빙, 문서 관리에서 정확성과 보안을 지킨 근거",
            "구성원, 지원자, 외부 업체와의 안내·조율·응대 사례",
        ],
        "weak": [
            "사무보조라고만 쓰고 인사/총무 업무 범위가 드러나지 않는 경우",
            "행사 참여 경험만 있고 운영·조율 책임이 없는 경우",
            "친절함 같은 태도만 있고 민감 자료 관리나 절차 근거가 없는 경우",
        ],
        "cap": [
            "채용/조직운영/총무 중 하나 이상의 직접 업무 근거가 없으면 40점 이하로 제한하세요.",
            "개인정보나 문서 정확성 근거가 없으면 보안·정확성 항목은 고득점을 주지 마세요.",
        ],
    },
    "회계/재무": {
        "direct": [
            "전표, 계정과목, 세금계산서, 증빙, 정산, 월마감 처리 근거",
            "ERP, 더존, Excel 함수·피벗 등 회계 자료 처리 도구 활용 근거",
            "금액 대조, 잔액 확인, 오류 발견·수정 등 숫자 검증 근거",
            "비용, 예산, 손익, 추이 등 수치 해석이나 보고 근거",
        ],
        "weak": [
            "돈을 관리했다는 표현만 있고 회계 처리 단위나 증빙 근거가 없는 경우",
            "Excel 사용만 있고 회계·정산·마감 업무와 연결되지 않는 경우",
            "꼼꼼함만 강조하고 숫자 검증 사례가 없는 경우",
        ],
        "cap": [
            "회계/정산/증빙 처리 근거가 없으면 40점 이하로 제한하세요.",
            "숫자 정확성 검증 근거가 없으면 정확성 항목은 고득점을 주지 마세요.",
        ],
    },
    "사무행정": {
        "direct": [
            "회의록, 보고서, 공문, 정리 문서 등 실제 문서 작성 근거",
            "Excel, Word, PPT로 처리한 표·함수·자료 정리·보고 업무 근거",
            "일정 조율, 예약, 체크리스트, 마감 관리 등 행정 운영 근거",
            "부서·고객·동료와 요청을 전달하고 누락을 줄인 커뮤니케이션 근거",
        ],
        "weak": [
            "개발·마케팅 프로젝트 경험만 있고 문서/OA/일정관리 근거가 없는 경우",
            "성실함, 꼼꼼함만 있고 어떤 자료를 어떻게 처리했는지 없는 경우",
            "팀 활동 참여만 있고 행정 지원 역할이 드러나지 않는 경우",
        ],
        "cap": [
            "문서 작성 또는 OA 활용 직접 근거가 없으면 40점 이하로 제한하세요.",
            "다른 직군 경험을 사무행정으로 인정하려면 문서화·일정관리·자료정리 근거가 필요합니다.",
        ],
    },
    "영업/영업지원": {
        "direct": [
            "고객 발굴, 니즈 파악, 상담, 제안, 견적, 계약 후속 관리 근거",
            "CRM, 고객 리스트, 견적서, 영업 자료를 관리한 근거",
            "매출, 계약 수, 전환율, 목표 달성률 등 영업 성과 수치 근거",
            "고객 요청을 내부 부서와 조율해 해결한 커뮤니케이션 근거",
        ],
        "weak": [
            "고객 응대만 있고 제안·상담·후속 관리 흐름이 없는 경우",
            "서비스를 설명했다는 말만 있고 고객 니즈 파악 근거가 없는 경우",
            "성과 수치 없이 열심히 판매했다는 표현만 있는 경우",
        ],
        "cap": [
            "고객 접점과 제안/상담 근거가 없으면 40점 이하로 제한하세요.",
            "성과 관리 근거가 없으면 실적/목표 항목은 고득점을 주지 마세요.",
        ],
    },
    "고객상담/CS": {
        "direct": [
            "문의, 불만, 클레임, 요청을 응대하고 해결한 구체 사례",
            "서비스 정책·기능·FAQ·매뉴얼을 이해하고 고객에게 안내한 근거",
            "상담 기록, 이슈 이관, 후속 관리, 재발 방지로 연결한 근거",
            "까다로운 고객 상황에서 경청·공감·감정 관리를 한 근거",
        ],
        "weak": [
            "친절하다는 태도만 있고 실제 응대 상황과 처리 결과가 없는 경우",
            "고객이라는 단어만 있고 문의 유형이나 해결 과정이 없는 경우",
            "영업 성과만 있고 상담 기록·문제 해결 근거가 없는 경우",
        ],
        "cap": [
            "고객 문의를 처리한 실제 사례가 없으면 40점 이하로 제한하세요.",
            "서비스 이해나 기록/후속 관리 근거가 없으면 CS 전문성 항목은 고득점을 주지 마세요.",
        ],
    },
    "디자인": {
        "direct": [
            "Figma, Photoshop, Illustrator 등으로 만든 결과물과 본인 작업 범위 근거",
            "문제, 목표, 사용자, 디자인 의도, 최종 산출물을 설명한 포트폴리오 근거",
            "UX 흐름, 와이어프레임, 프로토타입, 사용성 개선 근거",
            "기획·개발 피드백을 반영해 디자인을 수정한 협업 근거",
        ],
        "weak": [
            "툴 이름만 있고 작업물의 목적·의도·결과가 없는 경우",
            "이미지 제작만 있고 사용자 문제나 브랜드/UX 맥락이 없는 경우",
            "개발 구현 경험만 있고 디자인 산출물 근거가 없는 경우",
        ],
        "cap": [
            "확인 가능한 디자인 결과물 또는 포트폴리오 근거가 없으면 40점 이하로 제한하세요.",
            "툴 사용만 있고 디자인 의사결정 근거가 없으면 고득점을 주지 마세요.",
        ],
    },
    "생산/물류": {
        "direct": [
            "생산 공정, 작업 라인, 현장 운영, 납기 관리 흐름을 이해한 근거",
            "품질 검사, 불량 확인, 안전 점검, 표준 준수 사례",
            "입고, 출고, 재고, 창고, 자재, 배송 데이터를 관리한 근거",
            "Excel이나 시스템으로 수량·불량·입출고 데이터를 기록·분석한 근거",
        ],
        "weak": [
            "현장 경험이라고만 쓰고 공정·품질·재고 중 어떤 업무인지 없는 경우",
            "단순 아르바이트 경험만 있고 생산/물류 관리 관점이 없는 경우",
            "체력이나 성실함만 있고 안전·품질·수량 관리 근거가 없는 경우",
        ],
        "cap": [
            "공정/품질/재고 중 하나 이상의 직접 근거가 없으면 40점 이하로 제한하세요.",
            "현장 데이터를 다룬 근거가 없으면 관리·개선 항목은 고득점을 주지 마세요.",
        ],
    },
}


def list_job_groups(db: Session) -> list[dict]:
    groups = (
        db.query(JobGroup)
        .filter(JobGroup.is_active.is_(True))
        .order_by(JobGroup.id)
        .all()
    )
    return [
        {"id": group.id, "name": group.name, "description": group.description}
        for group in groups
    ]


def _structured_to_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(v) for v in value)
    if value is None:
        return ""
    return str(value)


def _has_meaningful_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_meaningful_value(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_meaningful_value(v) for v in value)
    return value is not None


def _keyword_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _count_matches(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    normalized = text.lower()
    seen = set()
    matches = []
    for keyword in keywords:
        key = keyword.lower()
        if key in seen:
            continue
        seen.add(key)
        if key in normalized:
            matches.append(keyword)
    return len(matches), matches


_ACTION_INDICATORS = [
    "개발", "구현", "설계", "해결", "개선", "분석", "작성", "기획", "운영", "배포",
    "관리", "활용", "정리", "제작", "도입", "검토", "확인", "수정", "테스트", "협업",
    "조율", "응대", "발표", "제안", "자동화", "최적화", "리팩토링", "built", "implemented",
    "designed", "deployed", "managed", "analyzed",
]
_RESULT_INDICATORS = [
    "결과", "성과", "달성", "증가", "감소", "개선", "완료", "성공", "효율", "시간",
    "기간", "사용자", "고객", "트래픽", "매출", "조회수", "전환율", "%", "명", "건",
    "회", "점", "등", "위",
]
_ROLE_INDICATORS = [
    "제가", "본인", "담당", "역할", "주도", "참여", "맡", "기여", "책임", "리드",
    "직접", "팀", "협업",
]
_PROBLEM_INDICATORS = [
    "문제", "과제", "상황", "어려움", "이슈", "오류", "에러", "원인", "요구사항",
    "목표", "필요",
]
_MATERIAL_KEYWORDS = [
    "github",
    "포트폴리오",
    "readme",
    "erd",
    "api 명세",
    "자격증",
    "보고서",
    "기획서",
    "배포",
]
_PLACEHOLDER_PATTERNS = [
    r"^질문\s*\d*$",
    r"^답변\s*\d*$",
    r"^question\s*\d*$",
    r"^answer\s*\d*$",
    r"^test$",
    r"^테스트$",
    r"^asdf+$",
    r"^ㅇ+$",
    r"^ㅋ+$",
    r"^ㅎ+$",
    r"^\d+$",
]


def _contains_any(text: str, words: list[str]) -> bool:
    normalized = text.lower()
    return any(word.lower() in normalized for word in words)


def _normalize_for_quality(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _meaningful_length(text: str) -> int:
    return len(re.sub(r"[^0-9A-Za-z가-힣]", "", text or ""))


def _is_placeholder_text(text: str) -> bool:
    normalized = _normalize_for_quality(text).lower()
    if not normalized:
        return True
    if any(re.fullmatch(pattern, normalized) for pattern in _PLACEHOLDER_PATTERNS):
        return True
    if _meaningful_length(normalized) <= 2:
        return True
    return False


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?。！？])\s+|[\n\r]+|[•·\-]\s*", text or "")
    return [re.sub(r"\s+", " ", chunk).strip() for chunk in chunks if chunk.strip()]


def _is_evidence_sentence(sentence: str) -> bool:
    compact = sentence.strip()
    if len(compact) < 12:
        return False
    return _contains_any(compact, _ACTION_INDICATORS) or _contains_any(compact, _RESULT_INDICATORS)


def _keyword_occurrences(text: str, keywords: list[str]) -> dict[str, int]:
    normalized = text.lower()
    counts: dict[str, int] = {}
    for keyword in keywords:
        key = keyword.lower()
        if not key:
            continue
        counts[keyword] = normalized.count(key)
    return counts


def _find_keyword_evidence(text: str, keywords: list[str]) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for sentence in _split_sentences(text):
        normalized_sentence = sentence.lower()
        if not _is_evidence_sentence(sentence):
            continue
        for keyword in keywords:
            if keyword.lower() in normalized_sentence and keyword not in evidence:
                evidence[keyword] = sentence
    return evidence


def _keyword_stuffing_penalty(text: str, matched_keywords: list[str]) -> int:
    if not matched_keywords:
        return 0

    counts = _keyword_occurrences(text, matched_keywords)
    repeated_overage = sum(max(0, count - 2) for count in counts.values())
    if repeated_overage <= 2:
        return 0

    evidence_count = len(_find_keyword_evidence(text, matched_keywords))
    if evidence_count >= len(matched_keywords):
        return min(8, repeated_overage)
    return min(20, repeated_overage * 3)


def _criterion_cap(matched_keywords: list[str], evidence_keywords: list[str]) -> int:
    if not matched_keywords:
        return 25
    if not evidence_keywords:
        return 40
    return 100


def _group_match_keywords(group: JobGroup, criteria: list[JobReadinessCriteria]) -> list[str]:
    words = [group.name, group.description or ""]
    for seed_group in DEFAULT_JOB_GROUPS:
        if seed_group["name"] == group.name:
            words.extend(seed_group["keywords"])
            break
    for criterion in criteria:
        words.extend(_keyword_list(criterion.keywords))
    return [word for word in words if word]


def _job_group_evaluation_rubric(job_group: JobGroup | str) -> str:
    group_name = job_group if isinstance(job_group, str) else job_group.name
    rubric = JOB_GROUP_EVALUATION_RUBRICS.get(group_name)
    if not rubric:
        return "직무군별 별도 평가 가이드가 없습니다. 평가 기준 설명과 키워드를 우선하여 엄격하게 판단하세요."

    labels = {
        "direct": "높게 인정할 직접 근거",
        "weak": "약하게 볼 근거",
        "cap": "상한/감점 기준",
    }
    lines = [f"{group_name} 직무군 평가 가이드"]
    for key in ("direct", "weak", "cap"):
        items = rubric.get(key, [])
        if not items:
            continue
        lines.append(f"{labels[key]}:")
        lines.extend(f"- {item}" for item in items)
    return "\n".join(lines)


def _load_active_groups_with_criteria(db: Session) -> tuple[list[JobGroup], dict[int, list[JobReadinessCriteria]]]:
    groups = (
        db.query(JobGroup)
        .filter(JobGroup.is_active.is_(True))
        .order_by(JobGroup.id)
        .all()
    )
    criteria_by_group: dict[int, list[JobReadinessCriteria]] = {group.id: [] for group in groups}
    group_ids = [group.id for group in groups]
    if not group_ids:
        return groups, criteria_by_group

    criteria = (
        db.query(JobReadinessCriteria)
        .filter(JobReadinessCriteria.job_group_id.in_(group_ids))
        .order_by(
            JobReadinessCriteria.job_group_id,
            JobReadinessCriteria.sort_order,
            JobReadinessCriteria.id,
        )
        .all()
    )
    for criterion in criteria:
        criteria_by_group.setdefault(criterion.job_group_id, []).append(criterion)
    return groups, criteria_by_group


def _choose_job_group(
    groups: list[JobGroup],
    criteria_by_group: dict[int, list[JobReadinessCriteria]],
    desired_job: str,
    corpus: str,
) -> JobGroup | None:
    if not groups:
        raise CareerDiagnosisConfigError("등록된 직무군이 없습니다.")

    target_text = f"{desired_job} {corpus}".lower()
    scored = []
    for group in groups:
        score, _ = _count_matches(target_text, _group_match_keywords(group, criteria_by_group.get(group.id, [])))
        scored.append((score, group))
    scored.sort(key=lambda item: (item[0], -item[1].id), reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else None


def _job_fit_cap(score: int) -> int:
    if score < 25:
        return 25
    if score < 40:
        return 40
    if score < 55:
        return 55
    if score < 70:
        return 70
    return 100


def _assess_job_group_fit(
    job_group: JobGroup,
    groups: list[JobGroup],
    criteria_by_group: dict[int, list[JobReadinessCriteria]],
    content: str,
) -> dict:
    target_keywords = _group_match_keywords(job_group, criteria_by_group.get(job_group.id, []))
    _, matched_keywords = _count_matches(content, target_keywords)
    evidence_by_keyword = _find_keyword_evidence(content, matched_keywords)

    competing_keywords: list[str] = []
    for group in groups:
        if group.id == job_group.id:
            continue
        _, group_matches = _count_matches(
            content,
            _group_match_keywords(group, criteria_by_group.get(group.id, [])),
        )
        competing_keywords.extend(group_matches)

    competing_unique = list(dict.fromkeys(competing_keywords))
    evidence_keywords = list(evidence_by_keyword.keys())
    score = min(100, len(evidence_keywords) * 22 + max(0, len(matched_keywords) - len(evidence_keywords)) * 4)
    if competing_unique and len(competing_unique) > max(1, len(matched_keywords)) * 2 and score < 70:
        score = max(0, score - min(20, (len(competing_unique) - len(matched_keywords)) * 2))

    cap = _job_fit_cap(score)
    return {
        "score": score,
        "cap": cap,
        "matched_keywords": matched_keywords[:8],
        "evidence_keywords": evidence_keywords[:8],
        "competing_keywords": competing_unique[:8],
        "feedback": (
            "선택 직무군과 직접 연결된 경험 근거가 충분합니다."
            if cap == 100
            else "선택 직무군과 직접 연결된 경험 근거가 부족해 점수 상한이 적용되었습니다."
        ),
    }


def _apply_job_fit_cap(criteria_results: list[dict], job_fit: dict) -> list[dict]:
    cap = int(job_fit.get("cap", 100))
    if cap >= 100:
        return criteria_results

    capped_results = []
    for item in criteria_results:
        capped_score = min(int(item["score"]), cap)
        updated = {
            **item,
            "score": capped_score,
            "job_fit_cap": cap,
            "job_fit_capped": capped_score < int(item["score"]),
        }
        if updated["job_fit_capped"]:
            updated["feedback"] += f" 직무 적합성 검토 결과 {cap}점 상한이 적용되었습니다."
        capped_results.append(updated)
    return capped_results


def _specificity_score(structured: dict, content: str) -> int:
    text_length = len(content.strip())
    length_score = min(10, text_length // 180)

    sections = 0
    for key in ("skills", "career", "projects", "self_introduction", "education"):
        if _has_meaningful_value(structured.get(key)):
            sections += 1

    return min(20, length_score + sections * 2)


def _material_score(corpus: str) -> int:
    _, raw_matches = _count_matches(corpus, _MATERIAL_KEYWORDS)
    evidence = _find_keyword_evidence(corpus, _MATERIAL_KEYWORDS)
    evidence_matches = [keyword for keyword in raw_matches if keyword in evidence]
    weak_matches = [keyword for keyword in raw_matches if keyword not in evidence]
    return min(20, len(evidence_matches) * 5 + len(weak_matches) * 2)


def _answer_unit_quality(pair: dict[str, str]) -> int:
    question = (pair.get("question_text") or "").strip()
    answer = (pair.get("answer_text") or "").strip()
    if not answer:
        return 0

    score = 0
    answer_length = len(answer)
    score += min(5, answer_length // 80)
    if _contains_any(answer, _ROLE_INDICATORS):
        score += 4
    if _contains_any(answer, _PROBLEM_INDICATORS):
        score += 5
    if _contains_any(answer, _ACTION_INDICATORS):
        score += 6
    if _contains_any(answer, _RESULT_INDICATORS):
        score += 6
    if question and len(answer) >= 40:
        score += 2
    return min(25, score)


def _qa_unit_quality_score(answer_units: list[dict[str, str]], keywords: list[str]) -> int:
    if not answer_units:
        return 0

    relevant_scores = []
    generic_scores = []
    for pair in answer_units:
        unit_text = f"{pair.get('question_text', '')} {pair.get('answer_text', '')}"
        score = _answer_unit_quality(pair)
        generic_scores.append(score)
        if any(keyword.lower() in unit_text.lower() for keyword in keywords):
            relevant_scores.append(score)

    if relevant_scores:
        return round(sum(sorted(relevant_scores, reverse=True)[:2]) / min(2, len(relevant_scores)))

    generic_average = round(sum(generic_scores) / len(generic_scores))
    return min(8, round(generic_average * 0.35))


def _assess_input_quality(resume_content: str, answer_units: list[dict[str, str]]) -> list[str]:
    reasons: list[str] = []
    resume_text = _normalize_for_quality(resume_content)
    if _is_placeholder_text(resume_text) or _meaningful_length(resume_text) < 40:
        reasons.append("이력서 내용이 너무 짧거나 임시 문구라서 평가할 수 없습니다.")

    if not answer_units:
        reasons.append("자소서 질문/답변이 없어 평가할 수 없습니다.")
        return reasons

    meaningful_answers = []
    placeholder_answers = []
    for index, pair in enumerate(answer_units, start=1):
        question = _normalize_for_quality(pair.get("question_text", ""))
        answer = _normalize_for_quality(pair.get("answer_text", ""))
        if _is_placeholder_text(question) and _is_placeholder_text(answer):
            placeholder_answers.append(index)
            continue
        if _is_placeholder_text(answer) or _meaningful_length(answer) < 20:
            placeholder_answers.append(index)
            continue
        meaningful_answers.append(answer)

    if not meaningful_answers:
        reasons.append("자소서 답변이 '답변1', '테스트' 같은 임시 문구이거나 너무 짧아 평가할 수 없습니다.")
    elif sum(_meaningful_length(answer) for answer in meaningful_answers) < 50:
        reasons.append("자소서 답변의 전체 분량이 부족해 직무 준비도를 판단하기 어렵습니다.")

    if placeholder_answers and meaningful_answers:
        reasons.append(f"{', '.join(str(i) for i in placeholder_answers)}번 자소서 답변이 임시 문구이거나 너무 짧습니다.")

    return reasons


def _build_unavailable_payload(
    *,
    job_group: JobGroup,
    cover_letter,
    desired_job: str,
    reasons: list[str],
) -> dict:
    reason_text = " ".join(reasons)
    return {
        "job_group": {
            "id": job_group.id,
            "name": job_group.name,
            "description": job_group.description,
        },
        "source_cover_letter": {
            "id": cover_letter.id,
            "title": cover_letter.title,
            "company_name": cover_letter.company_name,
            "job_group_id": cover_letter.job_group_id,
        },
        "desired_job": desired_job,
        "total_score": 0,
        "score_label": "평가 불가",
        "summary": f"입력 자료가 충분하지 않아 취업 준비도 진단을 진행할 수 없습니다. {reason_text}",
        "strengths": [],
        "weaknesses": [],
        "criteria_results": [],
        "action_plan": [],
        "evaluation_available": False,
        "unavailable_reasons": reasons,
        "llm_reviewed": False,
        "caution": "이력서와 자소서에 실제 경험, 본인 역할, 수행한 행동, 결과 근거를 작성한 뒤 다시 진단해주세요.",
    }


def _score_criterion(
    criterion: JobReadinessCriteria,
    structured: dict,
    content: str,
    answer_units: list[dict[str, str]] | None = None,
) -> dict:
    keywords = _keyword_list(criterion.keywords)
    structured_text = _flatten(structured)
    corpus = f"{content} {structured_text}"
    _, matched_keywords = _count_matches(corpus, keywords)
    evidence_by_keyword = _find_keyword_evidence(content, keywords)
    structured_matches = [
        keyword
        for keyword in matched_keywords
        if keyword.lower() in structured_text.lower()
    ]
    evidence_matched_keywords = list(dict.fromkeys([
        *evidence_by_keyword.keys(),
        *structured_matches,
    ]))

    if evidence_matched_keywords:
        keyword_score = min(35, len(evidence_matched_keywords) * 10)
    else:
        keyword_score = min(10, len(matched_keywords) * 3)

    detail_score = _specificity_score(structured, content)
    material_score = _material_score(corpus)
    if not evidence_matched_keywords:
        material_score = min(4, material_score)
    qa_score = _qa_unit_quality_score(answer_units or [], keywords)
    stuffing_penalty = _keyword_stuffing_penalty(content, matched_keywords)
    criterion_cap = _criterion_cap(matched_keywords, evidence_matched_keywords)
    raw_score = max(0, keyword_score + detail_score + material_score + qa_score - stuffing_penalty)
    score = max(0, min(criterion_cap, raw_score))

    if score >= 75:
        feedback = f"{criterion.criterion_name}은 현재 자료에서 근거가 비교적 잘 보입니다."
    elif score >= 55:
        feedback = f"{criterion.criterion_name}은 기본 근거가 있으나 역할, 행동, 결과를 더 구체화하면 좋습니다."
    else:
        feedback = f"{criterion.criterion_name}은 자료에서 확인되는 실행 근거가 부족합니다. 액션 플랜부터 보완해보세요."

    if evidence_matched_keywords:
        feedback += f" 근거가 확인된 키워드: {', '.join(evidence_matched_keywords[:4])}"
    elif matched_keywords:
        feedback += f" 키워드는 있으나 수행 근거 문장이 부족합니다: {', '.join(matched_keywords[:4])}"
    if qa_score < 10:
        feedback += " 자소서 답변은 문제-행동-결과 구조를 더 보완해주세요."
    if stuffing_penalty:
        feedback += " 키워드 반복 나열 가능성이 있어 일부 감점되었습니다."
    if criterion_cap < 100:
        feedback += f" 선택 기준과 직접 연결된 실행 근거가 부족해 {criterion_cap}점 상한이 적용되었습니다."

    return {
        "criterion_id": criterion.id,
        "criterion_name": criterion.criterion_name,
        "description": criterion.description,
        "score": score,
        "raw_score": raw_score,
        "rule_score": score,
        "weight": criterion.weight,
        "feedback": feedback,
        "matched_keywords": matched_keywords,
        "evidence_keywords": evidence_matched_keywords,
        "keyword_score": keyword_score,
        "specificity_score": detail_score,
        "material_score": material_score,
        "qa_score": qa_score,
        "keyword_stuffing_penalty": stuffing_penalty,
        "criterion_cap": criterion_cap,
        "llm_reviewed": False,
    }


_LLM_REVIEW_TEMPLATE = """당신은 채용 담당자이자 커리어 코치입니다.
지원자의 이력서와 자기소개서 답변을 바탕으로 취업 준비도 평가 기준별 점수를 검토하세요.

중요한 원칙:
- 키워드가 많아도 실제 역할, 행동, 문제 해결, 결과 근거가 없으면 낮게 평가하세요.
- 선택 직무군과 직접 관련 없는 경험은 일반 역량으로만 제한적으로 인정하고 높은 점수를 주지 마세요.
- 예를 들어 개발 프로젝트 경험은 사무행정 기준의 문서 작성, OA/Excel, 일정 관리 근거가 명확할 때만 인정하세요.
- 평가 기준과 직접 연결된 경험 근거가 없으면 40점 이하로 평가하세요.
- 평가 기준 키워드 자체가 없거나 다른 직군 경험만 있으면 25점 이하로 평가하세요.
- 자료가 성실하게 작성되어 있어도 선택 직무군과 직접 맞지 않으면 높은 점수를 주지 마세요.
- 같은 키워드를 반복하거나 나열만 한 경우 is_keyword_stuffed를 true로 표시하세요.
- 자기소개서 질문/답변 단위로 답변이 질문에 맞는지, STAR 구조가 있는지 확인하세요.
- 원문에 없는 경험을 추측하지 마세요.
- 모든 출력은 한국어로 작성하세요.

직무군: {job_group}

직무군별 세부 평가 가이드:
{job_group_rubric}

평가 기준과 룰 기반 1차 점수:
{criteria}

이력서 요약/원문:
{resume_content}

자기소개서 Q/A:
{cover_letter_items}
"""


class CareerReadinessLLMReviewer:
    def __init__(self, llm: Runnable | None = None):
        self.llm = llm if llm is not None else get_chat_model(
            primary="gemini",
            temperature=0.1,
            max_tokens=3000,
            schema=LLMDiagnosisReview,
        )
        self.chain = ChatPromptTemplate.from_template(_LLM_REVIEW_TEMPLATE) | self.llm

    def review(
        self,
        *,
        job_group: JobGroup,
        criteria_results: list[dict],
        resume_content: str,
        answer_units: list[dict[str, str]],
    ) -> dict[str, dict]:
        criteria_payload = [
            {
                "criterion_name": item["criterion_name"],
                "description": item["description"],
                "rule_score": item["score"],
                "matched_keywords": item.get("matched_keywords", []),
                "evidence_keywords": item.get("evidence_keywords", []),
                "feedback": item["feedback"],
            }
            for item in criteria_results
        ]
        result = self.chain.invoke({
            "job_group": job_group.name,
            "job_group_rubric": _job_group_evaluation_rubric(job_group),
            "criteria": json.dumps(criteria_payload, ensure_ascii=False),
            "resume_content": resume_content[:6000],
            "cover_letter_items": json.dumps(answer_units, ensure_ascii=False),
        })

        if isinstance(result, BaseModel):
            data = result.model_dump()
        elif isinstance(result, dict):
            data = result
        elif hasattr(result, "content"):
            try:
                data = json.loads(result.content)
            except (TypeError, json.JSONDecodeError):
                return {}
        else:
            return {}

        reviews = data.get("criteria", [])
        if not isinstance(reviews, list):
            return {}

        normalized: dict[str, dict] = {}
        for review in reviews:
            if not isinstance(review, dict):
                continue
            name = str(review.get("criterion_name") or "").strip()
            if not name:
                continue
            try:
                score = max(0, min(100, int(round(float(review.get("score", 0))))))
            except (TypeError, ValueError):
                continue
            normalized[name] = {
                "score": score,
                "feedback": str(review.get("feedback") or "").strip(),
                "evidence_summary": str(review.get("evidence_summary") or "").strip(),
                "is_keyword_stuffed": bool(review.get("is_keyword_stuffed")),
            }
        return normalized


def _run_llm_review(
    job_group: JobGroup,
    criteria_results: list[dict],
    resume_content: str,
    answer_units: list[dict[str, str]],
) -> dict[str, dict]:
    try:
        return CareerReadinessLLMReviewer().review(
            job_group=job_group,
            criteria_results=criteria_results,
            resume_content=resume_content,
            answer_units=answer_units,
        )
    except Exception:
        logger.warning("취업 준비도 LLM 검토 실패 - 룰 기반 점수로 계속 진행합니다.", exc_info=True)
        return {}


def _apply_llm_review(criteria_results: list[dict], llm_reviews: dict[str, dict]) -> list[dict]:
    if not llm_reviews:
        return criteria_results

    adjusted_results = []
    for item in criteria_results:
        review = llm_reviews.get(item["criterion_name"])
        if not review:
            adjusted_results.append(item)
            continue

        rule_score = int(item["score"])
        llm_raw_score = int(review["score"])
        llm_score_cap = int(item.get("criterion_cap", 100))
        llm_score = min(llm_raw_score, llm_score_cap)
        adjusted_score = round(rule_score * 0.2 + llm_score * 0.8)
        if review.get("is_keyword_stuffed"):
            adjusted_score = max(0, adjusted_score - 8)
        adjusted_score = min(adjusted_score, llm_score_cap)

        updated = {
            **item,
            "score": max(0, min(100, adjusted_score)),
            "llm_score": llm_score,
            "llm_raw_score": llm_raw_score,
            "llm_score_cap": llm_score_cap,
            "llm_feedback": review.get("feedback", ""),
            "llm_evidence_summary": review.get("evidence_summary", ""),
            "llm_keyword_stuffed": bool(review.get("is_keyword_stuffed")),
            "llm_reviewed": True,
        }
        if updated["llm_feedback"]:
            updated["feedback"] += f" AI 검토: {updated['llm_feedback']}"
        if updated["llm_keyword_stuffed"]:
            updated["feedback"] += " AI 검토에서도 키워드 나열 가능성이 확인되었습니다."
        adjusted_results.append(updated)

    return adjusted_results


def _score_label(score: int) -> str:
    if score >= 80:
        return "준비 상태가 좋은 편입니다."
    if score >= 60:
        return "기본 준비는 되어 있으나 보완이 필요합니다."
    if score >= 40:
        return "주요 준비 항목이 부족합니다."
    return "기초 자료부터 정리가 필요합니다."


def _build_action_plan(
    db: Session,
    job_group_id: int,
    sorted_results: list[dict],
) -> list[dict]:
    criterion_ids = [item["criterion_id"] for item in sorted_results[:3]]
    actions = (
        db.query(ActionTemplate)
        .filter(
            ActionTemplate.job_group_id == job_group_id,
            ActionTemplate.criterion_id.in_(criterion_ids),
        )
        .order_by(ActionTemplate.sort_order, ActionTemplate.id)
        .all()
    )
    action_by_criterion = {action.criterion_id: action for action in actions}

    plan = []
    for item in sorted_results[:3]:
        action = action_by_criterion.get(item["criterion_id"])
        if action:
            plan.append({"title": action.action_title, "detail": action.action_detail})
    return plan


def create_diagnosis(
    db: Session,
    user_id: int,
    *,
    cover_letter_id: int | None = None,
) -> dict:
    status = resume_service.get_resume_status(db, user_id)
    if not status["ready_for_career_diagnosis"]:
        raise CareerDiagnosisPrerequisiteError("자소서와 이력서를 등록 후 이용하시기 바랍니다.")

    resume = resume_service.get_resume(db, user_id)
    user = db.get(User, user_id)
    if cover_letter_id is None:
        cover_letter = cover_letter_service.get_latest_cover_letter(db, user_id)
    else:
        cover_letter = cover_letter_service.get_cover_letter(db, user_id, cover_letter_id)
        if not cover_letter:
            raise CareerDiagnosisPrerequisiteError("선택한 자소서를 찾을 수 없습니다.")

    if not cover_letter:
        raise CareerDiagnosisPrerequisiteError("자소서와 이력서를 등록 후 이용하시기 바랍니다.")

    cover_letter_text = cover_letter_service.to_analysis_text(cover_letter)
    answer_units = cover_letter_service.split_cover_letter_pairs(cover_letter)
    structured = _structured_to_dict(resume.structured)
    desired_job = user.desired_job if user and user.desired_job else ""
    content = f"{resume.content}\n{cover_letter_text}"
    corpus = f"{desired_job} {content} {_flatten(structured)}"

    groups, criteria_by_group = _load_active_groups_with_criteria(db)
    if cover_letter.job_group and cover_letter.job_group.is_active:
        job_group = cover_letter.job_group
    else:
        job_group = _choose_job_group(groups, criteria_by_group, desired_job, corpus)
        if not job_group:
            raise CareerDiagnosisConfigError("입력 자료에서 직무군을 판단할 수 없습니다. 자소서 직무군을 확인해주세요.")

    quality_reasons = _assess_input_quality(resume.content or "", answer_units)
    if quality_reasons:
        payload = _build_unavailable_payload(
            job_group=job_group,
            cover_letter=cover_letter,
            desired_job=desired_job,
            reasons=quality_reasons,
        )
        result = CareerDiagnosisResult(
            user_id=user_id,
            resume_id=resume.id,
            job_group_id=job_group.id,
            desired_job=desired_job,
            total_score=payload["total_score"],
            result_json=payload,
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return {"diagnosis_id": result.id, **payload}

    criteria = criteria_by_group.get(job_group.id, [])
    if not criteria:
        raise CareerDiagnosisConfigError("선택된 직무군의 진단 기준이 없습니다.")

    criteria_results = [
        _score_criterion(criterion, structured, content, answer_units)
        for criterion in criteria
    ]
    llm_reviews = _run_llm_review(job_group, criteria_results, resume.content or "", answer_units)
    criteria_results = _apply_llm_review(criteria_results, llm_reviews)
    job_fit = _assess_job_group_fit(job_group, groups, criteria_by_group, content)
    criteria_results = _apply_job_fit_cap(criteria_results, job_fit)
    total_weight = sum(item["weight"] for item in criteria_results) or 100
    total_score = round(
        sum(item["score"] * item["weight"] for item in criteria_results) / total_weight
    )

    sorted_results = sorted(criteria_results, key=lambda item: item["score"])
    strengths = [
        item["criterion_name"]
        for item in sorted(criteria_results, key=lambda item: item["score"], reverse=True)
        if item["score"] >= 65
    ][:3]
    strength_names = set(strengths)
    weaknesses = [
        item["criterion_name"]
        for item in sorted_results
        if item["criterion_name"] not in strength_names and item["score"] < 65
    ][:3]
    action_plan = _build_action_plan(db, job_group.id, sorted_results)

    target = desired_job or job_group.name
    strength_sentence = (
        f"{', '.join(strengths)}은 강점으로 보입니다."
        if strengths
        else "아직 뚜렷한 강점은 부족합니다."
    )
    weakness_sentence = (
        f"{', '.join(weaknesses)}은 우선 보완할 항목입니다."
        if weaknesses
        else "뚜렷한 약점은 적지만, 선택한 직무에 맞춘 사례 근거를 계속 보완해보세요."
    )
    summary = (
        f"{target} 기준 종합 취업 준비도는 {total_score}점입니다. "
        f"{_score_label(total_score)} "
        f"{strength_sentence} "
        f"{weakness_sentence}"
    )

    payload = {
        "job_group": {
            "id": job_group.id,
            "name": job_group.name,
            "description": job_group.description,
        },
        "source_cover_letter": {
            "id": cover_letter.id,
            "title": cover_letter.title,
            "company_name": cover_letter.company_name,
            "job_group_id": cover_letter.job_group_id,
        },
        "desired_job": desired_job,
        "total_score": total_score,
        "score_label": _score_label(total_score),
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "criteria_results": criteria_results,
        "action_plan": action_plan,
        "job_fit": job_fit,
        "evaluation_available": True,
        "unavailable_reasons": [],
        "llm_reviewed": bool(llm_reviews),
        "caution": "이 점수는 합격 가능성이 아니라, 입력된 자료 기준으로 희망 직무 대비 준비 자료와 경험 근거가 얼마나 정리되어 있는지를 나타냅니다.",
    }

    result = CareerDiagnosisResult(
        user_id=user_id,
        resume_id=resume.id,
        job_group_id=job_group.id,
        desired_job=desired_job,
        total_score=total_score,
        result_json=payload,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return {"diagnosis_id": result.id, **payload}

