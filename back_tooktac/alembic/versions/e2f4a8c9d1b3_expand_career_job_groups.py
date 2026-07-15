"""expand career job group master data

Revision ID: e2f4a8c9d1b3
Revises: c9d4e2f8a6b1
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import json


revision: str = "e2f4a8c9d1b3"
down_revision: Union[str, Sequence[str], None] = "c9d4e2f8a6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_GROUPS = ("개발/IT", "마케팅/기획", "사무/행정")


JOB_GROUPS = [
    {
        "name": "백엔드 개발",
        "description": "서버, API, 데이터베이스, 배포를 중심으로 하는 개발 직무",
        "criteria": [
            ("서버/API 구현", "서버와 API 기능을 직접 설계·구현한 경험을 평가합니다.", ["api", "rest", "fastapi", "spring", "controller", "endpoint", "서버", "백엔드", "인증", "인가"], 25, 1, "대표 API를 구체화하세요", "대표 API 3개를 목적, 요청/응답, 예외 처리, 본인 역할, 결과 기준으로 정리하세요."),
            ("DB 설계/활용", "DB 모델링, SQL, 트랜잭션, 성능 고려 경험을 평가합니다.", ["mysql", "postgresql", "sql", "erd", "index", "transaction", "정규화", "쿼리", "db", "database"], 20, 2, "DB 설계 근거를 정리하세요", "ERD, 주요 테이블, 관계, 인덱스나 트랜잭션을 고려한 이유를 작성하세요."),
            ("문제 해결/성능 개선", "오류 분석, 트러블슈팅, 구조 개선, 성능 개선 경험을 평가합니다.", ["오류", "에러", "트러블슈팅", "리팩토링", "최적화", "성능", "로그", "디버깅", "개선"], 20, 3, "트러블슈팅 사례를 보강하세요", "문제 상황, 원인 분석, 시도한 방법, 최종 해결, 수치 결과를 한 사례로 정리하세요."),
            ("배포/운영 이해", "서비스 배포, 서버 운영, 클라우드와 컨테이너 사용 경험을 평가합니다.", ["aws", "ec2", "docker", "nginx", "linux", "배포", "운영", "ci/cd", "github actions"], 20, 4, "배포 흐름을 설명하세요", "배포 환경, 사용 도구, 배포 절차, 장애 대응이나 운영 경험을 단계별로 정리하세요."),
            ("협업/문서화", "GitHub, README, API 명세, 협업 기록 등 개발 결과물 정리 수준을 평가합니다.", ["github", "readme", "api 명세", "swagger", "notion", "문서화", "협업", "코드리뷰", "wiki"], 15, 5, "개발 문서를 보완하세요", "README, API 명세, 실행 방법, 협업 방식, 코드 리뷰 경험을 포트폴리오에 연결하세요."),
        ],
    },
    {
        "name": "프론트엔드 개발",
        "description": "웹 UI 구현, 상태 관리, API 연동, 사용자 경험 개선 직무",
        "criteria": [
            ("UI 구현 능력", "화면 구조, 컴포넌트, 반응형 UI 구현 경험을 평가합니다.", ["react", "next", "vue", "typescript", "component", "반응형", "ui", "css", "tailwind"], 25, 1, "대표 화면 구현 사례를 정리하세요", "구현한 화면의 목적, 컴포넌트 구조, 반응형 처리, 본인 역할을 정리하세요."),
            ("상태관리/프론트 구조", "상태 관리, 라우팅, 컴포넌트 분리 등 프론트 구조화 경험을 평가합니다.", ["state", "zustand", "redux", "context", "routing", "hook", "상태관리", "컴포넌트", "구조"], 20, 2, "상태 관리 선택 이유를 쓰세요", "어떤 상태를 어디에 두었고 왜 그렇게 설계했는지 사례 중심으로 작성하세요."),
            ("API 연동/비동기 처리", "백엔드 API 연동, 에러 처리, 로딩 상태 처리 경험을 평가합니다.", ["api", "axios", "fetch", "비동기", "로딩", "에러 처리", "mutation", "query", "통신"], 20, 3, "API 연동 흐름을 구체화하세요", "요청/응답, 로딩, 에러, 인증 처리 경험을 한 기능 기준으로 정리하세요."),
            ("UX/성능 개선", "사용성 개선, 접근성, 렌더링 성능 개선 경험을 평가합니다.", ["ux", "사용성", "성능", "최적화", "accessibility", "접근성", "lighthouse", "렌더링", "개선"], 20, 4, "UX 개선 전후를 비교하세요", "불편했던 지점, 개선 방법, 사용자 관점의 결과를 전후 비교로 작성하세요."),
            ("배포/협업", "프론트 배포, Git 협업, 디자인 협업 경험을 평가합니다.", ["vercel", "netlify", "배포", "github", "figma", "협업", "디자인", "pr", "코드리뷰"], 15, 5, "협업 산출물을 정리하세요", "Figma 협업, PR, 배포 링크, 화면 캡처, README를 함께 정리하세요."),
        ],
    },
    {
        "name": "데이터/AI",
        "description": "데이터 처리, 분석, 머신러닝·AI 모델 활용 직무",
        "criteria": [
            ("데이터 처리/정제", "데이터 수집, 정제, 전처리 경험을 평가합니다.", ["python", "pandas", "numpy", "전처리", "정제", "수집", "크롤링", "etl", "데이터"], 25, 1, "데이터 처리 과정을 정리하세요", "데이터 출처, 정제 규칙, 결측치/이상치 처리, 최종 데이터 형태를 작성하세요."),
            ("분석/모델링 경험", "분석 모델, 머신러닝, AI 모델 활용 경험을 평가합니다.", ["모델", "머신러닝", "딥러닝", "sklearn", "pytorch", "tensorflow", "llm", "분류", "예측"], 25, 2, "모델 선택 근거를 쓰세요", "사용한 모델, 선택 이유, 입력/출력, 비교한 대안과 결과를 정리하세요."),
            ("SQL/데이터베이스", "SQL 쿼리, 데이터베이스 활용, 데이터 추출 역량을 평가합니다.", ["sql", "mysql", "postgresql", "join", "group by", "쿼리", "db", "데이터베이스"], 15, 3, "SQL 활용 사례를 추가하세요", "작성한 쿼리 목적, 조인/집계 방식, 결과 활용 방법을 작성하세요."),
            ("실험/평가 지표", "모델 또는 분석 결과를 지표로 평가한 경험을 평가합니다.", ["accuracy", "precision", "recall", "f1", "auc", "rmse", "평가", "검증", "실험", "지표"], 20, 4, "평가 지표를 명확히 하세요", "왜 그 지표를 썼고, 결과가 어떤 의미였는지 업무 관점으로 해석하세요."),
            ("결과 해석/전달", "분석 결과를 시각화하거나 의사결정에 연결한 경험을 평가합니다.", ["시각화", "dashboard", "tableau", "matplotlib", "보고서", "인사이트", "해석", "발표"], 15, 5, "분석 결과의 의미를 정리하세요", "결과 수치뿐 아니라 어떤 의사결정이나 개선으로 이어졌는지 작성하세요."),
        ],
    },
    {
        "name": "서비스기획/PM",
        "description": "문제 정의, 요구사항, 정책, UX, 일정 조율을 담당하는 기획 직무",
        "criteria": [
            ("문제 정의/가설", "사용자 문제와 서비스 가설을 정의한 경험을 평가합니다.", ["문제 정의", "가설", "pain point", "니즈", "사용자", "고객", "문제", "목표"], 25, 1, "문제 정의를 한 문장으로 쓰세요", "누구의 어떤 문제를 왜 해결하려 했는지 사용자와 근거를 함께 정리하세요."),
            ("요구사항/정책 정리", "요구사항, 기능 명세, 정책 문서 작성 경험을 평가합니다.", ["요구사항", "기능 명세", "정책", "유저스토리", "prd", "기획서", "명세", "범위"], 25, 2, "요구사항 문서를 보완하세요", "핵심 기능, 예외 정책, 우선순위, 수용 기준을 표 형태로 정리하세요."),
            ("UX/화면 설계", "사용자 흐름, 와이어프레임, 화면 설계 경험을 평가합니다.", ["ux", "flow", "wireframe", "figma", "화면설계", "사용자 흐름", "프로토타입"], 20, 3, "사용자 흐름을 그리세요", "주요 사용자 행동 흐름과 각 화면의 목적을 간단한 플로우로 정리하세요."),
            ("지표/데이터 활용", "서비스 지표를 정의하고 분석한 경험을 평가합니다.", ["kpi", "지표", "전환율", "retention", "활성", "데이터", "분석", "퍼널"], 15, 4, "핵심 지표를 정의하세요", "기획의 성공을 판단할 지표와 측정 방법을 작성하세요."),
            ("협업/일정 관리", "개발·디자인과 협업하고 일정과 범위를 조율한 경험을 평가합니다.", ["협업", "일정", "조율", "스프린트", "jira", "notion", "회의", "우선순위"], 15, 5, "협업 조율 사례를 정리하세요", "이견이 있었던 상황, 조율 기준, 결정 과정, 결과를 작성하세요."),
        ],
    },
    {
        "name": "마케팅",
        "description": "콘텐츠, 캠페인, 채널 운영, 성과 분석 중심의 마케팅 직무",
        "criteria": [
            ("캠페인/콘텐츠 실행", "콘텐츠 제작, 캠페인 운영 경험을 평가합니다.", ["콘텐츠", "캠페인", "sns", "카드뉴스", "블로그", "인스타그램", "영상", "광고"], 25, 1, "대표 캠페인을 구조화하세요", "목표, 타깃, 채널, 메시지, 실행 과정, 결과를 정리하세요."),
            ("고객/시장 이해", "고객, 타깃, 시장, 경쟁사 분석 경험을 평가합니다.", ["고객", "타깃", "시장조사", "경쟁사", "페르소나", "니즈", "세그먼트"], 20, 2, "타깃 분석 근거를 보완하세요", "타깃을 어떻게 정의했고 어떤 근거로 메시지를 설계했는지 작성하세요."),
            ("성과 지표/분석", "마케팅 성과를 수치로 분석한 경험을 평가합니다.", ["조회수", "클릭률", "전환율", "roas", "cpc", "ctr", "참여율", "팔로워", "증가"], 25, 3, "성과 지표를 수치로 정리하세요", "노출, 클릭, 전환, 참여율 등 캠페인 결과를 수치와 해석으로 작성하세요."),
            ("채널/툴 활용", "GA4, 광고관리자, SNS, CRM 등 마케팅 도구 활용 경험을 평가합니다.", ["ga4", "광고관리자", "meta", "google ads", "crm", "notion", "excel", "엑셀"], 15, 4, "마케팅 도구 활용 목적을 쓰세요", "사용한 도구와 그 도구로 확인하거나 개선한 항목을 구체화하세요."),
            ("개선/실험 경험", "A/B 테스트, 메시지 개선, 소재 개선 경험을 평가합니다.", ["a/b", "테스트", "개선", "실험", "소재", "카피", "랜딩", "최적화"], 15, 5, "개선 전후를 비교하세요", "어떤 가설로 무엇을 바꿨고 지표가 어떻게 달라졌는지 정리하세요."),
        ],
    },
    {
        "name": "인사/총무",
        "description": "채용, 온보딩, 조직 운영, 총무 지원 직무",
        "criteria": [
            ("채용/온보딩 지원", "채용 일정, 지원자 관리, 온보딩 지원 경험을 평가합니다.", ["채용", "면접", "지원자", "온보딩", "교육", "입사", "공고", "일정"], 25, 1, "채용 지원 경험을 정리하세요", "채용 단계, 담당 업무, 일정 관리, 지원자 커뮤니케이션 경험을 작성하세요."),
            ("조직 운영/총무", "비품, 자산, 행사, 사내 운영 지원 경험을 평가합니다.", ["총무", "비품", "자산", "행사", "운영", "관리", "복리후생", "사내"], 20, 2, "운영 지원 사례를 구체화하세요", "운영한 업무의 목적, 처리 절차, 협업 부서, 결과를 작성하세요."),
            ("문서/규정 관리", "문서 작성, 규정 정리, 계약/증빙 관리 경험을 평가합니다.", ["문서", "규정", "계약", "증빙", "보고서", "정리", "작성", "관리"], 20, 3, "문서 관리 방식을 쓰세요", "어떤 문서를 어떤 기준으로 정리했고 누락을 어떻게 방지했는지 작성하세요."),
            ("커뮤니케이션", "구성원, 지원자, 외부 업체와 소통한 경험을 평가합니다.", ["소통", "안내", "응대", "조율", "협업", "전달", "커뮤니케이션"], 20, 4, "소통 사례를 정리하세요", "상대방, 요청 사항, 조율 과정, 결과를 상황 중심으로 작성하세요."),
            ("정확성/보안 의식", "개인정보, 인사 자료, 비용 자료를 정확히 관리한 경험을 평가합니다.", ["개인정보", "보안", "정확성", "검토", "확인", "누락", "오류"], 15, 5, "정확성 관리 경험을 보완하세요", "민감 자료나 반복 업무에서 실수를 줄인 방법을 작성하세요."),
        ],
    },
    {
        "name": "회계/재무",
        "description": "회계 처리, 정산, 전표, 재무 자료 관리 직무",
        "criteria": [
            ("회계 기초/전표", "회계 원리, 전표, 계정과목 이해와 처리 경험을 평가합니다.", ["회계", "전표", "계정", "분개", "세금계산서", "부가세", "원장"], 25, 1, "회계 처리 경험을 구체화하세요", "처리한 전표나 증빙 유형, 확인 기준, 사용 시스템을 정리하세요."),
            ("정산/마감 경험", "정산, 월마감, 비용 처리 경험을 평가합니다.", ["정산", "마감", "비용", "매입", "매출", "증빙", "지급", "청구"], 25, 2, "정산 절차를 단계별로 쓰세요", "자료 수집, 검토, 입력, 확인, 보고까지 본인이 맡은 단계를 작성하세요."),
            ("Excel/시스템 활용", "Excel과 회계 시스템 활용 역량을 평가합니다.", ["excel", "엑셀", "함수", "피벗", "더존", "erp", "회계시스템", "데이터"], 20, 3, "Excel 활용 사례를 보완하세요", "사용한 함수, 검증 방식, 업무 효율 개선 사례를 구체화하세요."),
            ("정확성/검토", "숫자 검증, 오류 확인, 자료 대조 경험을 평가합니다.", ["검토", "대조", "확인", "오류", "정확성", "누락", "잔액", "차이"], 20, 4, "오류 방지 방법을 쓰세요", "자료를 대조하거나 검토해 오류를 발견·수정한 사례를 작성하세요."),
            ("보고/분석", "재무 자료 보고, 비용 분석, 수치 해석 경험을 평가합니다.", ["보고", "분석", "비용", "예산", "손익", "추이", "자료", "수치"], 10, 5, "숫자 해석 경험을 정리하세요", "단순 입력을 넘어 수치를 비교하거나 보고한 경험을 작성하세요."),
        ],
    },
    {
        "name": "사무행정",
        "description": "문서 작성, OA, 일정 관리, 행정 지원 직무",
        "criteria": [
            ("문서 작성 능력", "회의록, 보고서, 공문 등 문서 작성 경험을 평가합니다.", ["회의록", "보고서", "문서", "공문", "작성", "정리", "양식"], 25, 1, "문서 작성 사례를 정리하세요", "작성한 문서 유형, 목적, 독자, 결과를 구체적으로 작성하세요."),
            ("OA/Excel 활용", "Excel, Word, PPT 등 OA 도구 활용 경험을 평가합니다.", ["excel", "엑셀", "word", "ppt", "함수", "피벗", "표", "데이터"], 25, 2, "OA 활용 경험을 구체화하세요", "사용한 기능과 그 기능으로 처리한 업무를 함께 작성하세요."),
            ("일정/업무 관리", "일정 조율, 체크리스트, 마감 관리 경험을 평가합니다.", ["일정", "체크리스트", "마감", "업무", "관리", "조율", "예약"], 20, 3, "업무 관리 방식을 쓰세요", "마감과 우선순위를 어떻게 관리했는지 사례로 작성하세요."),
            ("커뮤니케이션", "부서, 고객, 동료와의 전달·응대 경험을 평가합니다.", ["응대", "전달", "소통", "협업", "조율", "안내", "커뮤니케이션"], 15, 4, "응대/전달 경험을 정리하세요", "누구에게 무엇을 전달했고 어떻게 오해를 줄였는지 작성하세요."),
            ("정확성/꼼꼼함", "자료 검토, 누락 방지, 반복 업무 처리 정확성을 평가합니다.", ["검토", "확인", "정확성", "꼼꼼", "누락", "오류", "대조"], 15, 5, "검토 루틴을 작성하세요", "반복 업무에서 실수를 줄이기 위해 사용한 체크 방식과 결과를 정리하세요."),
        ],
    },
    {
        "name": "영업/영업지원",
        "description": "고객 발굴, 제안, 상담, 영업 자료와 실적 관리 직무",
        "criteria": [
            ("고객 발굴/응대", "잠재 고객 발굴, 고객 응대 경험을 평가합니다.", ["고객", "영업", "발굴", "응대", "상담", "리드", "콜", "방문"], 25, 1, "고객 응대 사례를 정리하세요", "고객 유형, 니즈 파악, 응대 방식, 결과를 작성하세요."),
            ("제안/상담 역량", "상품·서비스 제안, 상담, 설득 경험을 평가합니다.", ["제안", "상담", "설득", "니즈", "견적", "계약", "상품", "서비스"], 25, 2, "제안 과정을 구체화하세요", "고객 니즈와 제안 내용, 반응, 후속 조치를 정리하세요."),
            ("CRM/자료 관리", "고객 정보, 견적서, 영업 자료 관리 경험을 평가합니다.", ["crm", "고객관리", "견적서", "자료", "excel", "엑셀", "리스트", "관리"], 15, 3, "고객 자료 관리 방식을 쓰세요", "고객 정보나 견적 자료를 어떤 기준으로 관리했는지 작성하세요."),
            ("실적/목표 관리", "목표, 실적, 전환율 등 수치 관리 경험을 평가합니다.", ["실적", "목표", "매출", "전환율", "달성", "계약", "%", "증가"], 20, 4, "성과 지표를 수치로 정리하세요", "목표 대비 결과, 달성률, 매출 또는 계약 성과를 작성하세요."),
            ("커뮤니케이션/협업", "내부 부서와 협업하고 고객 요청을 조율한 경험을 평가합니다.", ["협업", "조율", "소통", "전달", "요청", "이슈", "커뮤니케이션"], 15, 5, "협업 조율 사례를 쓰세요", "고객 요청을 내부와 어떻게 조율했고 결과가 어땠는지 작성하세요."),
        ],
    },
    {
        "name": "고객상담/CS",
        "description": "고객 문의 응대, 문제 해결, 서비스 운영 지원 직무",
        "criteria": [
            ("고객 응대 경험", "문의, 불만, 요청을 응대한 경험을 평가합니다.", ["고객", "문의", "응대", "상담", "cs", "콜", "채팅", "안내"], 25, 1, "고객 응대 사례를 정리하세요", "문의 유형, 응대 방식, 고객 반응, 후속 조치를 작성하세요."),
            ("문제 해결", "고객 문제 원인 파악과 해결 경험을 평가합니다.", ["문제", "불만", "이슈", "해결", "원인", "처리", "개선", "클레임"], 25, 2, "문제 해결 과정을 쓰세요", "고객 문제, 확인한 원인, 조치, 재발 방지 방법을 정리하세요."),
            ("서비스 이해", "상품·서비스 정책과 기능을 이해하고 안내한 경험을 평가합니다.", ["서비스", "정책", "기능", "상품", "매뉴얼", "가이드", "안내", "faq"], 20, 3, "서비스 이해 근거를 보완하세요", "어떤 정책이나 기능을 이해하고 고객에게 어떻게 설명했는지 작성하세요."),
            ("감정 관리/태도", "감정 노동 상황에서 침착하게 대응한 경험을 평가합니다.", ["감정", "침착", "공감", "경청", "불만", "갈등", "태도", "응대"], 15, 4, "어려운 응대 경험을 정리하세요", "까다로운 상황에서 어떤 태도로 대응했고 결과가 어땠는지 작성하세요."),
            ("기록/전달", "상담 기록, 이슈 전달, 후속 관리 경험을 평가합니다.", ["기록", "전달", "이관", "보고", "crm", "히스토리", "후속", "관리"], 15, 5, "상담 기록 방식을 쓰세요", "상담 내용을 어떻게 기록하고 담당자에게 전달했는지 작성하세요."),
        ],
    },
    {
        "name": "디자인",
        "description": "UI/UX, 그래픽, 브랜딩, 콘텐츠 디자인 직무",
        "criteria": [
            ("디자인 툴 활용", "Figma, Photoshop, Illustrator 등 디자인 툴 활용 경험을 평가합니다.", ["figma", "photoshop", "illustrator", "xd", "툴", "시안", "프로토타입"], 25, 1, "툴 활용 결과물을 정리하세요", "사용한 툴, 만든 결과물, 본인 작업 범위를 포트폴리오에 연결하세요."),
            ("포트폴리오/결과물", "완성도 있는 디자인 결과물과 설명 자료를 평가합니다.", ["포트폴리오", "결과물", "시안", "작업물", "케이스스터디", "브랜딩", "ui"], 25, 2, "작업물 설명을 보완하세요", "문제, 목표, 디자인 의도, 최종 결과를 각 작업물에 추가하세요."),
            ("UX/사용자 이해", "사용자 흐름, UX 개선, 사용성 고려 경험을 평가합니다.", ["ux", "사용자", "사용성", "flow", "와이어프레임", "리서치", "개선"], 20, 3, "사용자 관점을 설명하세요", "디자인 결정이 어떤 사용자 문제를 해결했는지 작성하세요."),
            ("브랜딩/시각 표현", "브랜드 톤, 레이아웃, 색상, 타이포그래피 활용 역량을 평가합니다.", ["브랜딩", "로고", "컬러", "타이포", "레이아웃", "그래픽", "비주얼"], 15, 4, "시각적 의도를 정리하세요", "색상, 레이아웃, 타이포그래피 선택 이유를 작업물별로 작성하세요."),
            ("협업/피드백 반영", "기획·개발과 협업하고 피드백을 반영한 경험을 평가합니다.", ["협업", "피드백", "수정", "개발", "기획", "커뮤니케이션", "handoff"], 15, 5, "피드백 반영 사례를 쓰세요", "받은 피드백, 수정 방향, 최종 개선 결과를 정리하세요."),
        ],
    },
    {
        "name": "생산/물류",
        "description": "생산관리, 품질관리, 구매·자재, 물류관리 직무",
        "criteria": [
            ("공정/생산 이해", "생산 흐름, 공정, 현장 운영 이해를 평가합니다.", ["생산", "공정", "라인", "작업", "현장", "제조", "설비", "생산관리"], 25, 1, "공정 이해 경험을 정리하세요", "어떤 공정이나 생산 흐름을 이해했고 어떤 역할을 했는지 작성하세요."),
            ("품질/안전 관리", "품질 확인, 불량 대응, 안전 준수 경험을 평가합니다.", ["품질", "불량", "검사", "안전", "표준", "점검", "개선", "관리"], 25, 2, "품질/안전 사례를 구체화하세요", "불량이나 안전 이슈를 어떻게 확인하고 조치했는지 작성하세요."),
            ("재고/물류 관리", "입출고, 재고, 배송, 창고 관리 경험을 평가합니다.", ["재고", "입고", "출고", "물류", "배송", "창고", "자재", "wms"], 20, 3, "재고 관리 경험을 쓰세요", "입출고, 재고 확인, 오류 방지 방법을 단계별로 작성하세요."),
            ("데이터/Excel 활용", "생산·물류 데이터를 정리하고 분석한 경험을 평가합니다.", ["excel", "엑셀", "데이터", "표", "집계", "분석", "보고서", "함수"], 15, 4, "현장 데이터를 정리하세요", "수량, 불량, 입출고 등 데이터를 어떻게 기록·분석했는지 작성하세요."),
            ("개선/협업 경험", "현장 문제 개선, 부서 협업, 일정 조율 경험을 평가합니다.", ["개선", "협업", "조율", "일정", "문제", "효율", "커뮤니케이션", "납기"], 15, 5, "개선 사례를 정리하세요", "현장에서 발견한 문제와 개선 행동, 결과를 구체적으로 작성하세요."),
        ],
    },
]


NEW_GROUP_NAMES = tuple(group["name"] for group in JOB_GROUPS)


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _scalar(sql: str, params: dict | None = None):
    return op.get_bind().execute(sa.text(sql), params or {}).scalar()


def _ensure_job_group(name: str, description: str) -> int:
    group_id = _scalar("SELECT id FROM job_group WHERE name = :name", {"name": name})
    if group_id:
        op.get_bind().execute(
            sa.text("UPDATE job_group SET description = :description, is_active = 1 WHERE id = :id"),
            {"id": group_id, "description": description},
        )
        return int(group_id)

    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO job_group (name, description, is_active)
            VALUES (:name, :description, 1)
            """
        ),
        {"name": name, "description": description},
    )
    return int(_scalar("SELECT id FROM job_group WHERE name = :name", {"name": name}))


