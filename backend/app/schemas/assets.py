"""M1 image organization contract; NoteGraph keeps using compatible AssetResponse."""

from typing import Annotated
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from .notes import AssetResponse

Tag = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)
]


class AssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(strict=True, ge=1)
    name: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
        ]
        | None
    ) = None
    alt: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None
    tags: list[Tag] | None = Field(default=None, max_length=12)

    @field_validator("name", "alt", "tags", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("整理字段不能为 null；清空说明/标签请传空字符串/[]")
        return value

    @field_validator("tags")
    @classmethod
    def deduplicate(cls, value):
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set - {"revision"}:
            raise ValueError("请提供至少一个整理字段")
        return self


class AssetPageResponse(BaseModel):
    items: list[AssetResponse]
    total: int
    offset: int
    limit: int
    tags: list[str]
