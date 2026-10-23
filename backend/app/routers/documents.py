from pathlib import Path
from uuid import UUID
from typing import List, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..dependencies import current_user
from ..models import (
    Citation,
    Course,
    Document,
    DocumentChunk,
    DocumentVersion,
    ProcessingJob,
    ManualTranscript,
    User,
)
from ..models.base import utc_now
from ..repositories.materials import active_document, active_version
from ..schemas.material import (
    ChunkResponse,
    DocumentResponse,
    DocumentUpdate,
    JobResponse,
    ReindexRequest,
    SearchResponse,
    SearchPage,
    VersionResponse,
    MaterialReferenceResponse,
    ReferenceNotePage,
    DocumentPage,
    JobPage,
    PreviewCapabilities,
    DocumentOrganize,
    DocumentOrganizeResult,
)
from ..schemas.workspace import LearningLinkPage, LearningLinkKind
from ..schemas.material_health import MaterialHealthPage, HealthIssue
from ..services.documents import save_upload
from ..core.storage import InsufficientStorage
from ..services import material_jobs
from ..services.search import search_chunks, search_page
from ..services.note_references import material_references
from ..services.courses import owned_course
from ..services.material_exports import owned_export
from ..services import material_browse, material_organize

router = APIRouter(prefix="/api/v1", tags=["materials"])


@router.get("/courses/{course_id}/material-health", response_model=MaterialHealthPage)
def material_health(
    course_id: str,
    issue: HealthIssue = "attention",
    q: str = Query(default="", max_length=200),
    offset: int = Query(default=0, ge=0, le=1000000),
    limit: int = Query(default=12, ge=1, le=50),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.material_health import page

    return page(db, user.id, course_id, issue, q, offset, limit)


@router.get("/versions/{version_id}/learning-links", response_model=LearningLinkPage)
def learning_links(
    version_id: str,
    kind: LearningLinkKind = "all",
    chunk_id: UUID | None = None,
    q: str = Query(default="", max_length=200),
    offset: int = Query(default=0, ge=0, le=1000000),
    limit: int = Query(default=12, ge=1, le=50),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.source_learning import links

    return links(
        db,
        user,
        version_id,
        str(chunk_id) if chunk_id else None,
        kind,
        q,
        offset,
        limit,
    )


def _course(course_id: str, user: User, db: Session) -> Course:
    return owned_course(db, user.id, course_id)


def _document_response(document: Document, db: Session) -> DocumentResponse:
    version = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_no.desc())
    )
    return DocumentResponse(
        id=document.id,
        course_id=document.course_id,
        name=document.name,
        category=document.category,
        tags=document.tags,
        created_at=document.created_at,
        updated_at=document.updated_at,
        original_filename=version.original_filename
        if version
        else document.original_filename,
        mime_type=version.mime_type if version else document.mime_type,
        size_bytes=version.size_bytes if version else document.size_bytes,
        sha256=version.sha256 if version else document.sha256,
        deleted_at=document.deleted_at,
        latest_version_id=version.id if version else None,
        latest_version_no=version.version_no if version else None,
        confirmed_transcript_count=db.scalar(
            select(func.count())
            .select_from(ManualTranscript)
            .where(
                ManualTranscript.version_id == version.id,
                ManualTranscript.user_id == document.user_id,
                ManualTranscript.status == "CONFIRMED",
            )
        )
        if version
        else 0,
        parse_status=version.parse_status if version else None,
        preview_status=version.preview_status if version else None,
        index_status=version.index_status if version else None,
        parse_error=version.parse_error if version else None,
        preview_error=version.preview_error if version else None,
    )


def _upload(file, course_id, user_id, db, document_id=None):
    try:
        _, _, job, _ = save_upload(file, course_id, user_id, db, document_id)
    except InsufficientStorage:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return JobResponse.model_validate(job, from_attributes=True)


