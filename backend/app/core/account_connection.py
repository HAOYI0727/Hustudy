"""Private, account-bound credentials. Never fall back to machine credentials."""

import base64
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID
from threading import RLock
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import HTTPException
from pydantic import SecretStr

LOCK = RLock()


def path(settings, user_id, namespace="api-connections"):
    identity = str(UUID(user_id))
    return (
        Path(settings.storage_root).resolve().parent
        / namespace
        / (identity + ".json")
    )


def cipher(settings, user_id):
    key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=("hustudy-account-ai-v1:" + str(UUID(user_id))).encode(),
    ).derive(settings.jwt_secret.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def read(settings, user_id, namespace="api-connections"):
    try:
        data = json.loads(path(settings, user_id, namespace).read_text(encoding="utf-8"))
        if (
            not isinstance(data, dict)
            or data.get("user_id") != user_id
            or type(data.get("revision")) is not int
            or data["revision"] < 1
        ):
            return {}
        return data
    except (OSError, ValueError):
        return {}


@contextmanager
def locked(settings, user_id, namespace="api-connections"):
    """Short mutation lock shared by API processes; never held during HTTP calls."""
    with LOCK:
        target = path(settings, user_id, namespace).with_suffix(".lock")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a+b") as stream:
            if not target.stat().st_size:
                stream.write(b"0")
                stream.flush()
            try:
                if os.name == "nt":
                    import msvcrt

                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise HTTPException(
                    409, "本账户API配置正在更新，请稍后刷新重试"
                ) from None
            try:
                yield
            finally:
                if os.name == "nt":
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)


def write(settings, user_id, data, namespace="api-connections"):
    target = path(settings, user_id, namespace)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".account-ai-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({**data, "user_id": user_id}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def effective(settings, user_id):
    data = read(settings, user_id)
    key = ""
    try:
        if data.get("encrypted_key"):
            key = (
                cipher(settings, user_id)
                .decrypt(data["encrypted_key"].encode())
                .decode()
            )
    except (InvalidToken, ValueError, AttributeError, UnicodeError):
        key = ""
    model = data.get("model", settings.llm_model)
    if model not in {"glm-4.7-flash", "glm-5.3-flash"}:
        model, key = settings.llm_model, ""
    return settings.model_copy(
        update=dict(
            llm_provider="zhipu" if key else "mock",
            llm_model=model,
            zhipu_api_key=SecretStr(key),
            credential_account_id=user_id,
            credential_revision=data.get("revision", 0),
        )
    )


def binding(settings):
    return {
        "user_id": settings.credential_account_id,
        "revision": settings.credential_revision,
    }
