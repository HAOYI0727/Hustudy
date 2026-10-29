"""Single-dispatch consented extraction. No automatic remote retry or paid fallback."""

from datetime import timedelta, timezone
import json
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select, update, exists
from ..core.database import SessionLocal
from ..models import PastPaper, ProcessingJob, PastQuestion
from ..models.base import utc_now
from ..ai.providers import ProviderFailure
from ..services import bank_ai, bank_topic_ai, question_bank as bank
from ..services.courses import owned_course


def run_bank_ai_once():
    with SessionLocal() as db:
        db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.type == "BANK_EXTRACT",
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_until < utc_now(),
            )
            .values(
                status="FAILED",
                error="AI识别中断；不会自动重发，请重新预览确认",
                lease_token=None,
                lease_until=None,
            )
        )
        db.commit()
        jid = db.scalar(
            select(ProcessingJob.id)
            .where(
                ProcessingJob.type == "BANK_EXTRACT", ProcessingJob.status == "QUEUED"
            )
            .order_by(ProcessingJob.created_at)
            .limit(1)
        )
        if not jid:
            return False
        if db.scalar(
            select(ProcessingJob.id)
            .where(
                ProcessingJob.type.in_(["BANK_EXTRACT", "AI_ANALYSIS"]),
                ProcessingJob.status == "RUNNING",
            )
            .limit(1)
        ):
            return False
        token = str(uuid4())
        active = ProcessingJob.__table__.alias("active_bank_ai")
        changed = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == jid,
                ProcessingJob.status == "QUEUED",
                ~exists(
                    select(active.c.id).where(
                        active.c.type.in_(["BANK_EXTRACT", "AI_ANALYSIS"]),
                        active.c.status == "RUNNING",
                    )
                ),
            )
            .values(
                status="RUNNING",
                lease_token=token,
                lease_until=utc_now() + timedelta(seconds=180),
                attempt_count=1,
            )
        )
        db.commit()
        if changed.rowcount != 1:
            return True
        job = db.get(ProcessingJob, jid)
        pid = job.resource_id
        owner_id = job.user_id
        row = db.get(PastPaper, pid)
        try:
            if not row or row.user_id != owner_id:
                raise ValueError("任务归属不匹配")
            meta = json.loads(row.bank_meta_json)
            topic_mode = meta.get("ai_topic_index", {}).get("job_id") == jid
            scope = meta["ai_topic_index" if topic_mode else "ai_extract"]
            if not scope.get("consented_at") or scope.get("job_id") != jid:
                raise ValueError("未明确确认发送")
            (bank_topic_ai if topic_mode else bank_ai).validate_scope(db, row, scope)
            content = row.content
            db.rollback()
        except Exception:
            job.status, job.error = "FAILED", "识别预览或来源已经无效，未发送"
            job.lease_token, job.lease_until = None, None
            db.commit()
            return True
    output, error = None, None

    def before_batch(index):
        with SessionLocal() as check_db:
            current = check_db.get(ProcessingJob, jid)
            if (
                not current
                or current.status != "RUNNING"
                or current.lease_token != token
                or not current.lease_until
                or current.lease_until.replace(tzinfo=timezone.utc) <= utc_now()
            ):
                raise ProviderFailure("CANCELLED", "归类任务已取消或失效")
            bank_topic_ai.validate_scope(check_db, check_db.get(PastPaper, pid), scope)
            current.lease_until = utc_now() + timedelta(seconds=180)
            current.progress = min(
                95, 5 + index * 90 // max(1, scope.get("batch_count", 1))
            )
            check_db.commit()

    try:
        output = (
            bank_topic_ai.classify(
                scope,
                bank_ai.provider(owner_id, scope.get("credential_revision")),
                before_batch=before_batch,
            )
            if topic_mode
            else bank_ai.extract(
                content, bank_ai.provider(owner_id, scope.get("credential_revision"))
            )
        )
    except ProviderFailure as exc:
        error = f"{exc.code}：{exc.message}"
    except Exception:
        error = "AI识别失败，未导入；不会自动重发，请检查接口或使用本地规则"
    with SessionLocal() as db:
        job = db.get(ProcessingJob, jid)
        if (
            not job
            or job.status != "RUNNING"
            or job.lease_token != token
            or not job.lease_until
            or job.lease_until.replace(tzinfo=timezone.utc) <= utc_now()
        ):
            return True
        row = db.get(PastPaper, pid)
        try:
            owned_course(db, row.user_id, row.course_id, lock=True)
            bank.no_active_attempt(db, row.user_id, row.course_id)
            (bank_topic_ai if topic_mode else bank_ai).validate_scope(db, row, scope)
            if error:
                raise ValueError(error)
            if topic_mode:
                bank_topic_ai.apply(db, row, scope, output)
            else:
                if db.scalar(
                    select(PastQuestion.id).where(PastQuestion.paper_id == pid).limit(1)
                ):
                    raise ValueError("识别结果已入库，拒绝重复写入")
                bank.populate_bank(
                    db,
                    row.user_id,
                    row.course_id,
                    row,
                    content,
                    output,
                    scope["sources"],
                    scope["default_topic_ids"],
                )
            job.status, job.progress, job.error = "SUCCEEDED", 100, None
        except (HTTPException, ValueError) as exc:
            db.rollback()
            job = db.get(ProcessingJob, jid)
            if job.status != "RUNNING" or job.lease_token != token:
                return True
            job.status, job.error = (
                "FAILED",
                str(exc.detail)[:800]
                if isinstance(exc, HTTPException)
                else str(exc)[:800],
            )
        except Exception:
            db.rollback()
            job = db.get(ProcessingJob, jid)
            job.status, job.error = "FAILED", "识别结果校验或保存失败，未采用结果"
        job.lease_token, job.lease_until = None, None
        db.commit()
    return True