def _ensure_criterion(
    job_group_id: int,
    name: str,
    description: str,
    keywords: list[str],
    weight: int,
    sort_order: int,
) -> int:
    criterion_id = _scalar(
        """
        SELECT id FROM job_readiness_criteria
        WHERE job_group_id = :job_group_id AND criterion_name = :name
        """,
        {"job_group_id": job_group_id, "name": name},
    )
    params = {
        "job_group_id": job_group_id,
        "name": name,
        "description": description,
        "keywords": json.dumps(keywords, ensure_ascii=False),
        "weight": weight,
        "sort_order": sort_order,
    }
    if criterion_id:
        op.get_bind().execute(
            sa.text(
                """
                UPDATE job_readiness_criteria
                SET description = :description,
                    keywords = :keywords,
                    weight = :weight,
                    sort_order = :sort_order
                WHERE id = :id
                """
            ),
            {"id": criterion_id, **params},
        )
        return int(criterion_id)

    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO job_readiness_criteria
                (job_group_id, criterion_name, description, keywords, weight, sort_order)
            VALUES
                (:job_group_id, :name, :description, :keywords, :weight, :sort_order)
            """
        ),
        params,
    )
    return int(
        _scalar(
            """
            SELECT id FROM job_readiness_criteria
            WHERE job_group_id = :job_group_id AND criterion_name = :name
            """,
            {"job_group_id": job_group_id, "name": name},
        )
    )


def _ensure_action_template(
    job_group_id: int,
    criterion_id: int,
    title: str,
    detail: str,
    sort_order: int,
) -> None:
    action_id = _scalar(
        """
        SELECT id FROM action_template
        WHERE job_group_id = :job_group_id
          AND criterion_id = :criterion_id
          AND action_title = :title
        """,
        {"job_group_id": job_group_id, "criterion_id": criterion_id, "title": title},
    )
    if action_id:
        op.get_bind().execute(
            sa.text(
                """
                UPDATE action_template
                SET action_detail = :detail, sort_order = :sort_order
                WHERE id = :id
                """
            ),
            {"id": action_id, "detail": detail, "sort_order": sort_order},
        )
        return

    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO action_template
                (job_group_id, criterion_id, action_title, action_detail, sort_order)
            VALUES
                (:job_group_id, :criterion_id, :title, :detail, :sort_order)
            """
        ),
        {
            "job_group_id": job_group_id,
            "criterion_id": criterion_id,
            "title": title,
            "detail": detail,
            "sort_order": sort_order,
        },
    )


