"""Private package previews and durable, atomic import receipts."""

from datetime import datetime
from sqlalchemy import JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, OwnedResourceMixin, UTCDateTime


class PackagePreview(Base, OwnedResourceMixin):
    __tablename__ = "package_previews"

    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, index=True
    )


class PackageImport(Base, OwnedResourceMixin):
    __tablename__ = "package_imports"
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_package_import_request"),
    )

    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
