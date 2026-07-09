"""CORS/쿠키 설정 검증 — 잘못된 조합은 기동 시점에 실패해야 한다"""
import importlib

import pytest

from app import config


def _set_valid(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(config, "JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setattr(config, "CORS_ALLOWED_ORIGINS", ["http://localhost:3000"])
    monkeypatch.setattr(config, "COOKIE_SAMESITE", "lax")
    monkeypatch.setattr(config, "COOKIE_SECURE", False)


def test_valid_settings_pass(monkeypatch):
    _set_valid(monkeypatch)
    config.validate_settings()


def test_missing_cors_origins_fails(monkeypatch):
    _set_valid(monkeypatch)
    monkeypatch.setattr(config, "CORS_ALLOWED_ORIGINS", [])

    with pytest.raises(RuntimeError, match="CORS_ALLOWED_ORIGINS"):
        config.validate_settings()


def test_invalid_samesite_fails(monkeypatch):
    _set_valid(monkeypatch)
    monkeypatch.setattr(config, "COOKIE_SAMESITE", "bogus")

    with pytest.raises(RuntimeError, match="COOKIE_SAMESITE"):
        config.validate_settings()


def test_samesite_none_without_secure_fails(monkeypatch):
    """SameSite=None + Secure 누락은 브라우저가 쿠키를 조용히 버려 로그인이 깨진다"""
    _set_valid(monkeypatch)
    monkeypatch.setattr(config, "COOKIE_SAMESITE", "none")
    monkeypatch.setattr(config, "COOKIE_SECURE", False)

    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        config.validate_settings()


def test_empty_cookie_env_falls_back_to_dev_defaults(monkeypatch):
    """.env에 키만 있고 값이 빈 경우("COOKIE_SECURE=")도 미설정과 같아야 한다"""
    monkeypatch.setenv("COOKIE_DOMAIN", "")
    monkeypatch.setenv("COOKIE_SECURE", "")
    monkeypatch.setenv("COOKIE_SAMESITE", "")

    reloaded = importlib.reload(config)
    try:
        assert reloaded.COOKIE_DOMAIN is None
        assert reloaded.COOKIE_SECURE is False
        assert reloaded.COOKIE_SAMESITE == "lax"
    finally:
        # 다른 테스트가 쓰는 모듈 전역을 원래 env 기준으로 되돌린다
        monkeypatch.undo()
        importlib.reload(config)
