from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, OwnedResourceMixin, UTCDateTime


class AIResult(Base, OwnedResourceMixin):
    __tablename__ = "ai_results"
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    model_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    prompt_version: Mapped[str] = mapped_column(
        String(40), default="mock-v1", nullable=False
    )


class RemoteQuery(Base, OwnedResourceMixin):
    __tablename__ = "remote_queries"
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list] = mapped_column(JSON, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    consented_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("processing_jobs.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    result_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_results.id", ondelete="SET NULL"), nullable=True
    )
