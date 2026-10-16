from datetime import datetime
from sqlalchemy import String, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from .base import Base, OwnedResourceMixin, UTCDateTime


class Course(Base, OwnedResourceMixin):
    __tablename__ = "courses"
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(64), nullable=False, default="未分类", server_default="未分类"
    )
    tags: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
