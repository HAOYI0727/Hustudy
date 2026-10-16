import base64
import hashlib
import hmac
import secrets
import time
from typing import Optional
from uuid import UUID, uuid4

import jwt

ISSUER = "hustudy-local"
AUDIENCE = "hustudy-api"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
    return (
        "pbkdf2_sha256$180000$"
        + base64.urlsafe_b64encode(salt).decode()
        + "$"
        + base64.urlsafe_b64encode(digest).decode()
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, iterations, salt_text, digest_text = encoded.split("$", 3)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            base64.urlsafe_b64decode(salt_text),
            int(iterations),
        )
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(digest_text))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, secret: str, minutes: int) -> str:
    if len(secret) < 32:
        raise ValueError("JWT签名密钥至少32字符")
    now = int(time.time())
    return jwt.encode(
        {
            "sub": str(UUID(user_id)),
            "jti": str(uuid4()),
            "iat": now,
            "nbf": now,
            "exp": now + minutes * 60,
            "iss": ISSUER,
            "aud": AUDIENCE,
            "token_use": "access",
        },
        secret,
        algorithm="HS256",
    )


def read_access_token(token: str, secret: str) -> Optional[str]:
    try:
        if not isinstance(token, str) or len(token) > 8192 or len(secret) < 32:
            return None
        header = jwt.get_unverified_header(token)
        if header.get("typ") != "JWT" or "crit" in header:
            return None
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={
                "require": [
                    "sub",
                    "jti",
                    "iat",
                    "nbf",
                    "exp",
                    "iss",
                    "aud",
                    "token_use",
                ],
                "strict_aud": True,
            },
        )
        if payload["token_use"] != "access" or any(
            type(payload[field]) is not int for field in ("iat", "nbf", "exp")
        ):
            return None
        if payload["exp"] <= payload["iat"] or payload["nbf"] < payload["iat"]:
            return None
        UUID(payload["jti"])
        return str(UUID(payload["sub"]))
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError, AttributeError):
        return None
