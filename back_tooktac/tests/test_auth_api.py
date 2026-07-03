"""회원가입/로그인/로그아웃/me API 유닛 테스트"""


def _signup_form(username="newuser"):
    return {
        "username": username,
        "password": "pw1234",
        "name": "신규유저",
        "nickname": "뉴비",
        "email": f"{username}@example.com",
        "birthdate": "1999-12-31",
        "desiredJob": "프론트엔드 개발자",
    }


def test_signup_creates_user(client, db_session):
    res = client.post("/signup", data=_signup_form())
    assert res.status_code == 200
    assert "user_id" in res.json()

    from app.repository.user import User

    user = db_session.query(User).filter_by(username="newuser").first()
    assert user is not None


def test_signup_stores_hashed_password(client, db_session):
    from app.core.password import is_bcrypt_hash, verify_password
    from app.repository.user import User

    client.post("/signup", data=_signup_form("hashuser"))

    user = db_session.query(User).filter_by(username="hashuser").first()
    assert user.password != "pw1234"
    assert is_bcrypt_hash(user.password)
    assert verify_password("pw1234", user.password)


def test_signup_duplicate_username_409(client, test_user):
    form = _signup_form(test_user.username)
    res = client.post("/signup", data=form)
    assert res.status_code == 409


def test_signup_duplicate_email_409(client, test_user):
    form = _signup_form("anotheruser")
    form["email"] = test_user.email
    res = client.post("/signup", data=form)
    assert res.status_code == 409


def test_signup_invalid_email_400(client):
    form = _signup_form("bademail")
    form["email"] = "not-an-email"
    res = client.post("/signup", data=form)
    assert res.status_code == 400


def test_signup_invalid_birthdate_400(client):
    form = _signup_form("badbirth")
    form["birthdate"] = "31-12-1999"
    res = client.post("/signup", data=form)
    assert res.status_code == 400


def test_check_username_availability(client, test_user):
    res = client.get("/check-username", params={"username": test_user.username})
    assert res.status_code == 200
    assert res.json()["available"] is False

    res = client.get("/check-username", params={"username": "unused-name"})
    assert res.json()["available"] is True


def test_login_success_sets_cookie(client, test_user):
    res = client.post("/login", data={"username": "tester", "password": "pw1234"})
    assert res.status_code == 200
    assert "access_token" in res.cookies


def test_login_wrong_password_401(client, test_user):
    res = client.post("/login", data={"username": "tester", "password": "wrong"})
    assert res.status_code == 401


def test_login_migrates_legacy_plaintext_password(client, db_session, test_user):
    """평문 비밀번호 사용자가 로그인하면 bcrypt 해시로 자동 마이그레이션"""
    from app.core.password import is_bcrypt_hash, verify_password

    assert test_user.password == "pw1234"  # 레거시 평문 상태

    res = client.post("/login", data={"username": "tester", "password": "pw1234"})
    assert res.status_code == 200

    db_session.refresh(test_user)
    assert is_bcrypt_hash(test_user.password)
    assert verify_password("pw1234", test_user.password)

    # 마이그레이션 후에도 로그인 가능
    res = client.post("/login", data={"username": "tester", "password": "pw1234"})
    assert res.status_code == 200


def test_login_hashed_user_success(client, db_session):
    from datetime import date

    from app.core.password import hash_password
    from app.repository.user import User

    user = User(
        username="hashed", password=hash_password("secret!"), name="해시",
        nickname="해시", email="hashed@example.com",
        birthdate=date(2000, 1, 1), desired_job="백엔드",
    )
    db_session.add(user)
    db_session.commit()

    assert client.post("/login", data={"username": "hashed", "password": "secret!"}).status_code == 200
    assert client.post("/login", data={"username": "hashed", "password": "wrong"}).status_code == 401


def test_me_requires_auth(client):
    res = client.get("/me")
    assert res.status_code == 401


def test_me_returns_profile(auth_client, test_user):
    res = auth_client.get("/me")
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == test_user.id
    assert body["nickname"] == test_user.nickname


def test_me_deleted_user_401(client):
    """토큰은 유효하지만 사용자가 삭제된 경우 401"""
    from app.core.security import create_access_token

    client.cookies.set("access_token", create_access_token(999999))
    res = client.get("/me")
    assert res.status_code == 401


def test_logout_clears_cookie(auth_client):
    res = auth_client.post("/logout")
    assert res.status_code == 200
    # max_age=0 쿠키가 내려와야 함
    set_cookie = res.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    assert 'Max-Age=0' in set_cookie or 'max-age=0' in set_cookie.lower()
