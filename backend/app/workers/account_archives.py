"""Account tasks never repeat a restore after lease expiry without user action."""

from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select, update
from ..core.database import SessionLocal
from ..core.storage import InsufficientStorage
from ..models import AccountArchive, ProcessingJob, User
from ..models.base import utc_now
from ..services import account_backups as service

KINDS = ["ACCOUNT_BACKUP", "ACCOUNT_RESTORE"]


def claim(db):
    expired = db.scalars(
        select(ProcessingJob).where(
            ProcessingJob.type.in_(KINDS),
            ProcessingJob.status == "RUNNING",
            (ProcessingJob.lease_until < utc_now())
            | ProcessingJob.lease_until.is_(None),
        )
    ).all()
    for job in expired:
        changed = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job.id,
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_token == job.lease_token,
            )
            .values(
                status="FAILED",
                error="备份/恢复任务中断，请核对账户后重新发起；不会自动重放",
                lease_token=None,
                lease_until=None,
            )
        )
        if changed.rowcount:
            row = db.get(AccountArchive, job.resource_id)
            if row and row.user_id == job.user_id:
                service.cleanup_restore(row.user_id, row.id)
                service.archive_path(row.user_id, row.id).unlink(missing_ok=True)
                service.archive_path(row.user_id, row.id, ".input.zip").unlink(
                    missing_ok=True
                )
    db.commit()
    db.expire_all()
    candidate = db.scalar(
        select(ProcessingJob)
        .join(AccountArchive, AccountArchive.id == ProcessingJob.resource_id)
        .where(
            ProcessingJob.type.in_(KINDS),
            ProcessingJob.status == "QUEUED",
            ProcessingJob.attempt_count < 1,
            AccountArchive.user_id == ProcessingJob.user_id,
            AccountArchive.job_id == ProcessingJob.id,
        )
        .order_by(ProcessingJob.created_at, ProcessingJob.id)
        .limit(1)
    )
    if not candidate:
        return None
    token = str(uuid4())
    changed = db.execute(
        update(ProcessingJob)
        .where(ProcessingJob.id == candidate.id, ProcessingJob.status == "QUEUED")
        .values(
            status="RUNNING",
            progress=10,
            attempt_count=1,
            lease_token=token,
            lease_until=utc_now() + timedelta(seconds=180),
        )
    )
    db.commit()
    if changed.rowcount:
        db.expire_all()
        return db.get(ProcessingJob, candidate.id)


def run_archive_once():
    with SessionLocal() as db:
        job = claim(db)
        if not job:
            return False
        job_id, token = job.id, job.lease_token
        row = db.get(AccountArchive, job.resource_id)
        record_id, user_id, purpose = row.id, row.user_id, row.purpose
        output = service.archive_path(user_id, record_id)
        result, error = None, None
        try:
            if purpose == "restore":
                lock = db.execute(
                    update(ProcessingJob)
                    .where(
                        ProcessingJob.id == job_id,
                        ProcessingJob.status == "RUNNING",
                        ProcessingJob.lease_token == token,
                        ProcessingJob.lease_until > utc_now(),
                    )
                    .values(progress=25)
                    .execution_options(synchronize_session=False)
                )
                if not lock.rowcount:
                    db.rollback()
                    return True
                db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(updated_at=User.updated_at)
                )
                db.connection().exec_driver_sql("PRAGMA defer_foreign_keys=ON")
                result = {"counts": service.restore_package(db, user_id, row)}
                db.flush()
            else:
                result = service.export_package(db, user_id, output)
                db.rollback()
        except (ValueError, InsufficientStorage) as exc:
            error = str(exc)[:300]
            db.rollback()
        except Exception:
            error = "备份或恢复失败：结构、文件完整性或关联校验未通过；未覆盖已有数据"
            db.rollback()
        try:
            locked = db.execute(
                update(ProcessingJob)
                .where(
                    ProcessingJob.id == job_id,
                    ProcessingJob.status == "RUNNING",
                    ProcessingJob.lease_token == token,
                    ProcessingJob.lease_until > utc_now(),
                )
                .values(progress=90)
                .execution_options(synchronize_session=False)
            )
            if not locked.rowcount:
                db.rollback()
                if purpose == "restore":
                    service.cleanup_restore(user_id, record_id)
                else:
                    output.unlink(missing_ok=True)
                return True
            db.expire_all()
            job, row = db.get(ProcessingJob, job_id), db.get(AccountArchive, record_id)
            if not error and purpose == "export":
                service.active_sources(db, user_id, result["sources"])
                row.artifact_path = str(output)
                row.sha256, row.size_bytes, row.sources = (
                    result["sha256"],
                    result["size_bytes"],
                    result["sources"],
                )
            row.counts = result["counts"] if not error else {}
            job.status = "FAILED" if error else "SUCCEEDED"
            job.error, job.progress = error, 100 if not error else 0
            job.lease_token, job.lease_until = None, None
            db.commit()
        except Exception:
            db.rollback()
            service.cleanup_restore(user_id, record_id)
            output.unlink(missing_ok=True)
            # Persist a terminal state without exposing SQL/path details.
            db.execute(
                update(ProcessingJob)
                .where(
                    ProcessingJob.id == job_id,
                    ProcessingJob.status == "RUNNING",
                    ProcessingJob.lease_token == token,
                )
                .values(
                    status="FAILED",
                    error="备份/恢复提交失败，所有业务写入已回滚",
                    lease_token=None,
                    lease_until=None,
                )
            )
            db.commit()
        finally:
            if purpose == "restore":
                input_path = service.archive_path(user_id, record_id, ".input.zip")
                input_path.unlink(missing_ok=True)
            if error:
                service.cleanup_restore(user_id, record_id)
                output.unlink(missing_ok=True)
        return True
