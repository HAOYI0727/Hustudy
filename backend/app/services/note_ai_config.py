import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import select
from ..core.config import get_settings
from ..models import NoteAIConfig
from ..ai.providers import ProviderFailure

DISABLED_REASON = "笔记AI整理已停用，请将识别文本插入当前笔记"


def owned_config(db, user_id):
    return db.scalar(select(NoteAIConfig).where(NoteAIConfig.user_id == user_id))


def cipher(user_id):
    key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=("hustudy-note-ai-v1:" + user_id).encode(),
    ).derive(get_settings().jwt_secret.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def effective_settings(db, user_id):
    raise ProviderFailure("DISABLED", DISABLED_REASON)


def config_response(db, user_id):
    row = owned_config(db, user_id)
    return {
        "provider": "zhipu",
        "model": row.model if row else get_settings().llm_model,
        "configured": False,
        "has_personal_key": bool(row and row.encrypted_key),
        "revision": row.revision if row else 0,
        "source": "personal" if row else "none",
        "reason": DISABLED_REASON,
        "endpoint": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    }
