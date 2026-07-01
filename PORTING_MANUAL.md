# Porting Manual

## 1. 개요

이 문서는 AI Interview Service를 새 서버, 새 운영 환경, 또는 다른 배포 환경으로 이전할 때 참고할 수 있는 포팅 매뉴얼입니다.

현재 프로젝트는 다음 두 부분으로 구성됩니다.

- 백엔드: FastAPI 기반 API 서버
- 프론트엔드: Next.js 기반 웹 애플리케이션

이 서비스는 기본적으로 MySQL 데이터베이스를 사용합니다. 따라서 포팅 시에는 DB 서버 준비와 연결 정보 설정이 필수입니다.

기본적으로 다음 포트가 사용됩니다.

- 프론트엔드: 3000
- 백엔드: 8000
- 데이터베이스: MySQL (기본 포트 3306)

---

## 2. 사전 준비

### 2.1 서버 요구사항

- Python 3.11 이상
- Node.js 18 이상 권장
- MySQL 8.0 이상
- uv (Python 패키지 관리)
- npm 또는 yarn

### 2.2 저장소 준비

```bash
git clone <repository-url>
cd ai-interview-service
```

---

## 3. 환경 변수 설정

백엔드에서 사용하는 주요 환경 변수는 다음과 같습니다.

### 3.1 데이터베이스

이 프로젝트는 MySQL을 기본 저장소로 사용하므로, 포팅 대상 환경에 MySQL 서버가 준비되어 있어야 합니다.

```env
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=3306
DB_NAME=your_db_name
```

예를 들어 로컬 환경에서는 다음처럼 설정할 수 있습니다.

```env
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=tooktac
```

### 3.2 인증 및 보안

```env
JWT_SECRET_KEY=your-secret-key
```

### 3.3 AI/클라우드 서비스

```env
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
GOOGLE_API_KEY=your_google_key
PROJECT_ID=your_google_project_id
PROCESSOR_ID=your_documentai_processor_id
LOCATION=us
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### 3.4 외부 STT/음성 서비스

```env
VITO_CLIENT_ID=your_vito_client_id
VITO_CLIENT_SECRET=your_vito_client_secret
CLOVA_SPEECH_API_URL=your_clova_url
CLOVA_API_KEY=your_clova_api_key
```

> 백엔드 코드에서는 `.env` 파일을 읽어 환경 변수를 사용하므로, 배포 서버에도 동일한 환경 변수를 설정해야 합니다.

---

## 4. 백엔드 포팅 절차

### 4.1 의존성 설치

```bash
cd back_tooktac
uv sync
```

### 4.2 데이터베이스 초기화

MySQL이 준비된 상태에서 다음 명령으로 테이블을 생성할 수 있습니다.

```bash
uv run python -c "from app.repository.database import Base, engine; import app.repository.model_registry; Base.metadata.create_all(engine)"
```

포팅 시에는 DB 접속 권한, 문자셋(예: utf8mb4), 인코딩, 스키마 생성 여부도 함께 확인해야 합니다.

### 4.3 백엔드 실행

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4.4 운영 환경 실행 권장 방식

운영 서버에서는 아래와 같은 방식으로 실행하는 것을 권장합니다.

- `systemd` 또는 `supervisord` 사용
- 로그 파일 출력 설정
- 자동 재시작 설정

예시:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 5. 프론트엔드 포팅 절차

### 5.1 의존성 설치

```bash
cd front_tooktac
npm install
```

### 5.2 프로덕션 빌드

```bash
npm run build
```

### 5.3 실행

```bash
npm run start
```

또는 개발 환경에서는:

```bash
npm run dev
```

---

## 6. CORS 및 도메인 설정

백엔드의 [back_tooktac/app/main.py](back_tooktac/app/main.py)에는 CORS 허용 origin이 정의되어 있습니다.

배포 시에는 다음 항목을 반드시 확인해야 합니다.

- 프론트엔드 도메인
- HTTPS 도메인
- 운영 환경 포트
- 실제 서비스 주소

예를 들어 운영 도메인이 `https://example.com`이라면, 백엔드의 CORS 허용 목록에 해당 도메인을 추가해야 합니다.

---

## 7. 포트 및 서비스 구성 예시

### 7.1 로컬 개발 환경

- 프론트엔드: http://localhost:3000
- 백엔드: http://localhost:8000

### 7.2 운영 서버 환경

- 프론트엔드: 80/443
- 백엔드 API: 8000 또는 리버스 프록시 경로 사용

예시 Nginx 구성:

```nginx
server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## 8. Windows 환경 포팅 체크리스트

Windows 서버나 로컬 환경에서 포팅할 때는 다음을 확인하세요.

- PowerShell 실행 정책 확인
- Python 가상환경 활성화
- 환경 변수 설정 확인
- MySQL 접속 가능 여부 확인
- Google Cloud 인증 파일 경로 확인
- 포트 3000, 8000, 3306이 열려 있는지 확인

예시:

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="3306"
$env:JWT_SECRET_KEY="your-secret-key"
```

---

## 9. 주의사항

- AI 관련 서비스는 외부 API 키가 필요합니다.
- Google Document AI 및 Gemini, OpenAI는 별도 인증이 필요합니다.
- 민감한 환경 변수는 소스 코드에 직접 포함하지 말고, 서버 환경 변수 또는 비밀 저장소를 사용하세요.
- 운영 배포 시에는 반드시 HTTPS를 사용하고, CORS와 인증 설정을 재점검하세요.

---

## 10. 요약

이 프로젝트를 포팅할 때 가장 중요한 점은 다음 세 가지입니다.

1. 백엔드 환경 변수 설정
2. MySQL 데이터베이스 연결 확인
3. 프론트엔드와 백엔드의 도메인/포트/인증 설정 정리

필요하면 다음 단계로 이어서 실제 배포용 Docker 구성이나 Nginx 설정 예시까지 추가해 드릴 수 있습니다.
