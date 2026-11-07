from app.core.security import (
    create_access_token,
    hash_password,
    read_access_token,
    verify_password,
)


def test_password_hash_round_trip():
    encoded = hash_password("correct horse battery staple")
    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong", encoded)


def test_access_token_rejects_tampering():
    from uuid import uuid4

    user_id = str(uuid4())
    secret = "test-signing-key-that-is-at-least-32-characters"
    token = create_access_token(user_id, secret, 5)
    assert len(token.split(".")) == 3
    assert read_access_token(token, secret) == user_id
    assert read_access_token(token + "x", secret) is None


def test_auth_api_rejects_duplicate_bad_password_and_expired_session():
    from uuid import uuid4
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.config import get_settings

    with TestClient(app) as client:
        payload = {
            "username": "auth_" + uuid4().hex[:12],
            "password": "test-password-123",
        }
        registered = client.post("/api/v1/auth/register", json=payload)
        assert registered.status_code == 201
        user_id = registered.json()["user"]["id"]
        assert "password" not in registered.json()["user"]
        assert client.post("/api/v1/auth/register", json=payload).status_code == 409
        assert (
            client.post(
                "/api/v1/auth/login", json={**payload, "password": "wrong-password"}
            ).status_code
            == 401
        )
        login = client.post("/api/v1/auth/login", json=payload)
        assert login.status_code == 200
        token = login.json()["access_token"]
        assert (
            client.get(
                "/api/v1/auth/me", headers={"Authorization": "Bearer " + token}
            ).json()["id"]
            == user_id
        )
        expired = create_access_token(user_id, get_settings().jwt_secret, -1)
        for invalid in (None, token + "x", expired):
            headers = {} if invalid is None else {"Authorization": "Bearer " + invalid}
            for path in ("/api/v1/auth/me", "/api/v1/courses"):
                response = client.get(path, headers=headers)
                assert response.status_code == 401
                assert (
                    response.json()["error"]["request_id"]
                    == response.headers["X-Request-ID"]
                )
