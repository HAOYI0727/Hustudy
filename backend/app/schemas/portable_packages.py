"""Explicit package selection and retry identity; unknown fields are rejected."""

from typing import Annotated, Literal
from uuid import UUID
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Selection = dict[str, list[UUID]]
Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class Selected(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selection: Selection

    @field_validator("selection")
    @classmethod
    def selected_budget(cls, value):
        if len(value) > 10 or sum(map(len, value.values())) > 3000:
            raise ValueError("所选对象数量超过预算")
        if any(len(ids) != len(set(ids)) for ids in value.values()):
            raise ValueError("所选对象不能重复")
        return value


class Confirmed(Selected):
    expected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class PackageExport(Confirmed):
    course_id: UUID
    kind: Literal["course", "folder"] = "course"
    folder_id: UUID | None = None

    @model_validator(mode="after")
    def folder_scope(self):
        if self.kind == "course" and self.folder_id is not None:
            raise ValueError("课程包不能同时指定笔记文件夹")
        return self


class PackageSelection(Selected):
    preview_id: UUID | None = None
    course_id: UUID | None = None
    kind: Literal["course", "folder"] = "course"
    folder_id: UUID | None = None
    target_course_id: UUID | None = None
    parent_folder_id: UUID | None = None
    title: Title | None = None

    @model_validator(mode="after")
    def one_source(self):
        if (self.preview_id is None) == (self.course_id is None):
            raise ValueError("请选择一个包来源")
        if self.preview_id is not None and self.folder_id is not None:
            raise ValueError("已上传包不能再指定来源文件夹")
        if self.preview_id is None and any(
            value is not None
            for value in (self.target_course_id, self.parent_folder_id, self.title)
        ):
            raise ValueError("导出范围核对不能设置导入目标")
        if self.kind == "course" and self.folder_id is not None:
            raise ValueError("课程包不能同时指定笔记文件夹")
        return self


class PackageImportRequest(Confirmed):
    preview_id: UUID
    request_id: UUID
    target_course_id: UUID | None = None
    parent_folder_id: UUID | None = None
    title: Title | None = None

    @field_validator("title")
    @classmethod
    def title_controls(cls, value):
        if value and any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("名称不能包含控制字符")
        return value
