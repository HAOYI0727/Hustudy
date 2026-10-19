"""Durable M3 jobs with bounded leases and late-writer rejection."""

from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select, update
from ..core.database import SessionLocal
from ..models import NoteExport, ProcessingJob
from ..models.base import utc_now
from ..services.note_package import (
    build_package,
    output_path,
    cleanup,
    sources_available,
)


def claim_export(db):
    for job in db.scalars(
        select(ProcessingJob).where(
            ProcessingJob.type == "NOTE_EXPORT",
            ProcessingJob.status == "RUNNING",
            (ProcessingJob.lease_until < utc_now())
            | ProcessingJob.lease_until.is_(None),
        )
    ).all():
        token = job.lease_token
        result = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job.id,
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_token == token,
                (ProcessingJob.lease_until < utc_now())
                | ProcessingJob.lease_until.is_(None),
            )
            .values(
                status="QUEUED" if job.attempt_count < job.max_attempts else "FAILED",
                error="笔记导出租约过期"
                if job.attempt_count < job.max_attempts
                else "笔记导出尝试次数已达上限",
                progress=0,
                lease_token=None,
                lease_until=None,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount == 1 and token:
            cleanup(output_path(job.user_id, job.id, token))
    db.commit()
    db.expire_all()
    for job_id in db.scalars(
        select(ProcessingJob.id)
        .where(
            ProcessingJob.type == "NOTE_EXPORT",
            ProcessingJob.status == "QUEUED",
            ProcessingJob.attempt_count < ProcessingJob.max_attempts,
        )
        .order_by(ProcessingJob.created_at, ProcessingJob.id)
        .limit(10)
    ).all():
        result = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.status == "QUEUED",
                ProcessingJob.attempt_count < ProcessingJob.max_attempts,
            )
            .values(
                status="RUNNING",
                lease_token=str(uuid4()),
                lease_until=utc_now() + timedelta(seconds=180),
                attempt_count=ProcessingJob.attempt_count + 1,
                progress=10,
                error=None,
            )
        )
        db.commit()
        if result.rowcount == 1:
            return db.get(ProcessingJob, job_id)
    return None


def run_note_export_once():
    with SessionLocal() as db:
        job = claim_export(db)
        if not job:
            return False
        job_id, user_id, token = job.id, job.user_id, job.lease_token
        output = output_path(user_id, job_id, token)
        record = db.get(NoteExport, job.resource_id)
        if not record or record.user_id != user_id:
            job.status, job.error = "CANCELLED", "笔记导出记录已移除"
            job.lease_token, job.lease_until = None, None
            db.commit()
            return True
        options = record.sources_json.get("request")
        db.commit()
        result, error = None, None
        try:
            result = build_package(db, user_id, output, options=options)
        except ValueError as exc:
            error = str(exc)
        except Exception:
            error = "笔记导出失败：文件缺失或读写异常，请检查存储后重试"
        db.rollback()
        locked = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_token == token,
            )
            .values(progress=90)
        )
        if locked.rowcount != 1:
            db.rollback()
            cleanup(output)
            return True
        db.expire_all()
        job = db.get(ProcessingJob, job_id)
        record = db.get(NoteExport, job_id)
        if not record:
            job.status, job.error = "CANCELLED", "笔记导出记录已移除"
        elif error:
            job.status, job.error = "FAILED", error
        elif not sources_available(db, user_id, result["sources"]):
            job.status, job.error = "FAILED", "生成期间来源已删除或撤回，请重新导出"
        else:
            record.zip_path, record.sha256, record.size_bytes = (
                str(output),
                result["sha256"],
                result["size_bytes"],
            )
            record.snapshot_at, record.sources_json, record.counts_json = (
                result["snapshot_at"],
                result["sources"] | ({"request": options} if options else {}),
                result["counts"],
            )
            job.status, job.error, job.progress = "SUCCEEDED", None, 100
        if job.status != "SUCCEEDED":
            cleanup(output)
        job.lease_token, job.lease_until = None, None
        try:
            db.commit()
        except Exception:
            db.rollback()
            cleanup(output)
            raise
        return True
