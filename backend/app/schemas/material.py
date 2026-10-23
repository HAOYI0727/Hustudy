from .common import SearchExcerpt
from datetime import datetime
from uuid import UUID
from typing import Optional, Annotated, Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    AwareDatetime,
    model_validator,
)


class DocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_updated_at: AwareDatetime | None = None
    name: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)
        ]
        | None
    ) = None
    category: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
        ]
        | None
    ) = None
    tags: (
        list[
            Annotated[
                str,
                StringConstraints(strip_whitespace=True, min_length=1, max_length=32),
            ]
        ]
        | None
    ) = Field(default=None, max_length=12)

    @field_validator("name", "category", "tags", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("整理字段不能为 null；清空标签请传 []")
        return value

    @field_validator("tags")
    @classmethod
    def unique_tags(cls, value):
        return list(dict.fromkeys(value))


class DocumentSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    expected_updated_at: AwareDatetime


class DocumentOrganize(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[DocumentSelection] = Field(min_length=1, max_length=100)
    category: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
        ]
        | None
    ) = None
    tags_mode: Literal["keep", "add", "remove", "replace", "clear"] = "keep"
    tags: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)
        ]
    ] = Field(default_factory=list, max_length=12)

    @field_validator("category", mode="before")
    @classmethod
    def reject_null_category(cls, value):
        if value is None:
            raise ValueError("分类不能为null，清空请使用未分类")
        return value

    @model_validator(mode="after")
    def check_operation(self):
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("所选资料不能重复")
        self.tags = list(dict.fromkeys(self.tags))
        if self.tags_mode in {"keep", "clear"} and self.tags:
            raise ValueError("保留或清空标签时不能提供标签列表")
        if self.tags_mode in {"add", "remove", "replace"} and not self.tags:
            raise ValueError("请提供需要整理的标签")
        if self.category is None and self.tags_mode == "keep":
            raise ValueError("请至少选择一项整理操作")
        return self


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    course_id: str
    name: str
    category: str
    tags: list[str]
    updated_at: datetime


class DocumentOrganizeResult(BaseModel):
    items: list[DocumentMetadata]
    changed: int


class DocumentResponse(BaseModel):
    id: str
    course_id: str
    name: str
    category: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
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
    preview_error: Optional[str] = None
    latest_version_no: Optional[int] = None
    confirmed_transcript_count: int = 0


class VersionResponse(BaseModel):
    id: str
    document_id: str
    version_no: int
    parse_status: str
    preview_status: str
    index_status: str
    parse_error: Optional[str]
    preview_error: Optional[str] = None
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    tokenizer_version: str
    created_at: datetime
    updated_at: datetime


class ChunkResponse(BaseModel):
    source_kind: str = "extracted"
    transcript_id: Optional[str] = None
    transcript_status: Optional[str] = None
    confirmed_at: Optional[datetime] = None
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
    attempt_count: int
    max_attempts: int
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    version_no: Optional[int] = None


class ReindexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID


class DocumentPage(BaseModel):
    items: list[DocumentResponse]
    total: int
    offset: int
    limit: int
    stats: dict[str, int]
    categories: list[str]
    tags: list[str]


class JobPage(BaseModel):
    items: list[JobResponse]
    total: int
    offset: int
    limit: int
    pending_count: int


class SearchResponse(BaseModel):
    source_kind: str = "extracted"
    transcript_id: Optional[str] = None
    chunk_id: str
    version_id: str
    document_id: str
    document_name: str
    category: str
    tags: list[str]
    version_no: int
    locator_type: str
    locator_value: str
    text: str
    score: float


class MaterialReferenceResponse(BaseModel):
    citation_id: str
    note_id: str
    note_title: str
    chunk_id: str
    quote: str
    locator_type: str
    locator_value: str


class ReferenceNote(BaseModel):
    note_id: str
    note_title: str
    note_course_id: str | None
    updated_at: datetime
    citation_count: int = Field(ge=1)
    citation_id: str
    chunk_id: str
    locator_type: str
    locator_value: str
    quote_excerpt: str = Field(max_length=180)


class ReferenceNotePage(BaseModel):
    course_id: str
    document_id: str
    version_id: str
    chunk_id: str | None
    items: list[ReferenceNote] = Field(max_length=50)
    total: int
    offset: int
    limit: int
    checked_at: datetime


class PreviewCapabilities(BaseModel):
    native_pdf: bool
    office_available: bool
    office_status: str
    message: str
    installation_url: str


class SearchPageItem(BaseModel):
    source_kind: str
    transcript_id: str | None
    chunk_id: str
    version_id: str
    document_id: str
    document_name: str
    category: str
    tags: list[str]
    version_no: int
    locator_type: str
    locator_value: str
    score: float
    excerpt: SearchExcerpt


class SearchPage(BaseModel):
    items: list[SearchPageItem]
    total: int
    offset: int
    limit: int