@router.post(
    "/courses/{course_id}/documents", response_model=JobResponse, status_code=202
)
def upload_document(
    course_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _course(course_id, user, db)
    return _upload(file, course_id, user.id, db)


@router.post(
    "/documents/{document_id}/versions", response_model=JobResponse, status_code=202
)
def upload_version(
    document_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    document = active_document(db, document_id, user.id)
    return _upload(file, document.course_id, user.id, db, document.id)


@router.get("/courses/{course_id}/documents", response_model=List[DocumentResponse])
def list_documents(
    course_id: str,
    category: str | None = Query(default=None, max_length=40),
    tag: str | None = Query(default=None, max_length=32),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _course(course_id, user, db)
    statement = select(Document).where(Document.library_scope == "material")
    if category is not None:
        statement = statement.where(Document.category == category.strip())
    if tag is not None:
        tag_values = (
            func.json_each(Document.tags).table_valued("value").alias("doc_tags")
        )
        statement = statement.where(
            select(1)
            .select_from(tag_values)
            .where(tag_values.c.value == tag.strip())
            .exists()
        )
    rows = db.scalars(
        statement.where(
            Document.course_id == course_id,
            Document.user_id == user.id,
            Document.deleted_at.is_(None),
        ).order_by(Document.created_at.desc())
    ).all()
    return [_document_response(row, db) for row in rows]


@router.get("/courses/{course_id}/documents/page", response_model=DocumentPage)
def browse_documents(
    course_id: str,
    q: str = Query(default="", max_length=200),
    category: str = Query(default="", max_length=40),
    tag: str = Query(default="", max_length=32),
    state: Literal["all", "ready", "processing", "failed"] = "all",
    sort: Literal["recent", "name", "size"] = "recent",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=12, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    page = material_browse.document_page(
        db,
        user.id,
        course_id,
        q=q,
        category=category,
        tag=tag,
        state=state,
        sort=sort,
        offset=offset,
        limit=limit,
    )
    page["items"] = [_document_response(row, db) for row in page.pop("rows")]
    return page


@router.get("/courses/{course_id}/jobs/page", response_model=JobPage)
def browse_jobs(
    course_id: str,
    status: Literal["all", "pending", "failed", "cancelled", "succeeded"] = "all",
    kind: Literal["all", "PARSE", "INDEX", "PREVIEW"] = "all",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    page = material_browse.job_page(
        db, user.id, course_id, status=status, kind=kind, offset=offset, limit=limit
    )
    page["items"] = [
        JobResponse.model_validate(job, from_attributes=True).model_copy(
            update={
                "document_id": document.id,
                "document_name": document.name,
                "version_no": version.version_no,
            }
        )
        for job, document, version in page.pop("rows")
    ]
    return page


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return _document_response(active_document(db, document_id, user.id), db)


@router.post(
    "/courses/{course_id}/documents/organize", response_model=DocumentOrganizeResult
)
def organize_documents(
    course_id: str,
    payload: DocumentOrganize,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return material_organize.organize(db, user.id, course_id, payload)


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    payload: DocumentUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    document = material_organize.update_one(db, user.id, document_id, payload)
    return _document_response(document, db)


@router.get("/documents/{document_id}/versions", response_model=List[VersionResponse])
def list_versions(
    document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    active_document(db, document_id, user.id)
    return [
        VersionResponse.model_validate(row, from_attributes=True)
        for row in db.scalars(
            select(DocumentVersion)
            .where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.user_id == user.id,
            )
            .order_by(DocumentVersion.version_no.desc())
        ).all()
    ]


@router.get("/versions/{version_id}", response_model=VersionResponse)
def get_version(
    version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return VersionResponse.model_validate(
        active_version(db, version_id, user.id), from_attributes=True
    )


@router.get("/versions/{version_id}/chunks", response_model=List[ChunkResponse])
def list_chunks(
    version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    active_version(db, version_id, user.id)
    return [
        ChunkResponse.model_validate(row, from_attributes=True).model_copy(
            update={
                "transcript_id": transcript.id if transcript else None,
                "transcript_status": transcript.status if transcript else None,
                "confirmed_at": transcript.confirmed_at if transcript else None,
            }
        )
        for row, transcript in db.execute(
            select(DocumentChunk, ManualTranscript)
            .outerjoin(ManualTranscript, ManualTranscript.chunk_id == DocumentChunk.id)
            .where(
                DocumentChunk.version_id == version_id, DocumentChunk.user_id == user.id
            )
            .where(
                (DocumentChunk.source_kind == "extracted")
                | ManualTranscript.status.in_(["CONFIRMED", "SUPERSEDED"])
            )
            .order_by(DocumentChunk.ordinal)
        ).all()
    ]


@router.get("/versions/{version_id}/reference-notes", response_model=ReferenceNotePage)
def reference_notes(
    version_id: str,
    chunk_id: str | None = Query(default=None),
    q: str = Query(default="", max_length=200),
    offset: int = Query(default=0, ge=0, le=1000000),
    limit: int = Query(default=6, ge=1, le=50),
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    from ..services.note_references import reference_notes as page
    return page(db, user.id, version_id, chunk_id, q, offset, limit)


@router.get(
    "/versions/{version_id}/references", response_model=List[MaterialReferenceResponse]
)
def references(
    version_id: str,
    chunk_id: str | None = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    active_version(db, version_id, user.id)
    if chunk_id and not db.scalar(
        select(DocumentChunk.id).where(
            DocumentChunk.id == chunk_id,
            DocumentChunk.version_id == version_id,
            DocumentChunk.user_id == user.id,
        )
    ):
        raise HTTPException(404, "资料片段不存在")
    return material_references(db, user.id, version_id, chunk_id)


@router.get("/versions/{version_id}/original")
def original(
    version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    version = active_version(db, version_id, user.id)
    if not Path(version.source_path).is_file():
        raise HTTPException(404, "原始文件不可用")
    return FileResponse(
        version.source_path,
        media_type=version.mime_type,
        filename=version.original_filename,
    )


@router.get("/versions/{version_id}/preview")
def preview(
    version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    version = active_version(db, version_id, user.id)
    if (
        version.preview_status != "SUCCEEDED"
        or not version.preview_path
        or not Path(version.preview_path).is_file()
    ):
        raise HTTPException(
            409,
            {
                "message": "PDF 预览尚不可用，可使用结构化文本阅读",
                "preview_status": version.preview_status,
                "reason": version.preview_error,
            },
        )
    from ..services.preview_integrity import check_preview_mapping

    try:
        check_preview_mapping(Path(version.source_path), Path(version.preview_path))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return FileResponse(
        version.preview_path,
        media_type="application/pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/courses/{course_id}/search", response_model=List[SearchResponse])
def search(
    course_id: str,
    q: str = Query(max_length=200),
    category: str | None = Query(default=None, max_length=40),
    tag: str | None = Query(default=None, max_length=32),
    latest_only: bool = False,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _course(course_id, user, db)
    return [
        SearchResponse(**row)
        for row in search_chunks(
            db,
            user.id,
            course_id,
            q.strip(),
            category=category,
            tag=tag,
            latest_only=latest_only,
        )
    ]


@router.get("/courses/{course_id}/search/page", response_model=SearchPage)
def paged_search(
    course_id: str,
    q: str = Query(max_length=200),
    category: str | None = Query(default=None, max_length=40),
    tag: str | None = Query(default=None, max_length=32),
    latest_only: bool = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=12, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _course(course_id, user, db)
    return search_page(
        db,
        user.id,
        course_id,
        q.strip(),
        category=category,
        tag=tag,
        latest_only=latest_only,
        offset=offset,
        limit=limit,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    job = db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.id == job_id, ProcessingJob.user_id == user.id
        )
    )
    if not job:
        raise HTTPException(404, "任务不存在")
    if job.type in {"PARSE", "INDEX", "PREVIEW"}:
        active_version(db, job.resource_id, user.id)
    elif job.type == "MATERIAL_EXPORT":
        # Removed export records may retain terminal history; a retained record
        # still has its course scope and must be checked.
        from ..models import MaterialExport

        if db.get(MaterialExport, job.resource_id):
            owned_export(db, job.resource_id, user.id)
    elif job.type == "AI_ANALYSIS":
        from ..services.remote_ai import owned_query

        owned_query(db, user.id, job.resource_id)
    return JobResponse.model_validate(job, from_attributes=True)


@router.get("/courses/{course_id}/jobs", response_model=List[JobResponse])
def list_jobs(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    _course(course_id, user, db)
    rows = db.execute(
        select(ProcessingJob, Document, DocumentVersion)
        .join(DocumentVersion, ProcessingJob.resource_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(
            Document.course_id == course_id,
            Document.deleted_at.is_(None),
            Document.library_scope == "material",
            Document.user_id == user.id,
            DocumentVersion.user_id == user.id,
            ProcessingJob.user_id == user.id,
            ProcessingJob.type.in_(["PARSE", "INDEX", "PREVIEW"]),
        )
        .order_by(ProcessingJob.created_at.desc())
        .limit(100)
    ).all()
    return [
        JobResponse.model_validate(job, from_attributes=True).model_copy(
            update={
                "document_id": document.id,
                "document_name": document.name,
                "version_no": version.version_no,
            }
        )
        for job, document, version in rows
    ]


@router.post("/jobs/{job_id}/retry", response_model=JobResponse, status_code=202)
def retry_job(
    job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return material_jobs.retry_job(db, user.id, job_id)


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
def cancel_job(
    job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return material_jobs.cancel_job(db, user.id, job_id)


@router.post(
    "/versions/{version_id}/reindex", response_model=JobResponse, status_code=202
)
def reindex_version(
    version_id: str,
    payload: ReindexRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return material_jobs.reindex(db, user.id, version_id, str(payload.request_id))


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> None:
    document = active_document(db, document_id, user.id)
    if document.library_scope == "question_bank":
        from ..services.courses import owned_course
        from ..services.question_bank import no_active_attempt

        owned_course(db, user.id, document.course_id, lock=True)
        no_active_attempt(db, user.id, document.course_id)
    document.deleted_at = utc_now()
    from ..services.ai_retirement import cancel_source_queries

    cancel_source_queries(
        db,
        user.id,
        db.scalars(
            select(DocumentVersion.id).where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.user_id == user.id,
            )
        ).all(),
    )
    versions = select(DocumentVersion.id).where(
        DocumentVersion.document_id == document.id
    )
    db.execute(
        update(Citation)
        .where(Citation.version_id.in_(versions))
        .values(availability="unavailable")
    )
    db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.resource_id.in_(versions),
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
        .values(
            status="CANCELLED", lease_token=None, lease_until=None, error="资料已删除"
        )
    )
    db.commit()


@router.get("/material-capabilities", response_model=PreviewCapabilities)
def material_capabilities(user: User = Depends(current_user)):
    from ..services.preview_runtime import preview_capabilities

    return preview_capabilities()


@router.post(
    "/versions/{version_id}/preview-jobs", response_model=JobResponse, status_code=202
)
def request_preview(
    version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return material_jobs.request_preview(db, user.id, version_id)
