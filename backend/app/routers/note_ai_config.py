from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import NoteAIConfig, User
from ..services.note_ai_config import DISABLED_REASON, config_response, owned_config
from ..services.note_folders import lock_owner

router = APIRouter(prefix="/api/v1/note-ai", tags=["note-ai-config"])


class ConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    revision: int = Field(ge=0, strict=True)
    model: Literal["glm-4.7-flash", "glm-5.3-flash"]
    api_key: SecretStr | None = None


@router.get("/config")
def get(
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    return config_response(db, user.id)


@router.put("/config")
def put(
    payload: ConfigUpdate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    raise HTTPException(410, DISABLED_REASON)


@router.delete("/config")
def remove(
    response: Response,
    revision: int = Query(ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    lock_owner(db, user.id)
    row = owned_config(db, user.id)
    if revision != (row.revision if row else 0):
        raise HTTPException(409, "AI配置已变化，请重新读取后清除")
    if not row:
        row = NoteAIConfig(user_id=user.id, revision=0, model="glm-4.7-flash")
        db.add(row)
    row.encrypted_key = None
    row.revision += 1
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return config_response(db, user.id)
