"""M1 course removal: revoke files and jobs, keep source identity and tombstones."""

from sqlalchemy import select, update, func, or_, text
from ..models import Document, DocumentVersion, Asset, ProcessingJob, MaterialExport
from ..models.base import utc_now
from ..repositories.assets import available_assets
from .note_retirement import invalidate_material_citations


def course_versions(user_id, course_id):
    return (
        select(DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(
            DocumentVersion.user_id == user_id,
            Document.user_id == user_id,
            Document.course_id == course_id,
        )
    )


def course_material_counts(db, user_id, course_id):
    docs = select(Document.id).where(
        Document.user_id == user_id,
        Document.course_id == course_id,
        Document.deleted_at.is_(None),
    )
    return {
        "documents": db.scalar(
            select(func.count()).select_from(Document).where(Document.id.in_(docs))
        ),
        "versions": db.scalar(
            select(func.count())
            .select_from(DocumentVersion)
            .where(
                DocumentVersion.user_id == user_id,
                DocumentVersion.document_id.in_(docs),
            )
        ),
        "assets": db.scalar(
            select(func.count())
            .select_from(Asset)
            .where(available_assets(user_id, course_id))
        ),
        "material_exports": db.scalar(
            select(func.count())
            .select_from(MaterialExport)
            .where(
                MaterialExport.user_id == user_id, MaterialExport.course_id == course_id
            )
        ),
    }


def retire_course_materials(db, user_id, course_id):
    versions = course_versions(user_id, course_id)
    invalidate_material_citations(db, user_id, versions)
    export_jobs = select(MaterialExport.job_id).where(
        MaterialExport.user_id == user_id, MaterialExport.course_id == course_id
    )
    db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.user_id == user_id,
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
            or_(
                (ProcessingJob.type.in_(["PARSE", "INDEX", "PREVIEW"]))
                & ProcessingJob.resource_id.in_(versions),
                (ProcessingJob.type == "MATERIAL_EXPORT")
                & ProcessingJob.id.in_(export_jobs),
            ),
        )
        .values(
            status="CANCELLED", lease_token=None, lease_until=None, error="课程已删除"
        )
        .execution_options(synchronize_session=False)
    )
    db.execute(
        text("""DELETE FROM chunk_search WHERE chunk_id IN (
        SELECT c.id FROM document_chunks c JOIN document_versions v ON c.version_id=v.id JOIN documents d ON v.document_id=d.id
        WHERE c.user_id=:u AND v.user_id=:u AND d.user_id=:u AND d.course_id=:course)"""),
        {"u": user_id, "course": course_id},
    )
    db.execute(
        update(Document)
        .where(
            Document.user_id == user_id,
            Document.course_id == course_id,
            Document.deleted_at.is_(None),
        )
        .values(deleted_at=utc_now(), updated_at=utc_now())
        .execution_options(synchronize_session=False)
    )
    db.execute(
        update(Asset)
        .where(Asset.user_id == user_id, Asset.course_id == course_id)
        .values(deleted=True, updated_at=utc_now())
        .execution_options(synchronize_session=False)
    )
