from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..core.config import get_settings
from ..core.database import get_db
from ..schemas.common import HealthResponse
from ..schemas.common import ProcessingStatusResponse
from ..dependencies import current_user
from ..models import User
from ..models.base import utc_now
from ..services.worker_runtime import processing_status

router = APIRouter(tags=["system"])


@router.get("/api/v1/processing/status", response_model=ProcessingStatusResponse)
def processing_service(_user: User = Depends(current_user)):
    state = processing_status()
    messages = {
        "ready": "资料处理服务已连接，上传后会继续解析与索引。",
        "starting": "资料处理服务正在连接，已保存的原件将等待处理。",
        "unavailable": "资料处理服务暂不可用，原件仍可上传保存；处理恢复后继续，无需重复上传。",
    }
    return ProcessingStatusResponse(
        state=state, checked_at=utc_now().isoformat(), message=messages[state]
    )


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(
        status="ok",
        service="hustudy-api",
        environment=get_settings().env,
        database="ok",
    )
