from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from .base import Base, OwnedResourceMixin
class Course(Base, OwnedResourceMixin):
    __tablename__ = "courses"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