def upgrade() -> None:
    required_tables = ("job_group", "job_readiness_criteria", "action_template")
    if not all(_has_table(table_name) for table_name in required_tables):
        return

    op.get_bind().execute(
        sa.text("UPDATE job_group SET is_active = 0 WHERE name IN :names").bindparams(
            sa.bindparam("names", expanding=True)
        ),
        {"names": LEGACY_GROUPS},
    )

    action_sort_order = 1
    for group in JOB_GROUPS:
        group_id = _ensure_job_group(group["name"], group["description"])
        for criterion in group["criteria"]:
            (
                criterion_name,
                description,
                keywords,
                weight,
                sort_order,
                action_title,
                action_detail,
            ) = criterion
            criterion_id = _ensure_criterion(
                group_id,
                criterion_name,
                description,
                keywords,
                weight,
                sort_order,
            )
            _ensure_action_template(
                group_id,
                criterion_id,
                action_title,
                action_detail,
                action_sort_order,
            )
            action_sort_order += 1


def downgrade() -> None:
    if not _has_table("job_group"):
        return
    op.get_bind().execute(
        sa.text("UPDATE job_group SET is_active = 0 WHERE name IN :names").bindparams(
            sa.bindparam("names", expanding=True)
        ),
        {"names": NEW_GROUP_NAMES},
    )
    op.get_bind().execute(
        sa.text("UPDATE job_group SET is_active = 1 WHERE name IN :names").bindparams(
            sa.bindparam("names", expanding=True)
        ),
        {"names": LEGACY_GROUPS},
    )
