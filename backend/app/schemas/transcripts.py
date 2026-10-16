from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

BodyText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)
]


class TranscriptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(ge=1, strict=True)
    text: BodyText
    supersedes_id: str | None = None


class TranscriptRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1, strict=True)


class TranscriptUpdate(TranscriptRevision):
    text: BodyText


class TranscriptResponse(BaseModel):
    id: str
    version_id: str
    page: int
    text: str
    text_hash: str
    revision: int
    status: Literal["DRAFT", "CONFIRMED", "SUPERSEDED", "WITHDRAWN"]
    supersedes_id: str | None
    chunk_id: str | None
    confirmed_by: str | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
