"""M3 course removal interface; preserve other notes and unavailable citations."""

from sqlalchemy import select, update, func
from ..models import Note, Citation
from ..models.base import utc_now
from datetime import timedelta
from .note_trash import retention


def course_note_counts(db, user_id, course_id):
    return {
        "notes": db.scalar(
            select(func.count())
            .select_from(Note)
            .where(
                Note.user_id == user_id,
                Note.course_id == course_id,
                Note.deleted.is_(False),
            )
        )
    }


def retire_course_notes(db, user_id, course_id):
    now, days = utc_now(), retention(db, user_id)
    db.execute(
        update(Note)
        .where(
            Note.user_id == user_id,
            Note.course_id == course_id,
            Note.deleted.is_(False),
        )
        .values(
            deleted=True,
            revision=Note.revision + 1,
            updated_at=now,
            deleted_at=now,
            purge_after=now + timedelta(days=days) if days is not None else None,
        )
        .execution_options(synchronize_session=False)
    )


def invalidate_material_citations(db, user_id, version_ids):
    db.execute(
        update(Citation)
        .where(Citation.user_id == user_id, Citation.version_id.in_(version_ids))
        .values(availability="unavailable", updated_at=utc_now())
        .execution_options(synchronize_session=False)
    )
