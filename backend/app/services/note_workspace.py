"""M3-owned bounded metadata adapter; notes' contents stay in the editor."""

from sqlalchemy import select, func
from ..models import Note, Citation
from ..repositories.source_links import valid_reference
from .workspace_record_query import metadata_query


def records(user_id, course_id):
    return metadata_query(
        Note.id,
        Note.title,
        "note",
        "SAVED",
        Note.updated_at,
    ).where(
        Note.user_id == user_id,
        Note.course_id == course_id,
        Note.deleted.is_(False),
    )


def linked_records(user_id, course_id, version_id, chunk_id=None):
    reference = (
        select(Citation.id)
        .where(
            Citation.note_id == Note.id,
            Citation.user_id == user_id,
            Citation.version_id == version_id,
            Citation.availability == "active",
            valid_reference(
                user_id, version_id, Citation.chunk_id, Citation.quote, chunk_id
            ),
        )
        .exists()
    )
    return records(user_id, course_id).where(reference)


def summary(db, user, course_id):
    scope = (
        Note.user_id == user.id,
        Note.course_id == course_id,
        Note.deleted.is_(False),
    )
    count = db.scalar(select(func.count()).select_from(Note).where(*scope)) or 0
    rows = db.execute(
        select(Note.id, Note.title, Note.updated_at)
        .where(*scope)
        .order_by(Note.updated_at.desc(), Note.id)
        .limit(6)
    ).all()
    return {
        "counts": {"total": count},
        "recent": [
            dict(
                id=row.id,
                title=row.title,
                kind="note",
                status="SAVED",
                updated_at=row.updated_at,
            )
            for row in rows
        ],
    }
