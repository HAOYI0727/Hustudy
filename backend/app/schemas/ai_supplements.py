"""User-confirmed M2 inputs, distinct from model output and original citations."""

from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TeacherMark(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["key", "difficult", "exam"] = "key"
    version_id: UUID
    chunk_id: UUID
    quote: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=1000)
    confirmed: bool = Field(strict=True)

    @model_validator(mode="after")
    def explicit(self):
        if not self.confirmed:
            raise ValueError("教师强调须本人确认记录")
        return self


class SupplementSelection(BaseModel):
    note_ids: list[UUID] = Field(default_factory=list, max_length=5)
    notes_confirmed: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def confirmed_notes(self):
        if len(set(self.note_ids)) != len(self.note_ids):
            raise ValueError("笔记不能重复选择")
        if self.note_ids and not self.notes_confirmed:
            raise ValueError("须确认已核对选中笔记，AI草稿也须本人检查")
        return self
