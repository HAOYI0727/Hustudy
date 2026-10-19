from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .material import JobResponse


class NoteExportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    note_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=2000)
    include_images: bool = True

    @field_validator("note_ids")
    @classmethod
    def unique_notes(cls, value):
        if value is not None and len(set(value)) != len(value):
            raise ValueError("请勿重复选择同一篇笔记")
        return value


class NoteExportResponse(BaseModel):
    layout: str
    filename: str
    id: str
    created_at: datetime
    snapshot_at: datetime | None
    sha256: str | None
    size_bytes: int
    counts: dict[str, int]
    availability: str
    job: JobResponse
