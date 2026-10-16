from sqlalchemy import ForeignKey, String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, OwnedResourceMixin


class AccountArchive(Base, OwnedResourceMixin):
    __tablename__ = "account_archives"
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    counts: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sources: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
