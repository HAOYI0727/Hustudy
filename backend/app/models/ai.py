from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, OwnedResourceMixin


class AIResult(Base, OwnedResourceMixin):
    __tablename__ = "ai_results"
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    model_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), default="mock-v1", nullable=False)
