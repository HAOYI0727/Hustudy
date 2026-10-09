from typing import Any, List, Optional
from pydantic import BaseModel, Field


class AIQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    mode: str = Field(default="demo", pattern="^(demo|real)$")
    confirm_remote_send: bool = False


class AIResultResponse(BaseModel):
    id: str
    course_id: str
    query: str
    status: str
    model_mode: str
    result: dict[str, Any]


class StudyReportRequest(BaseModel):
    scope_version_ids: List[str] = []
    mode: str = Field(default="demo", pattern="^(demo|real)$")
    confirm_remote_send: bool = False


class StudyReportResponse(BaseModel):
    id: str
    status: str
    model_mode: str
    report: dict[str, Any]
