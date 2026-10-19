"""Private account credentials, intentionally excluded from portable backups."""

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, OwnedResourceMixin


class NoteAIConfig(Base, OwnedResourceMixin):
    __tablename__ = "note_ai_configs"
    __table_args__ = (UniqueConstraint("user_id"),)
    model: Mapped[str] = mapped_column(String(64), default="glm-4.7-flash")
    encrypted_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
