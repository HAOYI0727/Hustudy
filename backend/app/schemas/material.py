from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    course_id: str
    name: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    deleted_at: Optional[datetime]
    latest_version_id: Optional[str] = None
    parse_status: Optional[str] = None
    preview_status: Optional[str] = None
    index_status: Optional[str] = None
    parse_error: Optional[str] = None


class VersionResponse(BaseModel):
    id: str
    document_id: str
    version_no: int
    parse_status: str
    preview_status: str
    index_status: str
    parse_error: Optional[str]


class ChunkResponse(BaseModel):
    id: str
    version_id: str
    ordinal: int
    locator_type: str
    locator_value: str
    text: str
    start_offset: int
    end_offset: int


class JobResponse(BaseModel):
    id: str
    type: str
    status: str
    resource_id: Optional[str]
    progress: int
    error: Optional[str]


class SearchResponse(BaseModel):
    chunk_id: str
    version_id: str
    document_id: str
    document_name: str
    locator_type: str
    locator_value: str
    text: str
    score: float
