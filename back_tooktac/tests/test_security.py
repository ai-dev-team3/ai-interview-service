"""core/security.py — JWT 발급/검증 유닛 테스트"""
from datetime import timedelta

import pytest

from app.core.security import create_access_token, decode_access_token


def test_token_roundtrip():
    token = create_access_token(user_id=42)
    assert decode_access_token(token) == 42


def test_expired_token_rejected():
    token = create_access_token(user_id=1, expires_delta=timedelta(seconds=-1))
    with pytest.raises(ValueError):
        decode_access_token(token)


def test_garbage_token_rejected():
    with pytest.raises(ValueError):
        decode_access_token("not-a-jwt")


def test_tampered_token_rejected():
    token = create_access_token(user_id=1)
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
    with pytest.raises(ValueError):
        decode_access_token(tampered)
