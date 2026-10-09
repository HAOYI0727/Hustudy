from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..core.config import get_settings
from ..core.database import get_db
from ..schemas.common import HealthResponse
router = APIRouter(tags=["system"])
@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ok", service="hustudy-api", environment=get_settings().env, database="ok")
