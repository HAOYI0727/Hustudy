"""M3 citation lifecycle; source metadata uses the authorized M1 boundary."""

from fastapi import HTTPException
from sqlalchemy import select, update

from ..models import Note
from ..repositories.materials import active_document, active_version
from ..schemas.notes import CitationResponse


def lock_note(db, user_id, note_id):
    changed = db.execute(
        update(Note)
        .where(Note.id == note_id, Note.user_id == user_id, Note.deleted.is_(False))
        .values(updated_at=Note.updated_at)
        .execution_options(synchronize_session=False)
    )
    if changed.rowcount != 1:
        raise HTTPException(404, "笔记不存在")
    db.expire_all()
    return db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user_id))


def citation_response(db, user_id, citation, cache=None):
    cache = {} if cache is None else cache
    if citation.version_id not in cache:
        try:
            version = active_version(db, citation.version_id, user_id)
            document = active_document(db, version.document_id, user_id)
            cache[citation.version_id] = {
                "document_id": document.id,
                "document_name": document.name or document.original_filename,
                "version_no": version.version_no,
            }
        except HTTPException as error:
            if error.status_code != 404:
                raise
            cache[citation.version_id] = None
    metadata = cache[citation.version_id]
    result = CitationResponse.model_validate(citation, from_attributes=True)
    return result.model_copy(update=metadata or {"availability": "unavailable"})
