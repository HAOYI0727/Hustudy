from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class TrashItem(BaseModel):
    id: UUID
    revision: int = Field(ge=1)


class TrashBatch(BaseModel):
    action: Literal["trash", "restore", "purge"]
    notes: list[TrashItem] = Field(min_length=1, max_length=200)
    fallback_course_id: UUID | None = None

    @model_validator(mode="after")
    def unique(self):
        if len({n.id for n in self.notes}) != len(self.notes):
            raise ValueError("不能重复选择同一笔记")
        return self


class TrashPolicyUpdate(BaseModel):
    retention_days: int | None = Field(ge=1, le=365, strict=True)
    revision: int = Field(ge=0)


class TrashPolicyResponse(BaseModel):
    retention_days: int | None
    revision: int


class TrashEntry(BaseModel):
    id: str
    title: str
    course_id: str | None
    course_name: str
    folder_id: str | None
    tags: list[str]
    revision: int
    deleted_at: datetime
    purge_after: datetime | None
    restore_requires_course: bool


class TrashPage(BaseModel):
    items: list[TrashEntry]
    total: int
    snapshot: str


class EmptyTrash(BaseModel):
    snapshot: str = Field(pattern=r"^[0-9a-f]{64}$")
