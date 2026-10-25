"""Explicit account-scoped API setup and minimal consented connection test."""

from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, SecretStr, Field
from ..dependencies import current_user
from ..models import User
from ..core.config import base_settings, get_user_settings
from ..core import account_connection as store
from ..ai.providers import ZhipuProvider, ProviderFailure

router = APIRouter(prefix="/api/v1/api-connection", tags=["api-connection"])


class Save(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    revision: int = Field(ge=0, strict=True)
    key: SecretStr | None = None
    model: Literal["glm-5.3-flash", "glm-4.7-flash"] = "glm-5.3-flash"


class Check(BaseModel):
    revision: int = Field(ge=0, strict=True)
    confirm: bool = Field(default=False, strict=True)


class Probe(BaseModel):
    ok: bool


def status(user_id):
    settings = get_user_settings(user_id)
    try:
        data = store.read(base_settings(), user_id)
    except (OSError, ValueError):
        data = {}
    configured = settings.llm_provider == "zhipu" and bool(
        settings.zhipu_api_key.get_secret_value()
    )
    return {
        "configured": configured,
        "model": settings.llm_model,
        "revision": data.get("revision", 0),
        "scope": "account",
        "endpoint": settings.llm_endpoint,
        "test_status": data.get("test_status", "not_tested")
        if configured
        else "not_configured",
        "tested_at": data.get("tested_at"),
        "message": data.get("message", "")
        if configured
        else "请粘贴模型标准API的密钥后保存",
        "guide_url": "https://docs.bigmodel.cn/cn/guide/start/quick-start",
        "key_url": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
    }


@router.get("")
def get_connection(response: Response, user: User = Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return status(user.id)


@router.put("")
def save_connection(payload: Save, user: User = Depends(current_user)):
    with store.locked(base_settings(), user.id):
        settings = base_settings()
        old = store.read(settings, user.id)
        if payload.revision != old.get("revision", 0):
            raise HTTPException(409, "API配置已变化，请刷新状态后重试")
        if payload.key is not None:
            key = payload.key.get_secret_value().strip()
            if len(key) < 8 or len(key) > 512 or any(c.isspace() for c in key):
                raise HTTPException(422, "密钥格式不正确，请完整复制模型标准API Key")
        else:
            key = get_user_settings(user.id).zhipu_api_key.get_secret_value()
        if not key:
            raise HTTPException(422, "请先粘贴API Key")
        store.write(
            settings,
            user.id,
            {
                "revision": payload.revision + 1,
                "model": payload.model,
                "encrypted_key": store.cipher(settings, user.id)
                .encrypt(key.encode())
                .decode(),
                "test_status": "not_tested",
            },
        )
    return status(user.id)


@router.delete("")
def clear_connection(revision: int, user: User = Depends(current_user)):
    with store.locked(base_settings(), user.id):
        settings = base_settings()
        old = store.read(settings, user.id)
        if revision != old.get("revision", 0):
            raise HTTPException(409, "API配置已变化，请刷新后重试")
        store.write(
            settings,
            user.id,
            {
                "revision": revision + 1,
                "model": get_user_settings(user.id).llm_model,
                "encrypted_key": None,
                "test_status": "not_configured",
            },
        )
    return status(user.id)


def probe(settings):
    result, _usage = ZhipuProvider(settings).structured(
        "连接测试", [], '只返回JSON：{"ok":true}', Probe, max_tokens=512
    )
    if not result.ok:
        raise ProviderFailure("TEST_FAILED", "连接测试未通过，请重新测试")


@router.post("/test")
def test_connection(payload: Check, user: User = Depends(current_user)):
    if not payload.confirm:
        raise HTTPException(422, "请确认发送极短连接测试文本")
    with store.locked(base_settings(), user.id):
        before = status(user.id)
        if payload.revision != before["revision"]:
            raise HTTPException(409, "API配置已变化，请刷新后测试")
        if not before["configured"]:
            raise HTTPException(409, "请先保存API Key")
        settings = get_user_settings(user.id)
    try:
        probe(settings)
        outcome, message = "connected", "连接测试成功，可以使用AI功能"
    except ProviderFailure as exc:
        outcome, message = "failed", exc.message
    with store.locked(base_settings(), user.id):
        if status(user.id)["revision"] != payload.revision:
            raise HTTPException(409, "测试期间配置已变化，本次结果已丢弃")
        data = store.read(base_settings(), user.id)
        if not data:
            data = {
                "revision": 0,
                "model": settings.llm_model,
                "encrypted_key": store.cipher(base_settings(), user.id)
                .encrypt(settings.zhipu_api_key.get_secret_value().encode())
                .decode(),
            }
        data.update(
            test_status=outcome,
            message=message,
            tested_at=datetime.now(timezone.utc).isoformat(),
        )
        store.write(base_settings(), user.id, data)
    return status(user.id)
