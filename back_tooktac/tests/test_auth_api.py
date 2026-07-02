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


def test_me_requires_auth(client):
    res = client.get("/me")
    assert res.status_code == 401


def test_me_returns_profile(auth_client, test_user):
    res = auth_client.get("/me")
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == test_user.id
    assert body["nickname"] == test_user.nickname


def test_logout_clears_cookie(auth_client):
    res = auth_client.post("/logout")
    assert res.status_code == 200
    # max_age=0 쿠키가 내려와야 함
    set_cookie = res.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    assert 'Max-Age=0' in set_cookie or 'max-age=0' in set_cookie.lower()
