"""Owned, idempotent M3 ZIP lifecycle."""

from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select, update, func
from ..core.config import get_settings
from ..core.storage import LocalFileStorage
from ..models import NoteExport, Note, User, ProcessingJob
from ..schemas.material import JobResponse
from ..schemas.note_exports import NoteExportResponse
from .note_package import available_notes, sources_available, hash_file, cleanup
from .note_export_names import archive_filename


def filename(db, row):
    return archive_filename(row.created_at, db.get(User, row.user_id).timezone)


def owned_export(db, export_id, user_id):
    row = db.scalar(
        select(NoteExport).where(
            NoteExport.id == export_id, NoteExport.user_id == user_id
        )
    )
    if not row:
        raise HTTPException(404, "笔记导出记录不存在")
    return row


def lock_owner(db, user_id):
    db.execute(update(User).where(User.id == user_id).values(id=User.id))
    db.expire_all()


def response(db, row):
    job = db.get(ProcessingJob, row.job_id)
    availability = "pending"
    if job.status == "SUCCEEDED":
        availability = (
            "active"
            if row.zip_path
            and Path(row.zip_path).is_file()
            and sources_available(db, row.user_id, row.sources_json)
            else "unavailable"
        )
    return NoteExportResponse(
        layout="simple" if row.sources_json.get("request") else "legacy",
        filename=filename(db, row),
        id=row.id,
        created_at=row.created_at,
        snapshot_at=row.snapshot_at,
        sha256=row.sha256,
        size_bytes=row.size_bytes,
        counts=row.counts_json,
        availability=availability,
        job=JobResponse.model_validate(job, from_attributes=True),
    )


def active_job(db, user_id, exclude=None):
    return db.scalar(
        select(ProcessingJob.id).where(
            ProcessingJob.user_id == user_id,
            ProcessingJob.type == "NOTE_EXPORT",
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
            ProcessingJob.id != exclude if exclude else True,
        )
    )


def create_export(db, user_id, request_id, note_ids=None, include_images=True):
    requested = sorted(note_ids) if note_ids is not None else None
    lock_owner(db, user_id)
    existing = db.get(NoteExport, request_id)
    if existing:
        if existing.user_id != user_id:
            raise HTTPException(404, "请求标识不可用")
        previous = existing.sources_json.get("request", {})
        if (
            previous.get("note_ids") != requested
            or previous.get("include_images", False) != include_images
        ):
            raise HTTPException(409, "该请求已用于其他导出范围，请重新选择后导出")
        db.commit()
        return response(db, existing)
    if db.get(ProcessingJob, request_id):
        raise HTTPException(409, "请求标识已使用，请使用新的标识")
    if active_job(db, user_id):
        raise HTTPException(409, "已有笔记导出正在处理，请查看导出记录")
    if (
        db.scalar(
            select(func.count())
            .select_from(NoteExport)
            .where(NoteExport.user_id == user_id)
        )
        >= 20
    ):
        raise HTTPException(409, "最多保留20条笔记导出记录，请先移除旧记录")
    scope = available_notes(user_id)
    if requested is not None:
        scope = scope & Note.id.in_(requested)
    selected = list(
        db.scalars(select(Note.id).where(scope).order_by(Note.id).limit(2001))
    )
    if requested is not None and len(selected) != len(requested):
        raise HTTPException(404, "所选笔记已删除或不可访问，请刷新列表后重选")
    if not selected:
        raise HTTPException(409, "还没有可导出的已保存笔记")
    if len(selected) > 2000:
        raise HTTPException(422, "每次最多导出2000篇笔记，请分批选择")
    db.add(
        ProcessingJob(
            id=request_id, user_id=user_id, type="NOTE_EXPORT", resource_id=request_id
        )
    )
    db.flush()
    row = NoteExport(
        id=request_id,
        user_id=user_id,
        job_id=request_id,
        sources_json={
            "request": {
                "note_ids": requested,
                "selected_ids": selected,
                "include_images": include_images,
            }
        },
    )
    db.add(row)
    db.commit()
    return response(db, row)


def retry_export(db, export_id, user_id):
    lock_owner(db, user_id)
    row = owned_export(db, export_id, user_id)
    job = db.get(ProcessingJob, row.job_id)
    if job.status in {"QUEUED", "RUNNING"}:
        db.commit()
        return response(db, row)
    if job.status != "FAILED" or job.attempt_count >= job.max_attempts:
        raise HTTPException(409, "仅未达尝试上限的失败导出可以重试")
    if active_job(db, user_id, job.id):
        raise HTTPException(409, "已有其他笔记导出正在处理")
    job.status, job.progress, job.error = "QUEUED", 0, None
    job.lease_token, job.lease_until = None, None
    db.commit()
    return response(db, row)


def remove_export(db, export_id, user_id):
    lock_owner(db, user_id)
    row = owned_export(db, export_id, user_id)
    job = db.get(ProcessingJob, row.job_id)
    if job.status in {"QUEUED", "RUNNING"}:
        job.status, job.error = "CANCELLED", "笔记导出记录已移除"
        job.lease_token, job.lease_until = None, None
    stored = row.zip_path
    db.delete(row)
    db.commit()
    if stored:
        cleanup(
            LocalFileStorage(Path(get_settings().storage_root)).checked(Path(stored))
        )


def download_path(db, row):
    if db.get(ProcessingJob, row.job_id).status != "SUCCEEDED" or not row.zip_path:
        raise HTTPException(409, "笔记包尚未成功生成")
    if not sources_available(db, row.user_id, row.sources_json):
        raise HTTPException(404, "包内笔记、图片或来源已删除/撤回，请重新导出")
    root = Path(get_settings().storage_root)
    try:
        path = LocalFileStorage(root).checked(Path(row.zip_path))
        if (
            not path.resolve().is_relative_to(
                (root / row.user_id / "note-exports").resolve()
            )
            or not path.is_file()
        ):
            raise ValueError()
    except ValueError as exc:
        raise HTTPException(404, "笔记包文件不可用") from exc
    if path.stat().st_size != row.size_bytes or hash_file(path) != row.sha256:
        raise HTTPException(409, "笔记包文件校验失败，请重新导出")
    return path
