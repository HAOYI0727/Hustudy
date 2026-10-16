from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index, JSON, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, OwnedResourceMixin, UTCDateTime


class Document(Base, OwnedResourceMixin):
    __tablename__ = "documents"
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    category: Mapped[str] = mapped_column(
        String(40),
        default="未分类",
        server_default="未分类",
        nullable=False,
        index=True,
    )
    tags: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default="[]", nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class DocumentVersion(Base, OwnedResourceMixin):
    __tablename__ = "document_versions"
    __table_args__ = (
        Index("uq_document_version_number", "document_id", "version_no", unique=True),
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    parse_status: Mapped[str] = mapped_column(
        String(32), default="QUEUED", nullable=False
    )
    preview_status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False
    )
    index_status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False
    )
    parse_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)

    original_filename: Mapped[str] = mapped_column(
        String(255), default="", nullable=False
    )
    mime_type: Mapped[str] = mapped_column(
        String(120), default="application/octet-stream", nullable=False
    )
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    preview_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preview_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tokenizer_version: Mapped[str] = mapped_column(
        String(40), default="zh-bigram-v1", nullable=False
    )


class DocumentChunk(Base, OwnedResourceMixin):
    __tablename__ = "document_chunks"
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    locator_type: Mapped[str] = mapped_column(String(32), nullable=False)
    locator_value: Mapped[str] = mapped_column(String(120), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_kind: Mapped[str] = mapped_column(
        String(32), default="extracted", server_default="extracted", nullable=False
    )


class ManualTranscript(Base, OwnedResourceMixin):
    __tablename__ = "manual_transcripts"
    __table_args__ = (
        Index(
            "uq_manual_current_page",
            "version_id",
            "page",
            unique=True,
            sqlite_where=text("status = 'CONFIRMED'"),
        ),
    )
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)
    supersedes_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("manual_transcripts.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    confirmed_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime(), nullable=True
    )


class ProcessingJob(Base, OwnedResourceMixin):
    __tablename__ = "processing_jobs"
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    lease_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_token: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class MaterialExport(Base, OwnedResourceMixin):
    __tablename__ = "material_exports"
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    zip_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    counts_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    snapshot_at: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime(), nullable=True
    )
