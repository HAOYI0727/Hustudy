"""Account-owned model profiles; private encrypted files, never account archives."""

from urllib.parse import urlsplit
from pydantic import SecretStr
from fastapi import HTTPException
from cryptography.fernet import InvalidToken
from . import account_connection as store

NAMESPACE = "model-connections"
HOSTS = {
    "api.deepseek.com",
    "dashscope.aliyuncs.com",
    "api.siliconflow.cn",
    "api.moonshot.cn",
    "ark.cn-beijing.volces.com",
    "open.bigmodel.cn",
}


def read(settings, user_id):
    data = store.read(settings, user_id, NAMESPACE)
    if not data and store.resolve_path(settings, user_id, NAMESPACE).exists():
        raise HTTPException(
            409, "模型配置文件无法核对，已停止AI调用；请检查服务端配置文件"
        )
    if data and (
        not isinstance(data.get("profiles"), list)
        or len(data["profiles"]) > 8
        or any(
            not isinstance(p, dict)
            or not all(
                k in p
                for k in (
                    "id",
                    "name",
                    "vendor",
                    "model",
                    "endpoint",
                    "vision",
                    "thinking",
                    "json_mode",
                )
            )
            for p in data["profiles"]
        )
    ):
        raise HTTPException(409, "模型配置结构无法核对，已停止AI调用")
    return data


def endpoint(value, settings):
    try:
        parsed = urlsplit(value.strip())
        hosts = HOSTS | {
            h.strip().lower()
            for h in settings.additional_ai_hosts.split(",")
            if h.strip()
        }
        if (
            parsed.scheme != "https"
            or parsed.hostname not in hosts
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not parsed.path.endswith("/chat/completions")
            or ".." in parsed.path
            or "\\" in value
        ):
            raise ValueError()
    except ValueError:
        raise HTTPException(
            422,
            "请填写受支持服务商的HTTPS chat/completions地址；其他主机需由部署者配置HUSTUDY_ADDITIONAL_AI_HOSTS",
        ) from None
    return value.strip()


def profile_key(settings, user_id, profile):
    try:
        return (
            store.cipher(settings, user_id)
            .decrypt(profile.get("encrypted_key", "").encode())
            .decode()
        )
    except (InvalidToken, ValueError, AttributeError, UnicodeError):
        return ""


def apply(settings, user_id):
    data = read(settings, user_id)
    if not data:
        return settings
    # Selection mutations invalidate previews even when switching away and back.
    revision = settings.credential_revision * 1000000000 + data["revision"]
    selected = data.get("active")
    if not selected:
        return settings.model_copy(update={"credential_revision": revision})
    profile = next(
        (p for p in data.get("profiles", []) if p.get("id") == selected), None
    )
    if profile is None:
        return settings.model_copy(
            update={
                "llm_provider": "mock",
                "zhipu_api_key": SecretStr(""),
                "credential_revision": revision,
            }
        )
    try:
        target = endpoint(profile["endpoint"], settings)
    except (HTTPException, KeyError):
        return settings.model_copy(
            update={
                "llm_provider": "mock",
                "zhipu_api_key": SecretStr(""),
                "credential_revision": revision,
            }
        )
    key = profile_key(settings, user_id, profile)
    return settings.model_copy(
        update={
            "llm_provider": "compatible" if key else "mock",
            "llm_model": profile["model"],
            "llm_endpoint": target,
            "zhipu_api_key": SecretStr(key),
            "credential_revision": revision,
            "llm_vendor": profile["vendor"],
            "llm_vision": profile.get("vision", False),
            "llm_thinking": profile.get("thinking", False),
            "llm_json_mode": profile.get("json_mode", True),
        }
    )


def status(settings, user_id):
    data = read(settings, user_id)
    profiles = [
        {
            k: p[k]
            for k in (
                "id",
                "name",
                "vendor",
                "endpoint",
                "model",
                "vision",
                "thinking",
                "json_mode",
            )
        }
        | {"configured": bool(profile_key(settings, user_id, p))}
        for p in data.get("profiles", [])
    ]
    original = store.effective(settings, user_id)
    return {
        "revision": data.get("revision", 0),
        "active": data.get("active"),
        "profiles": profiles,
        "builtin": {
            "name": "原智谱配置",
            "model": original.llm_model,
            "configured": bool(original.zhipu_api_key.get_secret_value()),
        },
        "allowed_hosts": sorted(
            HOSTS
            | {
                h.strip().lower()
                for h in settings.additional_ai_hosts.split(",")
                if h.strip()
            }
        ),
    }
