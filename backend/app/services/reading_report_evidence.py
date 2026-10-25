"""M1 reading-mark boundary for M2. No reader or persisted marks exist yet.

M1 can install its read-only query during application startup in each API/worker
process. Nothing in the report request can install a reader or supply marks.
"""

from collections.abc import Callable
from typing import Literal
from uuid import UUID
from fastapi import HTTPException
from pydantic import Field, ValidationError
from ..schemas.ai_supplements import TeacherMark
from ..repositories.materials import checked_chunk


class ReadingTeacherMark(TeacherMark):
    id: UUID
    user_id: UUID
    course_id: UUID
    revision: int = Field(ge=1, strict=True)
    status: Literal["active"]
    mark_type: Literal["teacher_emphasis"]


_reader: Callable | None = None


def install_reader(reader: Callable | None):
    """Code integration hook for M1, not an API or a user-configurable switch."""
    global _reader
    _reader = reader


def teacher_emphases(db, user_id, course_id, sources):
    if _reader is None:
        return []
    result, seen = [], set()
    for index, raw in enumerate(_reader(db, user_id, course_id, sources)):
        if index >= 200:
            raise HTTPException(422, "阅读标记超过200条，请缩小报告范围")
        try:
            mark = ReadingTeacherMark.model_validate(raw)
        except ValidationError:
            # Unconfirmed, withdrawn, unsupported and legacy records carry no fact.
            continue
        data = mark.model_dump(mode="json")
        if (
            data["user_id"] != user_id
            or data["course_id"] != course_id
            or data["id"] in seen
        ):
            continue
        if not any(
            s["version_id"] == data["version_id"]
            and s["source_id"] == data["chunk_id"]
            and data["quote"] in s["text"]
            for s in sources
        ):
            continue
        checked_chunk(
            db, data["version_id"], data["chunk_id"], data["quote"], user_id, course_id
        )
        seen.add(data["id"])
        result.append(data)
    return sorted(result, key=lambda item: item["id"])
