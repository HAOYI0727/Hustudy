"""M3 read-only discovery adapter. No edits, parsing or cross-module writes."""

from ..core.database import begin_read_snapshot

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..core.search_excerpt import excerpt
from ..models import Note
from .courses import owned_course
from .note_filters import text_matches


def search_notes(
    db: Session,
    user_id: str,
    course_id: str,
    query: str,
    offset: int = 0,
    limit: int = 12,
) -> dict:
    begin_read_snapshot(db)
    owned_course(db, user_id, course_id)
    query = query.strip()
    page = {"items": [], "total": 0, "offset": offset, "limit": limit}
    if not query:
        return page
    predicate = (
        Note.user_id == user_id,
        Note.course_id == course_id,
        Note.deleted.is_(False),
        text_matches(query),
    )
    page["total"] = db.scalar(select(func.count()).select_from(Note).where(*predicate))
    # Only a page is loaded; full note bodies never leave this adapter.
    rows = db.execute(
        select(Note.id, Note.title, Note.content, Note.updated_at)
        .where(*predicate)
        .order_by(Note.updated_at.desc(), Note.id)
        .offset(offset)
        .limit(limit)
    ).all()
    page["items"] = [
        {
            "id": row.id,
            "title": row.title,
            "excerpt": excerpt(row.content, query),
            "updated_at": row.updated_at,
        }
        for row in rows
    ]
    return page
