from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.database import SessionLocal, get_db
from ..dependencies import current_user
from ..models import Course, Document, DocumentChunk, DocumentVersion, ProcessingJob, User
from ..schemas.material import ChunkResponse, DocumentResponse, JobResponse, SearchResponse, VersionResponse
from ..services.documents import process_version, save_upload

router = APIRouter(prefix="/api/v1", tags=["materials"])


def _course(course_id: str, user: User, db: Session) -> Course:
    course = db.scalar(select(Course).where(Course.id == course_id, Course.user_id == user.id))
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


def _doc(document_id: str, user: User, db: Session) -> Document:
    document = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user.id))
    if not document:
        raise HTTPException(status_code=404, detail="资料不存在")
    return document


def _document_response(document: Document, db: Session) -> DocumentResponse:
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id).order_by(DocumentVersion.version_no.desc()))
    return DocumentResponse(id=document.id, course_id=document.course_id, name=document.name, original_filename=document.original_filename, mime_type=document.mime_type, size_bytes=document.size_bytes, sha256=document.sha256, deleted_at=document.deleted_at, latest_version_id=version.id if version else None, parse_status=version.parse_status if version else None, preview_status=version.preview_status if version else None, index_status=version.index_status if version else None, parse_error=version.parse_error if version else None)


def _run_parse(version_id: str, user_id: str) -> None:
    db = SessionLocal()
    try:
        process_version(version_id, user_id, db)
    finally:
        db.close()


@router.post("/courses/{course_id}/documents", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_document(course_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)) -> JobResponse:
    _course(course_id, user, db)
    try:
        document, version, job, duplicate = save_upload(file, course_id, user.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if duplicate:
        return JobResponse.model_validate(job, from_attributes=True)
    background_tasks.add_task(_run_parse, version.id, user.id)
    return JobResponse.model_validate(job, from_attributes=True)


@router.get("/courses/{course_id}/documents", response_model=List[DocumentResponse])
def list_documents(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[DocumentResponse]:
    _course(course_id, user, db)
    rows = db.scalars(select(Document).where(Document.course_id == course_id, Document.user_id == user.id, Document.deleted_at.is_(None)).order_by(Document.created_at.desc())).all()
    return [_document_response(row, db) for row in rows]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> DocumentResponse:
    return _document_response(_doc(document_id, user, db), db)


@router.get("/documents/{document_id}/versions", response_model=List[VersionResponse])
def list_versions(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[VersionResponse]:
    _doc(document_id, user, db)
    return [VersionResponse.model_validate(row, from_attributes=True) for row in db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == document_id, DocumentVersion.user_id == user.id).order_by(DocumentVersion.version_no.desc())).all()]


@router.get("/versions/{version_id}/chunks", response_model=List[ChunkResponse])
def list_chunks(version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[ChunkResponse]:
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id, DocumentVersion.user_id == user.id))
    if not version:
        raise HTTPException(status_code=404, detail="资料版本不存在")
    rows = db.scalars(select(DocumentChunk).where(DocumentChunk.version_id == version_id, DocumentChunk.user_id == user.id).order_by(DocumentChunk.ordinal)).all()
    return [ChunkResponse.model_validate(row, from_attributes=True) for row in rows]


@router.get("/versions/{version_id}/original")
def original(version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> FileResponse:
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id, DocumentVersion.user_id == user.id))
    if not version or not Path(version.source_path).exists():
        raise HTTPException(status_code=404, detail="原始文件不可用")
    return FileResponse(version.source_path)


@router.get("/courses/{course_id}/search", response_model=List[SearchResponse])
def search(course_id: str, q: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[SearchResponse]:
    _course(course_id, user, db)
    query = q.strip()
    if not query:
        return []
    match = f"%{query}%"
    rows = db.execute(select(DocumentChunk, DocumentVersion, Document).join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id).where(DocumentChunk.user_id == user.id, Document.course_id == course_id, Document.deleted_at.is_(None), DocumentVersion.index_status == "SUCCEEDED", (DocumentChunk.text.ilike(match) | DocumentChunk.locator_value.ilike(match))).limit(50)).all()
    return [SearchResponse(chunk_id=chunk.id, version_id=version.id, document_id=document.id, document_name=document.name, locator_type=chunk.locator_type, locator_value=chunk.locator_value, text=chunk.text, score=1.0) for chunk, version, document in rows]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> JobResponse:
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_id, ProcessingJob.user_id == user.id))
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return JobResponse.model_validate(job, from_attributes=True)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    document = _doc(document_id, user, db)
    document.deleted_at = document.updated_at
    db.commit()
