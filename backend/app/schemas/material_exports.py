from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from .material import JobResponse


class MaterialExportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID


class MaterialExportResponse(BaseModel):
    id: str
    course_id: str
    created_at: datetime
    snapshot_at: datetime | None
    sha256: str | None
    size_bytes: int
    counts: dict[str, int]
    availability: str
    job: JobResponse
