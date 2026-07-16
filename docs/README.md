# tooktac — AI 면접 훈련 서비스

> AI가 답변·음성·표정·자세를 분석해 피드백과 리포트를 주는 면접 훈련 플랫폼

tooktac은 면접을 혼자 연습하기 어려운 취업준비생을 위한 서비스입니다. 사용자는 모의 면접을 진행하고, AI가 답변 내용은 물론 음성·표정·자세까지 분석해 개선 피드백과 결과 리포트를 제공합니다. 자기소개서 등록·첨삭부터 커리어 진단, 다른 사용자와의 랭킹 비교까지 면접 준비 전 과정을 하나의 흐름으로 지원합니다.

## 주요 기능

- **모의 면접 (Practice Interview)** — 세션 기반 면접 연습. 답변을 녹음/녹화하면 AI가 분석 후 결과를 돌려줍니다.
- **오늘의 면접 (Today's Interview)** — 아이스브레이킹 → 질문 답변 → 최종 평가 → 리포트로 이어지는 데일리 면접 루틴.
- **음성·표정·자세 분석** — 답변 음성을 STT(Vito/Clova)로 텍스트화하고, 표정·자세를 Vision으로 분석해 비언어 요소까지 평가합니다.
- **자기소개서 첨삭 (Cover Letter)** — 자소서 문항을 5개 유형(지원동기·직무적합성·도전및목표달성·창의성및문제해결·조직적합성과인성)으로 자동 분류(triage)한 뒤, 유형별 전문 에이전트가 첨삭합니다.
- **커리어 진단 (Career Diagnosis)** — 사용자 이력·자소서를 바탕으로 커리어 방향을 진단합니다.
- **결과 리포트 & 점수** — 면접별 점수·피드백을 종합한 리포트를 생성합니다.
- **랭킹 (Rank)** — 다른 사용자와 점수를 비교합니다.
- **마이페이지** — 계정 관리 및 훈련 이력(training history) 조회.
- **LLM 관측(Observability)** — 모든 LLM 호출을 self-host Langfuse로 전송해 대시보드에서 집계합니다.

## 기술 스택

### 백엔드 (`back_tooktac`)

- Python 3.11+ / FastAPI / WebSocket
- SQLAlchemy 2.x · PyMySQL (MySQL 8.x) · Alembic 마이그레이션
- Pydantic · pydantic-settings
- JWT 인증 (python-jose · bcrypt)
- LLM: LangChain / LangGraph 기반 멀티 에이전트 (OpenAI · Google Gemini)
- 외부 연동: STT(Vito · Clova), Google Document AI, ffmpeg(음성 변환)
- 관측: Langfuse v2

### 프론트엔드 (`front_tooktac`)

- Next.js · React · TypeScript
- Tailwind CSS
- Chart.js / Recharts

## 프로젝트 구조

```text
ai_interview/
├── back_tooktac/      # FastAPI 백엔드 (API · AI 분석 · 멀티 에이전트)
├── front_tooktac/     # Next.js 프론트엔드
└── docs/              # 프로젝트 문서
    ├── README.md          # 이 문서
    └── PORTING_MANUAL.md  # 설치 · 배포 · 포팅 가이드
```

## 시작하기

설치·실행·배포에 필요한 시스템 요구사항, 환경 변수, DB 초기화, 서버 실행 절차는 포팅 매뉴얼에 정리되어 있습니다.

👉 **[포팅 매뉴얼 (PORTING_MANUAL.md)](PORTING_MANUAL.md)**
