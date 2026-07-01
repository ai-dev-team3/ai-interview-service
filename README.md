# AI Interview Service

> AI 기반 면접 훈련 플랫폼

이 프로젝트는 백엔드와 프론트엔드가 분리된 AI 면접 훈련 서비스입니다. 사용자는 면접 연습을 진행하고, AI가 음성·표정·자세·답변 내용을 분석해 피드백과 결과 리포트를 받을 수 있습니다.

## 프로젝트 개요

- 백엔드: FastAPI 기반 API 서버
- 프론트엔드: Next.js 기반 웹 애플리케이션
- 주요 기능: 면접 질문 생성, 답변 기록, 음성/표정/자세 분석, 결과 리포트 제공
- 구성: `back_tooktac`(백엔드), `front_tooktac`(프론트엔드)

## 폴더 구조

```text
ai-interview-service/
├── back_tooktac/      # FastAPI 백엔드
├── front_tooktac/     # Next.js 프론트엔드
└── README.md          # 통합 프로젝트 설명서
```

## 기술 스택

### 백엔드

- Python 3.11+
- FastAPI
- SQLAlchemy
- Pydantic
- JWT 인증
- OpenAI / Google AI / Vision 관련 API
- WebSocket

### 프론트엔드

- Next.js
- React
- Tailwind CSS
- Chart.js / Recharts

## 시작하기

### 1. 백엔드 실행

```bash
cd back_tooktac
uv sync
uv run python -c "from app.repository.database import Base, engine; import app.repository.model_registry; Base.metadata.create_all(engine)"
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 프론트엔드 실행

```bash
cd front_tooktac
npm install
npm run dev
```

브라우저에서 http://localhost:3000 을 열면 결과를 확인할 수 있습니다.

## 프론트엔드 관련 안내

이 프로젝트는 Next.js로 생성된 create-next-app 기반 프로젝트입니다.

### 개발 서버 실행

```bash
npm run dev
# 또는
yarn dev
# 또는
pnpm dev
# 또는
bun dev
```

페이지를 수정하려면 `front_tooktac/app` 폴더의 페이지 파일을 변경하면 됩니다. 파일을 수정하면 페이지가 자동으로 갱신됩니다.

이 프로젝트는 `next/font`를 사용하여 Vercel의 새 폰트 패밀리인 Geist를 자동으로 최적화하고 불러옵니다.

## 더 알아보기

Next.js에 대해 더 자세히 알고 싶다면 다음 자료를 참고하세요.

- Next.js 문서: https://nextjs.org/docs
- Learn Next.js: https://nextjs.org/learn
- Next.js GitHub 저장소: https://github.com/vercel/next.js

## 참고 문서

- 백엔드 README: `back_tooktac/README.md`
- 프론트엔드 README: `front_tooktac/README.md`
