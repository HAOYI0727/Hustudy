"""Owned local recognition; results are text for insertion into the current note."""

import hashlib
import importlib.util
from pathlib import Path, PurePosixPath
from typing import Literal
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..core.config import get_settings
from ..core.database import get_db
from ..core.storage import LocalFileStorage
from ..dependencies import current_user
from ..models import NoteCapture, ProcessingJob, User
from ..services.courses import owned_course
from ..services.note_folders import lock_owner
from ..services.note_ai_config import DISABLED_REASON

router = APIRouter(prefix="/api/v1/note-captures", tags=["note-capture"])
SUFFIXES = {
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".wav",
    ".mp3",
    ".m4a",
    ".webm",
    ".ogg",
    ".mp4",
}


def owned(db, user, capture_id):
    row = db.scalar(
        select(NoteCapture).where(
            NoteCapture.id == capture_id, NoteCapture.user_id == user.id
        )
    )
    if not row:
        raise HTTPException(404, "识别任务不存在")
    owned_course(db, user.id, row.course_id)
    return row


def response(db, row):
    job = db.get(ProcessingJob, row.job_id)
    return {
        "id": row.id,
        "filename": row.filename,
        "course_id": row.course_id,
        "status": job.status,
        "kind": job.type,
        "error": job.error,
        "result": row.result,
        "ai_result": row.ai_result,
    }


@router.get("/capabilities")
def capabilities(user: User = Depends(current_user), db: Session = Depends(get_db)):
    settings = get_settings()
    return {
        "ocr": importlib.util.find_spec("rapidocr_onnxruntime") is not None,
        "speech": importlib.util.find_spec("faster_whisper") is not None
        and (Path(settings.speech_model_path) / "model.bin").is_file(),
        "ai": False,
        "model": "",
        "ai_unavailable_reason": DISABLED_REASON,
    }


@router.get("")
def listing(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_course(db, user.id, course_id)
    rows = db.scalars(
        select(NoteCapture)
        .where(NoteCapture.user_id == user.id, NoteCapture.course_id == course_id)
        .order_by(NoteCapture.created_at.desc())
        .limit(100)
    )
    return [response(db, row) for row in rows]


@router.post("", status_code=201)
async def upload(
    file: UploadFile = File(...),
    course_id: str = Form(...),
    request_id: UUID = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned_course(db, user.id, course_id)
    name = PurePosixPath((file.filename or "").replace("\\", "/")).name
    suffix = PurePosixPath(name).suffix.lower()
    if (
        suffix not in SUFFIXES
        or not name
        or len(name) > 240
        or any(ord(c) < 32 for c in name)
    ):
        raise HTTPException(
            422, "请选择PDF、DOCX、PNG/JPEG/WebP或音频文件，文件名最多240字"
        )
    try:
        data = await file.read(20 * 1024 * 1024 + 1)
    finally:
        await file.close()
    if not data or len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "文件不能为空且不能超过20MiB")
    digest = hashlib.sha256(data).hexdigest()
    lock_owner(db, user.id)
    owned_course(db, user.id, course_id)
    previous = db.get(NoteCapture, str(request_id))
    if previous:
        if previous.user_id != user.id:
            raise HTTPException(404, "请求标识不可用")
        if (
            previous.source_hash != digest
            or previous.filename != name
            or previous.course_id != course_id
        ):
            raise HTTPException(409, "请求标识已用于其他文件")
        return response(db, previous)
    if (
        db.scalar(
            select(func.count())
            .select_from(NoteCapture)
            .where(NoteCapture.user_id == user.id)
        )
        >= 100
    ):
        raise HTTPException(409, "最多保留100份识别任务，请先插入所需文本并移除旧任务")
    storage = LocalFileStorage(Path(get_settings().storage_root))
    path = storage.checked(
        storage.root / user.id / ".captures" / (str(request_id) + suffix)
    )
    storage.write(path, data)
    job = ProcessingJob(
        id=str(uuid4()),
        user_id=user.id,
        type="NOTE_CAPTURE",
        resource_id=str(request_id),
        max_attempts=1,
    )
    row = NoteCapture(
        id=str(request_id),
        user_id=user.id,
        course_id=course_id,
        job_id=job.id,
        filename=name,
        source_path=str(path),
        source_hash=digest,
    )
    try:
        db.add(job)
        db.flush()
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        storage.remove(path)
        raise
    return response(db, row)


@router.get("/{capture_id}")
def get(
    capture_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return response(db, owned(db, user, capture_id))


@router.get("/{capture_id}/file")
def source(
    capture_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    row = owned(db, user, capture_id)
    path = LocalFileStorage(Path(get_settings().storage_root)).checked(
        Path(row.source_path)
    )
    if not path.is_file():
        raise HTTPException(404, "原文件不可用")
    return FileResponse(
        path, filename=row.filename, media_type="application/octet-stream"
    )


class Organize(BaseModel):
    request_id: UUID
    text: str = Field(min_length=1, max_length=16000)
    mode: Literal["format", "summary", "outline"]
    model: str
    confirmed: Literal[True]


@router.post("/{capture_id}/organize")
def organize(
    capture_id: str,
    payload: Organize,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned(db, user, capture_id)
    raise HTTPException(410, DISABLED_REASON)


@router.delete("/{capture_id}", status_code=204)
def remove(
    capture_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    lock_owner(db, user.id)
    row = owned(db, user, capture_id)
    job = db.get(ProcessingJob, row.job_id)
    path = Path(row.source_path)
    db.delete(row)
    db.flush()
    db.delete(job)
    db.commit()
    try:
        LocalFileStorage(Path(get_settings().storage_root)).remove(path)
    except PermissionError:
        # A Windows decoder may still hold the original; the worker removes it on exit.
        pass
