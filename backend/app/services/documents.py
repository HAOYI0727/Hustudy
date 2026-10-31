"""Immutable ingestion and persistent task enqueueing; no heavy work in HTTP."""

import hashlib
import io
import mimetypes
import zipfile
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from ..core.storage import get_storage
from ..models import Document, DocumentVersion, ProcessingJob
from ..repositories.materials import active_document
from .courses import owned_course

ALLOWED_SUFFIXES = {".pptx", ".pdf", ".docx", ".md", ".markdown", ".txt"}
MAX_BYTES = 30 * 1024 * 1024
MIMES = {
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def validate_file(upload: UploadFile):
    filename = Path((upload.filename or "unnamed").replace("\\", "/")).name[:255]
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("仅支持 PPTX、PDF、DOCX、Markdown 或 TXT 文件")
    data = upload.file.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise ValueError("文件不能为空且不能超过 30 MiB")
    if suffix in {".pptx", ".docx"}:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                infos = archive.infolist()
                required = (
                    "ppt/presentation.xml" if suffix == ".pptx" else "word/document.xml"
                )
                if (
                    required not in archive.namelist()
                    or len(infos) > 10000
                    or sum(i.file_size for i in infos) > 100 * 1024 * 1024
                ):
                    raise ValueError("Office 文件内容或解压预算不合法")
                if any(i.flag_bits & 1 for i in infos):
                    raise ValueError("不支持加密 Office 文件")
        except zipfile.BadZipFile as error:
            raise ValueError("Office 文件格式无效") from error
    elif suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("文件内容不是 PDF")
    else:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("文本文件需采用 UTF-8 编码") from error
        if b"\x00" in data:
            raise ValueError("文本文件包含二进制内容")
    return filename, suffix, data


def save_upload(
    upload: UploadFile,
    course_id: str,
    user_id: str,
    db: Session,
    document_id: str | None = None,
    library_scope: str = "material",
):
    if library_scope not in {"material", "question_bank"}:
        raise ValueError("Unknown library scope")
    filename, suffix, data = validate_file(upload)
    owned_course(db, user_id, course_id, lock=True)
    digest = hashlib.sha256(data).hexdigest()
    document = active_document(db, document_id, user_id) if document_id else None
    if document and document.library_scope != library_scope:
        raise ValueError("Wrong library scope")
    if document:
        # Acquire the SQLite write lock before allocating the immutable version number.
        result = db.execute(
            update(Document)
            .where(Document.id == document.id, Document.deleted_at.is_(None))
            .values(name=Document.name)
        )
        if result.rowcount != 1:
            raise ValueError("资料已删除")
        existing = db.scalar(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.sha256 == digest,
            )
        )
    else:
        existing = db.scalar(
            select(DocumentVersion)
            .join(Document)
            .where(
                Document.user_id == user_id,
                Document.course_id == course_id,
                Document.library_scope == library_scope,
                Document.deleted_at.is_(None),
                DocumentVersion.sha256 == digest,
            )
        )
    if existing:
        document = db.get(Document, existing.document_id)
        job = db.scalar(
            select(ProcessingJob)
            .where(
                ProcessingJob.resource_id == existing.id, ProcessingJob.type == "PARSE"
            )
            .order_by(ProcessingJob.created_at.desc())
        )
        db.rollback()
        return document, existing, job, True
    storage = get_storage()
    stored = storage.new_path(
        user_id,
        course_id,
        suffix,
        "question_bank" if library_scope == "question_bank" else "",
    )
    published = False
    try:
        storage.write(stored, data)
        published = True
        mime = MIMES.get(suffix, mimetypes.guess_type(filename)[0] or "text/plain")
        if not document:
            document = Document(
                user_id=user_id,
                course_id=course_id,
                name=Path(filename).stem[:240],
                library_scope=library_scope,
                original_filename=filename,
                mime_type=mime,
                size_bytes=len(data),
                sha256=digest,
                storage_path=str(stored),
            )
            db.add(document)
            db.flush()
        number = (
            db.scalar(
                select(func.max(DocumentVersion.version_no)).where(
                    DocumentVersion.document_id == document.id
                )
            )
            or 0
        ) + 1
        version = DocumentVersion(
            user_id=user_id,
            document_id=document.id,
            version_no=number,
            source_path=str(stored),
            original_filename=filename,
            mime_type=mime,
            size_bytes=len(data),
            sha256=digest,
            # Native readers are the default.  A PDF is already a directly
            # readable page source; Office files keep their original format
            # until the user explicitly asks for a compatibility PDF.
            preview_status="SUCCEEDED" if suffix == ".pdf" else "TEXT_ONLY",
            preview_path=str(stored) if suffix == ".pdf" else None,
        )
        db.add(version)
        db.flush()
        job = ProcessingJob(user_id=user_id, type="PARSE", resource_id=version.id)
        db.add(job)
        db.commit()
        return document, version, job, False
    except Exception:
        db.rollback()
        if published:
            storage.remove(stored)
        raise
