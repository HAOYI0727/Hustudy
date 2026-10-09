import hashlib
import mimetypes
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models import Document, DocumentChunk, DocumentVersion, ProcessingJob
from .materials import parse_document

ALLOWED_SUFFIXES = {".pptx", ".pdf", ".docx", ".md", ".markdown", ".txt"}
MAX_BYTES = 20 * 1024 * 1024


def save_upload(upload: UploadFile, course_id: str, user_id: str, db: Session) -> Tuple[Document, DocumentVersion, ProcessingJob, bool]:
    filename = Path(upload.filename or "unnamed").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("仅支持 PPTX、PDF、DOCX、Markdown 或 TXT 文件")
    data = upload.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("文件大小不能超过 20 MiB")
    digest = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(Document).where(Document.user_id == user_id, Document.course_id == course_id, Document.sha256 == digest, Document.deleted_at.is_(None)))
    if existing:
        version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == existing.id).order_by(DocumentVersion.version_no.desc()))
        job = db.scalar(select(ProcessingJob).where(ProcessingJob.resource_id == (version.id if version else existing.id)).order_by(ProcessingJob.created_at.desc()))
        return existing, version, job, True
    settings = get_settings()
    folder = Path(settings.storage_root) / user_id / course_id
    folder.mkdir(parents=True, exist_ok=True)
    stored = folder / f"{uuid4().hex}{suffix}"
    stored.write_bytes(data)
    document = Document(user_id=user_id, course_id=course_id, name=Path(filename).stem, original_filename=filename, mime_type=upload.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream", size_bytes=len(data), sha256=digest, storage_path=str(stored))
    db.add(document)
    db.flush()
    version = DocumentVersion(user_id=user_id, document_id=document.id, version_no=1, source_path=str(stored))
    db.add(version)
    db.flush()
    job = ProcessingJob(user_id=user_id, type="PARSE", resource_id=version.id)
    db.add(job)
    db.commit()
    return document, version, job, False


def process_version(version_id: str, user_id: str, db: Session) -> ProcessingJob:
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id, DocumentVersion.user_id == user_id))
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.resource_id == version_id, ProcessingJob.user_id == user_id).order_by(ProcessingJob.created_at.desc()))
    if not version or not job:
        raise ValueError("处理任务不存在")
    job.status = "RUNNING"
    version.parse_status = "RUNNING"
    db.commit()
    try:
        chunks = parse_document(Path(version.source_path), Path(version.source_path).suffix)
        old = db.scalars(select(DocumentChunk).where(DocumentChunk.version_id == version.id)).all()
        for chunk in old:
            db.delete(chunk)
        for ordinal, item in enumerate(chunks):
            db.add(DocumentChunk(user_id=user_id, version_id=version.id, ordinal=ordinal, **item))
        version.parse_status = "SUCCEEDED"
        version.preview_status = "TEXT_ONLY"
        version.index_status = "SUCCEEDED"
        job.status = "SUCCEEDED"
        job.progress = 100
        job.error = None
    except Exception as exc:  # surface a structured failure in the document status
        version.parse_status = "FAILED"
        version.preview_status = "FAILED"
        version.index_status = "FAILED"
        version.parse_error = str(exc)
        job.status = "FAILED"
        job.error = str(exc)
    db.commit()
    return job
