"""M3 read-only adapter for explicitly selected personal supplements."""

import hashlib
from fastapi import HTTPException
from sqlalchemy import select
from ..models import Note


def selected_notes(db, user_id, course_id, ids):
    notes = []
    for identity in ids:
        note = db.scalar(
            select(Note)
            .where(
                Note.id == str(identity),
                Note.user_id == user_id,
                Note.course_id == course_id,
                Note.deleted.is_(False),
            )
            .execution_options(populate_existing=True)
        )
        if note is None:
            raise HTTPException(404, "补充笔记不存在或不属于当前课程")
        if not note.content.strip():
            raise HTTPException(422, "补充笔记正文为空，请取消选择")
        notes.append(
            dict(
                id=note.id,
                title=note.title,
                revision=note.revision,
                content=note.content,
                sha256=hashlib.sha256(note.content.encode()).hexdigest(),
                origin="user_confirmed_supplement",
            )
        )
    if sum(len(n["content"]) for n in notes) > 12000:
        raise HTTPException(
            422, "补充笔记正文合计超过12000字符，请减少选择；未截断发送"
        )
    return notes
