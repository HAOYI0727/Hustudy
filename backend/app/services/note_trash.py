"""Note trash lifecycle. Callers own the transaction and take the owner lock."""

from datetime import timedelta
import hashlib
from sqlalchemy import select, delete, or_
from ..models import Note, NoteLink, AssetReference, Citation, NoteTrashPolicy
from ..models.base import utc_now
from .note_folders import lock_owner


def policy(db, user_id):
    return db.scalar(select(NoteTrashPolicy).where(NoteTrashPolicy.user_id == user_id))


def retention(db, user_id):
    row = policy(db, user_id)
    return row.retention_days if row else 30


def mark_trashed(note, days, now):
    note.deleted = True
    note.deleted_at = now
    note.purge_after = now + timedelta(days=days) if days is not None else None
    note.revision += 1


def snapshot(db, user_id):
    rows = db.execute(
        select(Note.id, Note.revision)
        .where(Note.user_id == user_id, Note.deleted.is_(True))
        .order_by(Note.id)
    ).all()
    value = "\n".join(f"{id}:{revision}" for id, revision in rows)
    return len(rows), hashlib.sha256(value.encode()).hexdigest()


def purge(db, user_id, ids=None):
    scope = [Note.user_id == user_id, Note.deleted.is_(True)]
    if ids is not None:
        scope.append(Note.id.in_(ids))
    targets = select(Note.id).where(*scope)
    # Citations use SET NULL, but a purged note must not leave orphan citations.
    db.execute(
        delete(Citation).where(
            Citation.user_id == user_id, Citation.note_id.in_(targets)
        )
    )
    db.execute(
        delete(AssetReference).where(
            AssetReference.user_id == user_id, AssetReference.note_id.in_(targets)
        )
    )
    db.execute(
        delete(NoteLink).where(
            NoteLink.user_id == user_id,
            or_(
                NoteLink.source_note_id.in_(targets),
                NoteLink.target_note_id.in_(targets),
            ),
        )
    )
    return db.execute(delete(Note).where(*scope)).rowcount


def cleanup_due(db, now=None, limit=200):
    """Bounded, restart-safe cleanup; recheck deadlines after taking SQLite lock."""
    now = now or utc_now()
    due = (Note.deleted.is_(True), Note.purge_after <= now)
    candidates = db.execute(
        select(Note.id, Note.user_id)
        .where(*due)
        .order_by(Note.purge_after, Note.id)
        .limit(limit)
    ).all()
    removed = 0
    for user_id in dict.fromkeys(row.user_id for row in candidates):
        lock_owner(db, user_id)
        ids = db.scalars(
            select(Note.id).where(
                *due,
                Note.user_id == user_id,
                Note.id.in_([row.id for row in candidates if row.user_id == user_id]),
            )
        ).all()
        if ids:
            removed += purge(db, user_id, ids)
    db.commit()
    return removed
