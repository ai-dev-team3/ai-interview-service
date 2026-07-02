"""공용 테스트 픽스처.

- 테스트용 DB: 실 DB와 분리된 `{DB_NAME}_test` (또는 TEST_DB_NAME 환경변수)
- 각 테스트 후 모든 테이블을 비워 테스트 간 격리 보장
- 앱은 ML 라우터(audio/video)를 제외하고 구성 → torch/YOLO/MediaPipe 로드 없이 빠르게 실행
"""
import os

from dotenv import load_dotenv

# 앱 모듈은 import 시점에 os.getenv를 실행하므로, 어떤 app.* import보다 먼저 env를 채운다
load_dotenv()
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from datetime import date

import pymysql
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.repository.model_registry  # noqa: F401 — 모든 모델을 매퍼에 등록
from app.core.security import create_access_token
from app.repository.database import Base, get_db
from app.repository.user import User

TEST_DB_NAME = os.getenv("TEST_DB_NAME", os.getenv("DB_NAME", "tooktac").strip() + "_test")
TEST_DB_URL = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{TEST_DB_NAME}"
)


def _ensure_test_database():
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{TEST_DB_NAME}`")
    finally:
        conn.close()


@pytest.fixture(scope="session")
def engine():
    _ensure_test_database()
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    yield session
    session.close()
    # 테스트 간 격리: 모든 테이블 비우기
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


@pytest.fixture()
def test_app(db_session):
    """audio/video(ML) 라우터를 제외한 테스트용 앱"""
    from app.api.interview import router as interview_router
    from app.api.report import router as report_router
    from app.api.result import router as result_router
    from app.api.signup import router as signup_router
    from app.api.training_page import router as training_page_router
    from app.api.user import router as user_router

    app = FastAPI()
    for router in (signup_router, user_router, interview_router,
                   result_router, report_router, training_page_router):
        app.include_router(router)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture()
def client(test_app):
    return TestClient(test_app)


@pytest.fixture()
def test_user(db_session):
    user = User(
        username="tester",
        password="pw1234",
        name="테스터",
        nickname="테테",
        email="tester@example.com",
        birthdate=date(2000, 1, 1),
        desired_job="백엔드 개발자",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def auth_client(client, test_user):
    """access_token 쿠키가 세팅된 인증 클라이언트"""
    token = create_access_token(test_user.id)
    client.cookies.set("access_token", token)
    return client
