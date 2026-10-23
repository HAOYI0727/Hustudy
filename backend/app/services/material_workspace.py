"""M1-owned course read summary. Never return file bytes or chunk bodies."""

from sqlalchemy import select
from ..models import Document, DocumentVersion
from .material_browse import document_page, job_page
from .workspace_record_query import metadata_query
from .material_health import current_counts


def records(user_id, course_id):
    latest = (
        select(DocumentVersion.id)
        .where(
            DocumentVersion.document_id == Document.id,
            DocumentVersion.user_id == user_id,
        )
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
        .correlate(Document)
        .scalar_subquery()
    )
    return (
        metadata_query(
            Document.id,
            Document.name,
            "material",
            DocumentVersion.parse_status,
            Document.updated_at,
            Document.id,
            DocumentVersion.id,
        )
        .join(DocumentVersion, DocumentVersion.id == latest)
        .where(
            Document.user_id == user_id,
            Document.course_id == course_id,
            Document.library_scope == "material",
            Document.deleted_at.is_(None),
        )
    )


def summary(db, user, course_id):
    page = document_page(
        db,
        user.id,
        course_id,
        q="",
        category=None,
        tag=None,
        state="all",
        sort="recent",
        offset=0,
        limit=6,
    )
    queue = job_page(
        db,
        user.id,
        course_id,
        status="failed",
        kind="all",
        offset=0,
        limit=1,
    )
    recent = []
    for document in page["rows"]:
        version = db.scalar(
            select(DocumentVersion)
            .where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.user_id == user.id,
            )
            .order_by(DocumentVersion.version_no.desc())
            .limit(1)
        )
        if version:
            recent.append(
                dict(
                    id=document.id,
                    title=document.name,
                    kind="material",
                    status=version.parse_status,
                    updated_at=document.updated_at,
                    document_id=document.id,
                    version_id=version.id,
                )
            )
    return {
        "counts": {
            **page["stats"],
            "failed_jobs": queue["total"],
            "pending_jobs": queue["pending_count"],
            "attention_materials": current_counts(db, user.id, course_id)["attention"],
        },
        "recent": recent,
    }
