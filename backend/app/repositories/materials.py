"""The shared authorized source boundary consumed by M1, M2 and M3."""

from fastapi import HTTPException
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from ..models import Course, Document, DocumentChunk, DocumentVersion, ManualTranscript


def indexable_source():
    """Shared source eligibility for keyword search and M2 context selection."""
    return or_(
        and_(
            DocumentChunk.source_kind == "extracted",
            DocumentVersion.parse_status == "SUCCEEDED",
            DocumentVersion.index_status == "SUCCEEDED",
        ),
        and_(
            DocumentChunk.source_kind == "manual_transcript",
            select(ManualTranscript.id)
            .where(
                ManualTranscript.chunk_id == DocumentChunk.id,
                ManualTranscript.user_id == DocumentChunk.user_id,
                ManualTranscript.status == "CONFIRMED",
            )
            .exists(),
        ),
    )


def active_document(db: Session, document_id: str, user_id: str) -> Document:
    row = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
            Document.deleted_at.is_(None),
            select(Course.id)
            .where(
                Course.id == Document.course_id,
                Course.user_id == user_id,
                Course.deleted_at.is_(None),
            )
            .exists(),
        )
    )
    if row is None:
        raise HTTPException(404, "资料不存在或已删除")
    return row


def active_version(
    db: Session, version_id: str, user_id: str, course_id: str | None = None
) -> DocumentVersion:
    statement = (
        select(DocumentVersion)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(
            DocumentVersion.id == version_id,
            DocumentVersion.user_id == user_id,
            Document.user_id == user_id,
            Document.deleted_at.is_(None),
            select(Course.id)
            .where(
                Course.id == Document.course_id,
                Course.user_id == user_id,
                Course.deleted_at.is_(None),
            )
            .exists(),
        )
    )
    if course_id:
        statement = statement.where(Document.course_id == course_id)
    row = db.scalar(statement)
    if row is None:
        raise HTTPException(404, "资料版本不存在或已删除")
    return row


def checked_chunk(
    db: Session,
    version_id: str,
    chunk_id: str,
    quote: str,
    user_id: str,
    course_id: str | None = None,
):
    version = active_version(db, version_id, user_id, course_id)
    document = db.get(Document, version.document_id)
    from ..services.courses import owned_course

    owned_course(db, user_id, document.course_id, lock=True)
    row = db.scalar(
        select(DocumentChunk).where(
            DocumentChunk.id == chunk_id,
            DocumentChunk.version_id == version_id,
            DocumentChunk.user_id == user_id,
        )
    )
    if row is None or not quote.strip() or quote not in row.text:
        raise HTTPException(422, "引用版本、切片或摘录不匹配")
    if row.source_kind == "manual_transcript" and not db.scalar(
        select(ManualTranscript.id).where(
            ManualTranscript.chunk_id == row.id,
            ManualTranscript.user_id == user_id,
            ManualTranscript.status.in_(["CONFIRMED", "SUPERSEDED"]),
        )
    ):
        raise HTTPException(422, "人工来源尚未确认或已撤回")
    return row
