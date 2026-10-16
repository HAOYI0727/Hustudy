"""Read-only M3 interface for M1's source-to-note navigation."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Citation, Note
from ..repositories.materials import active_version


def material_references(
    db: Session, user_id: str, version_id: str, chunk_id: str | None = None
):
    active_version(db, version_id, user_id)
    statement = (
        select(Citation, Note)
        .join(Note, Note.id == Citation.note_id)
        .where(
            Citation.user_id == user_id,
            Citation.version_id == version_id,
            Citation.availability == "active",
            Note.user_id == user_id,
            Note.deleted.is_(False),
        )
    )
    if chunk_id:
        statement = statement.where(Citation.chunk_id == chunk_id)
    return [
        {
            "citation_id": citation.id,
            "note_id": note.id,
            "note_title": note.title,
            "chunk_id": citation.chunk_id,
            "quote": citation.quote,
            "locator_type": citation.locator_type,
            "locator_value": citation.locator_value,
        }
        for citation, note in db.execute(
            statement.order_by(Citation.updated_at.desc(), Citation.id)
        ).all()
    ]
