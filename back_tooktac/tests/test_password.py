"""core/password.py — bcrypt 해싱/검증 유닛 테스트"""
from app.core.password import hash_password, is_bcrypt_hash, verify_password


def test_hash_and_verify_roundtrip():
    hashed = hash_password("pw1234")
    assert hashed != "pw1234"
    assert is_bcrypt_hash(hashed)
    assert verify_password("pw1234", hashed)
    assert not verify_password("wrong", hashed)


def test_verify_against_plaintext_stored_value_is_false():
    # DB에 평문이 저장돼 있던 레거시 값은 bcrypt 검증이 아니라 False
    assert not verify_password("pw1234", "pw1234")


def test_is_bcrypt_hash_detects_plaintext():
    assert not is_bcrypt_hash("pw1234")
    assert not is_bcrypt_hash("")


def test_long_password_over_72_bytes():
    long_pw = "a" * 100
    hashed = hash_password(long_pw)
    assert verify_password(long_pw, hashed)
