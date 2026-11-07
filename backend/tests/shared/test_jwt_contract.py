import base64
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import time
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.security import AUDIENCE, ISSUER, create_access_token, read_access_token
from app.main import app

KEY = "deterministic-jwt-contract-test-key-123456789-only-tests-keep-64-bytes"


def claims():
    now = int(time.time())
    return dict(
        sub=str(uuid4()),
        jti=str(uuid4()),
        iat=now,
        nbf=now,
        exp=now + 300,
        iss=ISSUER,
        aud=AUDIENCE,
        token_use="access",
    )


@pytest.mark.parametrize(
    "change",
    [
        {"iss": "other-app"},
        {"aud": "other-api"},
        {"aud": [AUDIENCE]},
        {"token_use": "refresh"},
        {"sub": "not-uuid"},
        {"jti": "not-uuid"},
        {"exp": True},
        {"exp": str(int(time.time()) + 1000)},
        {"iat": int(time.time()) + 1000},
        {"nbf": int(time.time()) + 1000},
        {"exp": int(time.time()) - 1},
    ],
)
def test_signed_wrong_claims_are_not_access_tokens(change):
    token = jwt.encode({**claims(), **change}, KEY, algorithm="HS256")
    assert read_access_token(token, KEY) is None


@pytest.mark.parametrize(
    "missing", ["exp", "sub", "jti", "iat", "nbf", "iss", "aud", "token_use"]
)
def test_signed_tokens_require_all_claims(missing):
    data = claims()
    data.pop(missing)
    assert read_access_token(jwt.encode(data, KEY, algorithm="HS256"), KEY) is None


def test_wrong_algorithm_headers_legacy_and_malformed_are_rejected():
    payload = claims()
    tokens = [
        jwt.encode(payload, KEY, algorithm="HS384"),
        jwt.encode(payload, None, algorithm="none"),
        jwt.encode(payload, KEY, algorithm="HS256", headers={"typ": "refresh"}),
        jwt.encode(payload, KEY, algorithm="HS256", headers={"crit": ["custom"]}),
        "",
        ".",
        "...",
        "a" * 8193,
    ]
    body = (
        base64.urlsafe_b64encode(
            json.dumps({"sub": payload["sub"], "exp": int(time.time()) + 300}).encode()
        )
        .decode()
        .rstrip("=")
    )
    signature = (
        base64.urlsafe_b64encode(
            hmac.new(KEY.encode(), body.encode(), hashlib.sha256).digest()
        )
        .decode()
        .rstrip("=")
    )
    tokens.append(body + "." + signature)
    for token in tokens:
        assert read_access_token(token, KEY) is None
    valid = create_access_token(payload["sub"], KEY, 5)
    assert read_access_token(valid, KEY + "different") is None
    decoded = jwt.decode(
        valid, KEY, algorithms=["HS256"], audience=AUDIENCE, issuer=ISSUER
    )
    assert decoded["sub"] == payload["sub"]
    with pytest.raises(ValueError):
        create_access_token(payload["sub"], "short", 5)


def test_auth_upgrade_keeps_account_and_course_and_rejects_legacy():
    with TestClient(app) as client:
        account = {
            "username": "jwt_" + uuid4().hex[:12],
            "password": "password-test-only",
        }
        created = client.post("/api/v1/auth/register", json=account).json()
        token = created["access_token"]
        headers = {"Authorization": "Bearer " + token}
        course = client.post(
            "/api/v1/courses", headers=headers, json={"name": "JWT test"}
        ).json()
        new_token = client.post("/api/v1/auth/login", json=account).json()[
            "access_token"
        ]
        assert new_token != token
        listed = client.get(
            "/api/v1/courses", headers={"Authorization": "Bearer " + new_token}
        ).json()
        assert course["id"] in [row["id"] for row in listed]
        fake = jwt.encode(
            {**claims(), "sub": created["user"]["id"]},
            get_settings().jwt_secret,
            algorithm="HS384",
        )
        for invalid in [
            fake,
            "old-body.signature",
            create_access_token(created["user"]["id"], get_settings().jwt_secret, -1),
        ]:
            response = client.get(
                "/api/v1/auth/me", headers={"Authorization": "Bearer " + invalid}
            )
            assert response.status_code == 401
            assert response.headers["WWW-Authenticate"] == "Bearer"
            assert invalid not in response.text


def test_signing_setup_preserves_valid_keys_and_other_configuration(tmp_path):
    path = Path(__file__).resolve().parents[3] / "scripts/configure_auth.py"
    spec = importlib.util.spec_from_file_location("configure_auth", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    env = tmp_path / ".env"
    env.write_text(
        "HUSTUDY_JWT_SECRET=change-this-in-development\nHUSTUDY_ZHIPU_API_KEY=fake-preserved\nOTHER=value\n"
    )
    assert module.configure(env)
    first = env.read_text()
    assert "HUSTUDY_ZHIPU_API_KEY=fake-preserved" in first
    assert "OTHER=value" in first
    assert "change-this-in-development" not in first
    assert env.stat().st_mode & 0o777 == 0o600
    assert not module.configure(env)
    assert env.read_text() == first
    link = tmp_path / "link"
    link.symlink_to(env)
    with pytest.raises(ValueError):
        module.configure(link)
    with pytest.raises(ValueError):
        Settings(jwt_secret="short", _env_file=None)
