from datetime import datetime
from typing import Annotated
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Category = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
]
Tag = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)
]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


class CourseFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("tags", check_fields=False)
    @classmethod
    def deduplicate(cls, value):
        return list(dict.fromkeys(value))

    @field_validator("description", check_fields=False)
    @classmethod
    def empty_description(cls, value):
        return value or None


class CourseCreate(CourseFields):
    name: Name
    description: Description | None = None
    category: Category = "未分类"
    tags: list[Tag] = Field(default_factory=list, max_length=12)


class CourseUpdate(CourseFields):
    revision: int = Field(strict=True, ge=1)
    name: Name | None = None
    description: Description | None = None
    category: Category | None = None
    tags: list[Tag] | None = Field(default=None, max_length=12)

    @field_validator("name", "category", "tags", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("名称、分类、标签不能为 null")
        return value

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set - {"revision"}:
            raise ValueError("请提供至少一个整理字段")
        return self


class CourseResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None
    category: str
    tags: list[str]
    revision: int
    created_at: datetime
    updated_at: datetime


class CourseDeletionPreview(BaseModel):
    course: CourseResponse
    counts: dict[str, int]
