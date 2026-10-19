"""Single-dispatch local recognition; legacy AI jobs are cancelled without dispatch."""

from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import uuid4
from sqlalchemy import select, update
from ..core.config import get_settings
from ..core.database import SessionLocal
from ..core.storage import LocalFileStorage
from ..models import NoteCapture, ProcessingJob, Course
from ..models.base import utc_now
from ..services.note_ai_config import DISABLED_REASON
from ..services.note_folders import lock_owner


def recognize_isolated(path):
    with tempfile.TemporaryDirectory(prefix="hustudy-capture-") as folder:
        output = Path(folder) / "result.json"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "app.services.note_recognition",
                str(path),
                str(output),
            ],
            timeout=360,
            check=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])},
        )
        if output.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("识别结果超过预算，请拆分文件")
        result = json.loads(output.read_text(encoding="utf-8"))
        if "error" in result:
            raise ValueError(result["error"])
        return result["result"]


def run_capture_once():
    with SessionLocal() as db:
        db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.type == "NOTE_ORGANIZE",
                ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
            )
            .values(
                status="CANCELLED",
                error=DISABLED_REASON,
                lease_token=None,
                lease_until=None,
            )
        )
        db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.type == "NOTE_CAPTURE",
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_until < utc_now(),
            )
            .values(
                status="FAILED",
                error="识别被中断；未自动重试，请核对后重新上传",
                lease_token=None,
                lease_until=None,
            )
        )
        db.commit()
        job_id = db.scalar(
            select(ProcessingJob.id)
            .where(
                ProcessingJob.type == "NOTE_CAPTURE", ProcessingJob.status == "QUEUED"
            )
            .order_by(ProcessingJob.created_at)
            .limit(1)
        )
        if not job_id:
            return False
        token = str(uuid4())
        claimed = db.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id == job_id, ProcessingJob.status == "QUEUED")
            .values(
                status="RUNNING",
                lease_token=token,
                lease_until=utc_now() + timedelta(seconds=420),
                attempt_count=1,
            )
        )
        db.commit()
        if claimed.rowcount != 1:
            return True
        job = db.get(ProcessingJob, job_id)
        row = db.get(NoteCapture, job.resource_id)
        course = db.get(Course, row.course_id) if row else None
        if not row or row.user_id != job.user_id or not course or course.deleted_at:
            job.status, job.error = "CANCELLED", "来源课程或任务已删除"
            db.commit()
            return True
        user_id = job.user_id
        path = LocalFileStorage(Path(get_settings().storage_root)).checked(
            Path(row.source_path)
        )
        db.rollback()
    result, error = None, None
    try:
        result = recognize_isolated(path)
    except subprocess.TimeoutExpired:
        error = "识别超过6分钟，请拆分文件后重试"
    except ValueError as exc:
        error = str(exc)
    except Exception:
        error = "处理失败，请检查文件及本地识别组件；不会自动重试"
    with SessionLocal() as db:
        lock_owner(db, user_id)
        changed = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.lease_token == token,
                ProcessingJob.status == "RUNNING",
            )
            .values(
                status="FAILED" if error else "SUCCEEDED",
                error=error,
                progress=100,
                lease_token=None,
                lease_until=None,
            )
        )
        if changed.rowcount:
            job = db.get(ProcessingJob, job_id)
            row = db.get(NoteCapture, job.resource_id)
            course = db.get(Course, row.course_id) if row else None
            if row and course and not course.deleted_at and result:
                row.result = result
            elif not row or not course or course.deleted_at:
                job.status = "CANCELLED"
        db.commit()
        if not changed.rowcount and not db.scalar(
            select(NoteCapture.id).where(NoteCapture.source_path == str(path))
        ):
            LocalFileStorage(Path(get_settings().storage_root)).remove(path)
    return True
