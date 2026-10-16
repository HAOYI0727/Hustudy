"""Owned, stable, server-filtered catalogues; legacy array APIs stay compatible."""

from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import aliased
from ..models import Document, DocumentVersion, ProcessingJob, ManualTranscript
from .courses import owned_course


def document_page(
    db, user_id, course_id, *, q, category, tag, state, sort, offset, limit
):
    owned_course(db, user_id, course_id)
    version = aliased(DocumentVersion)
    latest = (
        select(DocumentVersion.id)
        .where(DocumentVersion.document_id == Document.id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
        .correlate(Document)
        .scalar_subquery()
    )
    manual = (
        select(1)
        .where(
            ManualTranscript.version_id == version.id,
            ManualTranscript.user_id == user_id,
            ManualTranscript.status == "CONFIRMED",
        )
        .exists()
    )
    ready = or_(
        and_(version.parse_status == "SUCCEEDED", version.index_status == "SUCCEEDED"),
        manual,
    )
    processing = or_(
        *(
            field.in_(["QUEUED", "RUNNING"])
            for field in (
                version.parse_status,
                version.index_status,
                version.preview_status,
            )
        )
    )
    failed = or_(
        *(
            field == "FAILED"
            for field in (
                version.parse_status,
                version.index_status,
                version.preview_status,
            )
        )
    )
    base = (
        select(Document)
        .outerjoin(version, version.id == latest)
        .where(
            Document.user_id == user_id,
            Document.course_id == course_id,
            Document.deleted_at.is_(None),
        )
    )

    def count(statement):
        return (
            db.scalar(
                statement.with_only_columns(
                    func.count(), maintain_column_froms=True
                ).order_by(None)
            )
            or 0
        )

    stats = {
        "total": count(base),
        "ready": count(base.where(ready)),
        "processing": count(base.where(processing)),
    }
    metadata = db.execute(
        select(Document.category, Document.tags).where(
            Document.user_id == user_id,
            Document.course_id == course_id,
            Document.deleted_at.is_(None),
        )
    ).all()
    query = base
    tags = func.json_each(Document.tags).table_valued("value").alias("browse_tags")
    if q.strip():
        value = q.strip().lower()
        query = query.where(
            or_(
                func.instr(func.lower(Document.name), value) > 0,
                func.instr(
                    func.lower(
                        func.coalesce(
                            version.original_filename, Document.original_filename
                        )
                    ),
                    value,
                )
                > 0,
                select(1)
                .select_from(tags)
                .where(func.instr(func.lower(tags.c.value), value) > 0)
                .exists(),
            )
        )
    if category:
        query = query.where(Document.category == category.strip())
    if tag:
        query = query.where(
            select(1).select_from(tags).where(tags.c.value == tag.strip()).exists()
        )
    if state != "all":
        query = query.where(
            {"ready": ready, "processing": processing, "failed": failed}[state]
        )
    order = {
        "recent": Document.updated_at.desc(),
        "name": func.lower(Document.name),
        "size": func.coalesce(version.size_bytes, Document.size_bytes).desc(),
    }[sort]
    return {
        "rows": list(
            db.scalars(query.order_by(order, Document.id).offset(offset).limit(limit))
        ),
        "total": count(query),
        "offset": offset,
        "limit": limit,
        "stats": stats,
        "categories": sorted({row.category for row in metadata}),
        "tags": sorted({value for row in metadata for value in row.tags}),
    }


def job_page(db, user_id, course_id, *, status, kind, offset, limit):
    owned_course(db, user_id, course_id)
    base = (
        select(ProcessingJob, Document, DocumentVersion)
        .join(DocumentVersion, ProcessingJob.resource_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(
            Document.course_id == course_id,
            Document.deleted_at.is_(None),
            Document.user_id == user_id,
            DocumentVersion.user_id == user_id,
            ProcessingJob.user_id == user_id,
            ProcessingJob.type.in_(["PARSE", "INDEX", "PREVIEW"]),
        )
    )

    def count(statement):
        return (
            db.scalar(
                statement.with_only_columns(
                    func.count(), maintain_column_froms=True
                ).order_by(None)
            )
            or 0
        )

    pending = count(base.where(ProcessingJob.status.in_(["QUEUED", "RUNNING"])))
    query = base
    if status != "all":
        query = query.where(
            ProcessingJob.status.in_(["QUEUED", "RUNNING"])
            if status == "pending"
            else ProcessingJob.status == status.upper()
        )
    if kind != "all":
        query = query.where(ProcessingJob.type == kind)
    return {
        "rows": db.execute(
            query.order_by(ProcessingJob.created_at.desc(), ProcessingJob.id)
            .offset(offset)
            .limit(limit)
        ).all(),
        "total": count(query),
        "pending_count": pending,
        "offset": offset,
        "limit": limit,
    }
