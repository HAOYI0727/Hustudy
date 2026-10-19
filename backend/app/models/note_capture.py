"""Disposable recognition drafts; confirmed notes use the normal Note model."""

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, OwnedResourceMixin


class NoteCapture(Base, OwnedResourceMixin):
    __tablename__ = "note_captures"
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id", ondelete="CASCADE")
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("processing_jobs.id", ondelete="CASCADE"), unique=True
    )
    filename: Mapped[str] = mapped_column(String(240))
    source_path: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_request: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_result: Mapped[dict] = mapped_column(JSON, default=dict)
