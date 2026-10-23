"""M3 metadata adapters: the editor alone reads full note bodies."""

from fastapi import HTTPException
from sqlalchemy import select, func, or_
from ..core.database import begin_read_snapshot
from ..models import Note, Course, NoteLink
from .courses import owned_course
from .note_filters import text_matches, tag_matches


def accessible(user_id):
    return (
        Note.user_id == user_id,
        Note.deleted.is_(False),
        or_(
            Note.course_id.is_(None),
            Note.course_id.in_(
                select(Course.id).where(
                    Course.user_id == user_id, Course.deleted_at.is_(None)
                )
            ),
        ),
    )


def columns():
    return (
        Note.id,
        Note.course_id,
        Note.folder_id,
        Note.title,
        Note.tags,
        Note.revision,
        Note.updated_at,
    )


def catalog(db, user_id, offset, limit):
    begin_read_snapshot(db)
    scope = accessible(user_id)
    return {
        "items": db.execute(
            select(*columns())
            .where(*scope)
            .order_by(Note.id)
            .offset(offset)
            .limit(limit)
        ).all(),
        "total": db.scalar(select(func.count()).select_from(Note).where(*scope)) or 0,
        "offset": offset,
        "limit": limit,
    }


def matches(db, user_id, course_id, query, tag):
    begin_read_snapshot(db)
    owned_course(db, user_id, course_id)
    scope = [*accessible(user_id), Note.course_id == course_id]
    if query.strip():
        scope.append(text_matches(query.strip()))
    if tag:
        scope.append(tag_matches(tag.strip()))
    ids = list(db.scalars(select(Note.id).where(*scope).order_by(Note.id).limit(20001)))
    if len(ids) > 20000:
        raise HTTPException(422, "匹配超过20000篇，请缩小关键词或标签范围")
    return {"ids": ids}


def backlinks(db, user_id, note_id):
    begin_read_snapshot(db)
    if not db.scalar(select(Note.id).where(*accessible(user_id), Note.id == note_id)):
        raise HTTPException(404, "笔记不存在")
    scope = select(NoteLink.source_note_id).where(
        NoteLink.user_id == user_id, NoteLink.target_note_id == note_id
    )
    return db.execute(
        select(*columns())
        .where(*accessible(user_id), Note.id.in_(scope))
        .order_by(Note.updated_at.desc(), Note.id)
    ).all()
