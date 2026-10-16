from .common import SearchExcerpt
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CitationCreate(BaseModel):
    version_id: str
    chunk_id: str
    quote: str = Field(min_length=1)
    note_id: Optional[str] = None


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str = ""
    course_id: Optional[str] = None
    tags: List[str] = []
    citations: List[CitationCreate] = Field(default_factory=list, max_length=50)


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=240)
    content: Optional[str] = None
    course_id: Optional[str] = None
    revision: int = Field(ge=1)


class NoteResponse(BaseModel):
    id: str
    user_id: str
    course_id: Optional[str]
    title: str
    content: str
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
