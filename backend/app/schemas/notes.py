from .common import SearchExcerpt
from datetime import datetime
from uuid import UUID
from typing import Annotated, List, Optional
from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    AfterValidator,
    field_validator,
)


def normalize_tags(tags: list[str]) -> list[str]:
    if any(any(ord(char) < 32 or ord(char) == 127 for char in tag) for tag in tags):
        raise ValueError("标签不能包含控制字符")
    return list(dict.fromkeys(tags))


NoteTag = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)
]
NoteTags = Annotated[
    list[NoteTag], Field(max_length=12), AfterValidator(normalize_tags)
]


class CitationCreate(BaseModel):
    version_id: str
    chunk_id: str
    quote: str = Field(min_length=1)
    note_id: Optional[str] = None


class NoteCreate(BaseModel):
    request_id: UUID | None = None
    title: str = Field(min_length=1, max_length=240)
    content: str = ""
    course_id: Optional[str] = None
    folder_id: str | None = None
    tags: NoteTags = Field(default_factory=list)
    citations: List[CitationCreate] = Field(default_factory=list, max_length=50)

    @field_validator("citations")
    @classmethod
    def unique_citations(cls, values):
        seen = set()
        unique = []
        for citation in values:
            key = (citation.version_id, citation.chunk_id, citation.quote)
            if key not in seen:
                unique.append(citation)
                seen.add(key)
        return unique


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=240)
    content: Optional[str] = None
    course_id: Optional[str] = None
    folder_id: str | None = None
    revision: int = Field(ge=1)
    tags: NoteTags | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def reject_null_tags(cls, value):
        if value is None:
            raise ValueError("标签不能为null；清空请传[]")
        return value


class NoteResponse(BaseModel):
    id: str
    user_id: str
    course_id: Optional[str]
    folder_id: str | None = None
    title: str
    content: str
    tags: list[str]
    revision: int
    created_at: datetime
    updated_at: datetime


class CitationResponse(BaseModel):
    id: str
    note_id: Optional[str]
    version_id: str
    chunk_id: str
    locator_type: str
    locator_value: str
    quote: str
    availability: str
    source_kind: str = "extracted"
    document_id: str | None = None
    document_name: str | None = None
    version_no: int | None = None


class AssetResponse(BaseModel):
    id: str
    name: str
    tags: list[str]
    revision: int
    course_id: Optional[str]
    original_filename: str
    mime_type: str
    size_bytes: int
    alt: str
    deleted: bool

    source_version_id: Optional[str] = None
    source_page: Optional[int] = None
    source_locator_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AssetMetadataResponse(AssetResponse):
    source_document_id: Optional[str] = None
    source_document_name: Optional[str] = None
    source_version_no: Optional[int] = None
    source_availability: str = "active"
    sha256: str
    created_at: datetime


class NoteSearchItem(BaseModel):
    id: str
    title: str
    excerpt: SearchExcerpt
    updated_at: datetime


class NoteSearchPage(BaseModel):
    items: list[NoteSearchItem]
    total: int
    offset: int
    limit: int
