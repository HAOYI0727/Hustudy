"""Optional model profiles; the original Zhipu configuration remains independent."""

from uuid import UUID, uuid4
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from ..dependencies import current_user
from ..models import User
from ..core.config import base_settings, get_user_settings
from ..core import account_connection as store, model_connections as profiles
from ..ai.providers import ZhipuProvider, ProviderFailure

router = APIRouter(prefix="/api/v1/model-connections", tags=["model-connections"])


class Save(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    revision: int = Field(ge=0, lt=1000000000, strict=True)
    id: UUID | None = None
    name: str = Field(min_length=1, max_length=60)
    vendor: Literal["deepseek", "compatible"] = "deepseek"
    endpoint: str = Field(max_length=500)
    model: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_./:-]+$")
    key: SecretStr | None = None
    vision: bool = Field(default=False, strict=True)
    thinking: bool = Field(default=False, strict=True)
    json_mode: bool = Field(default=True, strict=True)


class Select(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0, strict=True)
    profile_id: UUID | None = None


class Probe(BaseModel):
    ok: bool


class Check(Select):
    confirm: bool = Field(default=False, strict=True)


def changed(data, revision):
    if data.get("revision", 0) != revision:
        raise HTTPException(409, "模型配置已变化，请刷新后重试")


@router.get("")
def get_connections(response: Response, user: User = Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return profiles.status(base_settings(), user.id)


@router.put("")
def save(payload: Save, user: User = Depends(current_user)):
    settings = base_settings()
    target = profiles.endpoint(payload.endpoint, settings)
    if payload.vendor == "deepseek" and not target.startswith(
        "https://api.deepseek.com/"
    ):
        raise HTTPException(422, "DeepSeek配置请使用官方api.deepseek.com地址")
    with store.locked(settings, user.id, profiles.NAMESPACE):
        data = profiles.read(settings, user.id)
        changed(data, payload.revision)
        rows = data.get("profiles", [])
        identity = str(payload.id or uuid4())
        old = next((p for p in rows if p["id"] == identity), None)
        if payload.id and old is None:
            raise HTTPException(404, "模型配置不存在")
        if not old and len(rows) >= 8:
            raise HTTPException(422, "每个账户最多保存8份模型配置")
        key = (
            payload.key.get_secret_value().strip()
            if payload.key is not None
            else profiles.profile_key(settings, user.id, old or {})
        )
        if not 8 <= len(key) <= 512 or any(c.isspace() or ord(c) < 32 for c in key):
            raise HTTPException(422, "请完整复制API Key；留空仅保留这份配置原有的密钥")
        row = {
            **payload.model_dump(exclude={"revision", "id", "key"}),
            "id": identity,
            "endpoint": target,
            "encrypted_key": store.cipher(settings, user.id)
            .encrypt(key.encode())
            .decode(),
        }
        store.write(
            settings,
            user.id,
            {
                "revision": payload.revision + 1,
                "active": data.get("active"),
                "profiles": [row if p["id"] == identity else p for p in rows]
                if old
                else [*rows, row],
            },
            profiles.NAMESPACE,
        )
    return profiles.status(settings, user.id)


@router.post("/active")
def select(payload: Select, user: User = Depends(current_user)):
    settings = base_settings()
    with store.locked(settings, user.id, profiles.NAMESPACE):
        data = profiles.read(settings, user.id)
        changed(data, payload.revision)
        identity = str(payload.profile_id) if payload.profile_id else None
        if identity and not any(p["id"] == identity for p in data.get("profiles", [])):
            raise HTTPException(404, "模型配置不存在")
        store.write(
            settings,
            user.id,
            {
                **data,
                "profiles": data.get("profiles", []),
                "revision": payload.revision + 1,
                "active": identity,
            },
            profiles.NAMESPACE,
        )
    return profiles.status(settings, user.id)


@router.delete("/{profile_id}")
def remove(profile_id: UUID, revision: int, user: User = Depends(current_user)):
    settings = base_settings()
    with store.locked(settings, user.id, profiles.NAMESPACE):
        data = profiles.read(settings, user.id)
        changed(data, revision)
        if not any(p["id"] == str(profile_id) for p in data.get("profiles", [])):
            raise HTTPException(404, "模型配置不存在")
        if data.get("active") == str(profile_id):
            raise HTTPException(409, "请先切换到其他模型，再删除当前配置")
        store.write(
            settings,
            user.id,
            {
                **data,
                "revision": revision + 1,
                "profiles": [
                    p for p in data.get("profiles", []) if p["id"] != str(profile_id)
                ],
            },
            profiles.NAMESPACE,
        )
    return profiles.status(settings, user.id)


@router.post("/test")
def test(payload: Check, user: User = Depends(current_user)):
    if not payload.confirm:
        raise HTTPException(422, "请同意发送极短连接测试文本")
    settings = base_settings()
    data = profiles.read(settings, user.id)
    changed(data, payload.revision)
    # Only the explicitly selected active configuration is probed. No fallback.
    if (str(payload.profile_id) if payload.profile_id else None) != data.get("active"):
        raise HTTPException(409, "请先选择要测试的模型")
    effective = get_user_settings(user.id)
    if not effective.zhipu_api_key.get_secret_value():
        raise HTTPException(409, "请先保存模型密钥")
    try:
        result, _usage = ZhipuProvider(effective).structured(
            "连接测试", [], '只输出JSON：{"ok":true}', Probe, max_tokens=512
        )
        return {
            "connected": result.ok,
            "model": effective.llm_model,
            "message": "本次连接测试完成",
        }
    except ProviderFailure as exc:
        return {
            "connected": False,
            "model": effective.llm_model,
            "message": exc.message,
        }
