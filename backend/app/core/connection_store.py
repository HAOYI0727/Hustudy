"""Machine-wide encrypted API configuration; never part of account archives."""

import base64
import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import SecretStr

LOCK = RLock()


def path(settings):
    return Path(settings.storage_root).resolve().parent / "ai-connection.json"


def cipher(settings):
    key = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=b"hustudy-machine-ai-v1"
    ).derive(settings.jwt_secret.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def read(settings):
    target = path(settings)
    return json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}


def write(settings, value):
    target = path(settings)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".api-config-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def apply(settings):
    try:
        data = read(settings)
        if not data:
            return settings
        key = (
            cipher(settings).decrypt(data["encrypted_key"].encode()).decode()
            if data.get("encrypted_key")
            else ""
        )
        model = data.get("model", settings.llm_model)
        if model not in {"glm-5.3-flash", "glm-4.7-flash"}:
            raise ValueError("model")
        return settings.model_copy(
            update={
                "llm_provider": "zhipu" if key else "mock",
                "llm_model": model,
                "zhipu_api_key": SecretStr(key),
            }
        )
    except (OSError, ValueError, KeyError, InvalidToken):
        return settings.model_copy(
            update={"llm_provider": "mock", "zhipu_api_key": SecretStr("")}
        )
