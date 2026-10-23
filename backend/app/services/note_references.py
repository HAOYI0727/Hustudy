"""Read-only M3 interface for M1's source-to-note navigation."""

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..models import Citation, Note, Document, DocumentChunk
from ..core.database import begin_read_snapshot
from ..models.base import utc_now
from ..repositories.materials import active_version
from ..repositories.source_links import valid_reference


def _eligible(user_id, version_id, chunk_id=None):
    return (
        Citation.user_id == user_id,
        Citation.version_id == version_id,
        Citation.availability == "active",
        Note.user_id == user_id,
        Note.deleted.is_(False),
        valid_reference(
            user_id, version_id, Citation.chunk_id, Citation.quote, chunk_id
        ),
    )


def material_references(
    db: Session, user_id: str, version_id: str, chunk_id: str | None = None
):
    active_version(db, version_id, user_id)
    statement = (
        select(
            Citation.id.label("citation_id"),
            Note.id.label("note_id"),
            Note.title.label("note_title"),
            Citation.chunk_id,
            Citation.quote,
            Citation.locator_type,
            Citation.locator_value,
        )
        .join(Note, Note.id == Citation.note_id)
        .where(*_eligible(user_id, version_id, chunk_id))
    )
    if chunk_id:
        statement = statement.where(Citation.chunk_id == chunk_id)
    return (
        db.execute(statement.order_by(Citation.updated_at.desc(), Citation.id))
        .mappings()
        .all()
    )


def reference_notes(db, user_id, version_id, chunk_id, q, offset, limit):
    begin_read_snapshot(db)
    version = active_version(db, version_id, user_id)
    document = db.get(Document, version.document_id)
    if document.library_scope != "material":
        raise HTTPException(404, "资料版本不存在或不可访问")
    if chunk_id is not None and not db.scalar(
        select(DocumentChunk.id).where(
            DocumentChunk.id == chunk_id,
            DocumentChunk.version_id == version_id,
            DocumentChunk.user_id == user_id,
        )
    ):
        raise HTTPException(404, "原文片段不存在或不属于当前版本")
    rows = (
        select(
            Note.id.label("note_id"),
            Note.title.label("note_title"),
            Note.course_id.label("note_course_id"),
            Note.updated_at,
            Citation.id.label("citation_id"),
            Citation.chunk_id,
            Citation.locator_type,
            Citation.locator_value,
            func.substr(Citation.quote, 1, 180).label("quote_excerpt"),
            func.count(Citation.id).over(partition_by=Note.id).label("citation_count"),
            func.row_number()
            .over(
                partition_by=Note.id,
                order_by=(Citation.updated_at.desc(), Citation.id),
            )
            .label("sample_rank"),
        )
        .join(Citation, Citation.note_id == Note.id)
        .where(*_eligible(user_id, version_id, chunk_id))
    )
    if q.strip():
        rows = rows.where(func.instr(func.lower(Note.title), q.strip().lower()) > 0)
    ranked = rows.subquery()
    grouped = (
        select(*[col for col in ranked.c if col.key != "sample_rank"])
        .where(
            ranked.c.sample_rank == 1,
        )
        .subquery()
    )
    total = db.scalar(select(func.count()).select_from(grouped)) or 0
    items = (
        db.execute(
            select(grouped)
            .order_by(
                grouped.c.updated_at.desc(),
                grouped.c.note_id,
            )
            .offset(offset)
            .limit(limit)
        )
        .mappings()
        .all()
    )
    return dict(
        course_id=document.course_id,
        document_id=document.id,
        version_id=version_id,
        chunk_id=chunk_id,
        items=items,
        total=total,
        offset=offset,
        limit=limit,
        checked_at=utc_now(),
    )
