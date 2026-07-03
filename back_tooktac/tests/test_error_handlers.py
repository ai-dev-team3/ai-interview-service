"""전역 예외 핸들러 — 미처리 예외가 CORS 헤더 붙은 500으로 변환되는지 검증"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.error_handlers import register_exception_handlers

ORIGIN = "http://localhost:3000"


def _make_app():
    app = FastAPI()
    register_exception_handlers(app, [ORIGIN])

    @app.get("/boom")
    def boom():
        raise RuntimeError("의도된 테스트 예외")

    return app


def test_unhandled_exception_returns_500_with_cors():
    client = TestClient(_make_app(), raise_server_exceptions=False)

    res = client.get("/boom", headers={"Origin": ORIGIN})

    assert res.status_code == 500
    assert res.headers["access-control-allow-origin"] == ORIGIN
    assert res.headers["access-control-allow-credentials"] == "true"
    assert "detail" in res.json()


def test_unknown_origin_gets_no_cors_header():
    client = TestClient(_make_app(), raise_server_exceptions=False)

    res = client.get("/boom", headers={"Origin": "http://evil.example.com"})

    assert res.status_code == 500
    assert "access-control-allow-origin" not in res.headers
