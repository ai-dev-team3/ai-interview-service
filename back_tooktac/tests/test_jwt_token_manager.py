"""core/jwt_token_updater.py — VITO 토큰 메모리 캐시 테스트"""
from datetime import datetime, timedelta

import pytest

from app.core.jwt_token_updater import JwtTokenManager


@pytest.fixture(autouse=True)
def reset_cache():
    """클래스 레벨 캐시를 테스트 간 격리"""
    JwtTokenManager._cached_token = None
    JwtTokenManager._expires_at = None
    yield
    JwtTokenManager._cached_token = None
    JwtTokenManager._expires_at = None


def _patch_fetch(monkeypatch, calls, token="tok-1", expire_at=None):
    def fake_fetch(self):
        calls.append(1)
        data = {"access_token": token}
        if expire_at is not None:
            data["expire_at"] = expire_at
        return data

    monkeypatch.setattr(JwtTokenManager, "_fetch_token", fake_fetch)


def test_token_cached_within_ttl(monkeypatch):
    calls = []
    _patch_fetch(monkeypatch, calls)

    manager = JwtTokenManager()
    assert manager.get_token() == "tok-1"
    assert manager.get_token() == "tok-1"
    assert JwtTokenManager().get_token() == "tok-1"  # 다른 인스턴스도 캐시 공유

    assert len(calls) == 1  # 발급은 1회만


def test_token_refetched_after_expiry(monkeypatch):
    calls = []
    _patch_fetch(monkeypatch, calls)

    manager = JwtTokenManager()
    manager.get_token()
    # 만료 임박 상태로 조작 (여유 마진 60초 안쪽)
    JwtTokenManager._expires_at = datetime.now() + timedelta(seconds=10)

    manager.get_token()
    assert len(calls) == 2  # 재발급 발생


def test_expire_at_from_response(monkeypatch):
    epoch = int((datetime.now() + timedelta(hours=2)).timestamp())
    _patch_fetch(monkeypatch, [], expire_at=epoch)

    JwtTokenManager().get_token()
    assert JwtTokenManager._expires_at == datetime.fromtimestamp(epoch)


def test_missing_credentials_raises(monkeypatch):
    monkeypatch.delenv("VITO_CLIENT_ID", raising=False)
    monkeypatch.delenv("VITO_CLIENT_SECRET", raising=False)

    manager = JwtTokenManager()
    with pytest.raises(RuntimeError):
        manager.get_token()
