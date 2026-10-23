"""Small read models shared by the four course workspace adapters."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from .exams import ReviewTaskResponse

WorkspaceDomain = Literal["materials", "notes", "study", "practice"]
RecordKind = Literal["all", "material", "note", "qa", "report", "attempt", "mistake"]


class WorkspaceItem(BaseModel):
    id: str
    title: str
    kind: Literal["material", "note", "qa", "report", "attempt", "mistake"]
    status: str
    updated_at: datetime
    document_id: str | None = None
    version_id: str | None = None


class WorkspaceSection(BaseModel):
    course_id: str
    domain: WorkspaceDomain
    counts: dict[str, int]
    recent: list[WorkspaceItem] = Field(max_length=6)
    checked_at: datetime


class LearningRecordPage(BaseModel):
    course_id: str
    items: list[WorkspaceItem] = Field(max_length=50)
    total: int
    counts: dict[str, int]
    offset: int
    limit: int
    checked_at: datetime


LearningLinkKind = Literal["all", "note", "qa", "report", "topic", "mistake"]


class SourceReviewSummary(BaseModel):
    mastered: bool | None
    pending_count: int
    due_count: int
    next_due_date: str | None


class LearningLinkItem(BaseModel):
    id: str
    title: str
    kind: Literal["note", "qa", "report", "topic", "mistake"]
    status: str
    updated_at: datetime
    source_relation: Literal["citation", "version"] | None = None
    review: SourceReviewSummary | None = None


class LearningLinkPage(BaseModel):
    course_id: str
    document_id: str
    version_id: str
    chunk_id: str | None
    items: list[LearningLinkItem] = Field(max_length=50)
    counts: dict[str, int]
    total: int
    offset: int
    limit: int
    checked_at: datetime
    today: str
    timezone: str


class MistakeSource(BaseModel):
    version_id: str
    chunk_id: str = ""
    document_id: str | None = None
    title: str
    locator: str = ""
    availability: Literal["active", "unavailable"]


class MistakeSources(BaseModel):
    course_id: str
    items: list[MistakeSource] = Field(max_length=50)


class ReviewSchedulePage(BaseModel):
    items: list[ReviewTaskResponse] = Field(max_length=100)
    total: int
    offset: int
    limit: int
    today: str
    timezone: str
    course_id: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)
