"""Course package jobs share the SQLite lease protocol with the material worker."""

from datetime import timedelta
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select, update
from ..core.database import SessionLocal
from ..core.config import get_settings
from ..models import MaterialExport, ProcessingJob, Course
from ..models.base import utc_now
from ..services.material_exports import build_package, cleanup


def claim_export(db):
    expired = db.scalars(
        select(ProcessingJob).where(
            ProcessingJob.type == "MATERIAL_EXPORT",
            ProcessingJob.status == "RUNNING",
            (ProcessingJob.lease_until < utc_now())
            | ProcessingJob.lease_until.is_(None),
        )
    ).all()
    for row in expired:
        stale_token = row.lease_token
        recovered = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == row.id,
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_token == row.lease_token,
                (ProcessingJob.lease_until < utc_now())
                | ProcessingJob.lease_until.is_(None),
            )
            .values(
                status="QUEUED" if row.attempt_count < row.max_attempts else "FAILED",
                error="导出worker租约过期，等待恢复"
                if row.attempt_count < row.max_attempts
                else "导出尝试次数已达上限",
                lease_token=None,
                lease_until=None,
                progress=0,
            )
            .execution_options(synchronize_session=False)
        )
        if recovered.rowcount == 1 and stale_token:
            record = db.get(MaterialExport, row.resource_id)
            if record and record.user_id == row.user_id:
                stale_output = (
                    Path(get_settings().storage_root)
                    / row.user_id
                    / record.course_id
                    / "exports"
                    / (row.id + "-" + stale_token + ".zip")
                )
                cleanup(stale_output)
    db.commit()
    db.expire_all()
    for job_id in db.scalars(
        select(ProcessingJob.id)
        .where(
            ProcessingJob.type == "MATERIAL_EXPORT",
            ProcessingJob.status == "QUEUED",
            ProcessingJob.attempt_count < ProcessingJob.max_attempts,
        )
        .order_by(ProcessingJob.created_at, ProcessingJob.id)
        .limit(10)
    ).all():
        token = str(uuid4())
        result = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.status == "QUEUED",
                ProcessingJob.attempt_count < ProcessingJob.max_attempts,
            )
            .values(
                status="RUNNING",
                lease_token=token,
                lease_until=utc_now() + timedelta(seconds=180),
                attempt_count=ProcessingJob.attempt_count + 1,
                progress=10,
                error=None,
            )
        )
        db.commit()
        if result.rowcount == 1:
            db.expire_all()
            return db.get(ProcessingJob, job_id)
    return None


def run_export_once():
    with SessionLocal() as db:
        job = claim_export(db)
        if not job:
            return False
        job_id, token, user_id = job.id, job.lease_token, job.user_id
        row = db.get(MaterialExport, job.resource_id)
        if not row or row.user_id != user_id:
            job.status = "CANCELLED"
            job.error = "导出记录已移除"
            job.lease_token = None
            job.lease_until = None
            db.commit()
            return True
        course_id = row.course_id
        output = (
            Path(get_settings().storage_root)
            / user_id
            / course_id
            / "exports"
            / (job_id + "-" + token + ".zip")
        )
        db.commit()
        result, error = None, None
        try:
            result = build_package(db, row, output)
        except (ValueError, FileNotFoundError) as exc:
            error = (
                str(exc)
                if isinstance(exc, ValueError)
                else "原件或图片文件缺失，请排查后重试"
            )
        except Exception:
            error = "导出失败：课程来源不可用或文件读写异常，请检查存储与课程后重试"
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
        row = db.get(MaterialExport, job.resource_id)
        course = db.get(Course, course_id)
        if not row or not course or course.user_id != user_id or course.deleted_at:
            job.status = "CANCELLED"
            job.error = "课程或导出记录已移除"
            cleanup(output)
        elif error:
            job.status = "FAILED"
            job.error = error
            cleanup(output)
        else:
            row.zip_path = str(output)
            row.sha256 = result["sha256"]
            row.size_bytes = result["size_bytes"]
            row.snapshot_at = result["snapshot_at"]
            row.sources_json = result["sources"]
            row.counts_json = result["counts"]
            job.status = "SUCCEEDED"
            job.error = None
            job.progress = 100
        job.lease_token = None
        job.lease_until = None
        try:
            db.commit()
        except Exception:
            db.rollback()
            cleanup(output)
            raise
        return True
