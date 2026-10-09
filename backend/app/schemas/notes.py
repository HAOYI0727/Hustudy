from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str = ""
    course_id: Optional[str] = None
    tags: List[str] = []


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


class CitationCreate(BaseModel):
    version_id: str
    chunk_id: str
    quote: str = Field(min_length=1)
    note_id: Optional[str] = None


class CitationResponse(BaseModel):
    id: str
    note_id: Optional[str]
    version_id: str
    chunk_id: str
    locator_type: str
    locator_value: str
    quote: str
    availability: str


class AssetResponse(BaseModel):
    id: str
    course_id: Optional[str]
    original_filename: str
    mime_type: str
    size_bytes: int
    alt: str
    deleted: bool
