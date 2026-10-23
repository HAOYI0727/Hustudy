"""Read-only latest-version checks; task controls retain their original contract."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

HealthIssue = Literal[
    "all", "attention", "text", "parse", "index", "preview", "processing"
]


class HealthJob(BaseModel):
    id: str
    type: Literal["PARSE", "INDEX", "PREVIEW"]
    status: str
    attempt_count: int
    max_attempts: int
    error: str | None


class MaterialHealthItem(BaseModel):
    document_id: str
    name: str
    updated_at: datetime
    version_id: str
    version_no: int
    parse_status: str
    index_status: str
    preview_status: str
    has_text: bool
    issues: list[str]
    jobs: list[HealthJob] = Field(max_length=3)


class MaterialHealthPage(BaseModel):
    course_id: str
    items: list[MaterialHealthItem] = Field(max_length=50)
    counts: dict[str, int]
    total: int
    offset: int
    limit: int
    checked_at: datetime
