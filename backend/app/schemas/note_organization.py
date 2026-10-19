from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from .notes import NoteTags


def folder_name(value):
    if not isinstance(value, str):
        raise ValueError("文件夹名称必须是文本")
    value = value.strip()
    if (
        not 1 <= len(value) <= 64
        or value in {".", ".."}
        or any(c in "/\\" or ord(c) < 32 or ord(c) == 127 for c in value)
    ):
        raise ValueError("文件夹名称须为1–64字，不含路径分隔符或控制字符")
    return value


class FolderCreate(BaseModel):
    course_id: str
    parent_id: str | None = None
    name: str
    _name = field_validator("name", mode="before")(folder_name)


class FolderUpdate(BaseModel):
    revision: int = Field(ge=1)
    name: str | None = None
    parent_id: str | None = None
    _name = field_validator("name", mode="before")(folder_name)


class FolderResponse(FolderCreate):
    id: str
    user_id: str
    revision: int
    created_at: datetime
    updated_at: datetime


class NoteRevision(BaseModel):
    id: str
    revision: int = Field(ge=1)


class NoteBatch(BaseModel):
    notes: list[NoteRevision] = Field(min_length=1, max_length=200)
    add_tags: NoteTags = Field(default_factory=list)
    remove_tags: NoteTags = Field(default_factory=list)
    folder_id: str | None = None

    @model_validator(mode="after")
    def valid_operation(self):
        if len({n.id for n in self.notes}) != len(self.notes):
            raise ValueError("批量笔记不能重复")
        if (
            not self.add_tags
            and not self.remove_tags
            and "folder_id" not in self.model_fields_set
        ):
            raise ValueError("请选择标签或移动操作")
        return self
