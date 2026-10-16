from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, OwnedResourceMixin


class Note(Base, OwnedResourceMixin):
    __tablename__ = "notes"
    course_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    deleted: Mapped[bool] = mapped_column(default=False, nullable=False)


class NoteLink(Base, OwnedResourceMixin):
    __tablename__ = "note_links"
    source_note_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_note_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(240), nullable=False)


class Citation(Base, OwnedResourceMixin):
    __tablename__ = "citations"
    note_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("notes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    locator_type: Mapped[str] = mapped_column(String(32), nullable=False)
    locator_value: Mapped[str] = mapped_column(String(120), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    quote_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_kind: Mapped[str] = mapped_column(
        String(32), default="extracted", server_default="extracted", nullable=False
    )
    availability: Mapped[str] = mapped_column(
        String(24), default="active", nullable=False
    )


class Asset(Base, OwnedResourceMixin):
    __tablename__ = "assets"
    course_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), server_default="", nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default="[]", nullable=False
    )
    revision: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    alt: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    source_version_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_locator_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )
    deleted: Mapped[bool] = mapped_column(default=False, nullable=False)


class AssetReference(Base, OwnedResourceMixin):
    __tablename__ = "asset_references"
    note_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
