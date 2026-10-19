"""Disposable M3 export records, excluded from account business backups."""

from datetime import datetime
from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, OwnedResourceMixin, UTCDateTime


class NoteExport(Base, OwnedResourceMixin):
    __tablename__ = "note_exports"
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("processing_jobs.id", ondelete="CASCADE"), unique=True
    )
    zip_path: Mapped[str | None] = mapped_column(String(500))
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sources_json: Mapped[dict] = mapped_column(JSON, default=dict)
    counts_json: Mapped[dict] = mapped_column(JSON, default=dict)
    snapshot_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
