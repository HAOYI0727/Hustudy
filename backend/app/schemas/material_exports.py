from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .material import JobResponse


class MaterialExportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    document_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("document_ids")
    @classmethod
    def unique_documents(cls, value):
        if value is not None and len(set(value)) != len(value):
            raise ValueError("所选资料不能重复")
        return value


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
    scope: Literal["course", "selected"] = "course"
    selected_count: int = 0
