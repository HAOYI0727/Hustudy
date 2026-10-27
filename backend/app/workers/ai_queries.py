"""Durable consented AI jobs; no network retry after timeout or lost lease."""

from datetime import timedelta
import json
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select, update, exists
from ..core.database import SessionLocal
from ..core.config import get_user_settings
from ..models import RemoteQuery, ProcessingJob, AIResult
from ..models.base import utc_now
from ..ai.providers import ZhipuProvider, ProviderFailure, PROMPT_VERSION
from ..services.courses import owned_course
from ..services.ai_context import validate_context
from ..schemas.study_reports import report_envelope, REPORT_PROMPT_VERSION
from ..ai.study_reports import generate_report
from ..schemas.question_drafts import candidate_envelope, CANDIDATE_PROMPT_VERSION
from ..ai.question_drafts import generate_candidates
from ..services.remote_ai import validate_request_dependencies
from ..services.m2_execution import Execution, information


def claim(db):
    from ..services.m2_execution import expire_queued

    expire_queued(db)
    own_resource = exists(
        select(RemoteQuery.id).where(
            RemoteQuery.id == ProcessingJob.resource_id,
            RemoteQuery.user_id == ProcessingJob.user_id,
        )
    )
    db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.type == "AI_ANALYSIS",
            own_resource,
            ProcessingJob.status == "RUNNING",
            (ProcessingJob.lease_until < utc_now())
            | ProcessingJob.lease_until.is_(None),
        )
        .values(
            status="FAILED",
            lease_token=None,
            lease_until=None,
            error="AI运行租约过期；请重新预览确认，系统不会自动重复发送",
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    db.expire_all()
    candidate = db.scalar(
        select(ProcessingJob.id)
        .where(
            ProcessingJob.type == "AI_ANALYSIS",
            own_resource,
            ProcessingJob.status == "QUEUED",
            ProcessingJob.attempt_count < ProcessingJob.max_attempts,
        )
        .order_by(ProcessingJob.created_at, ProcessingJob.id)
        .limit(1)
    )
    if not candidate:
        return None
    # Different workers serialize globally before using the same provider account.
    active = ProcessingJob.__table__.alias("active_ai_job")
    token = str(uuid4())
    changed = db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.id == candidate,
            ProcessingJob.status == "QUEUED",
            ~exists(
                select(active.c.id).where(
                    active.c.type.in_(["AI_ANALYSIS", "BANK_EXTRACT"]),
                    active.c.status == "RUNNING",
                )
            ),
        )
        .values(
            status="RUNNING",
            attempt_count=ProcessingJob.attempt_count + 1,
            lease_token=token,
            lease_until=utc_now() + timedelta(seconds=180),
            progress=10,
            error=None,
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    db.expire_all()
    return db.get(ProcessingJob, candidate) if changed.rowcount else None


def run_ai_once():
    with SessionLocal() as db:
        job = claim(db)
        if not job:
            return False
        job_id, token, user_id = job.id, job.lease_token, job.user_id
        row = db.get(RemoteQuery, job.resource_id)
        error, output, status = None, None, None
        report = None
        candidate = None
        prompt_version = PROMPT_VERSION
        try:
            if (
                not row
                or row.user_id != user_id
                or row.job_id != job_id
                or not row.consented_at
            ):
                raise ProviderFailure("INVALID_CONSENT", "任务没有有效发送确认")
            report = report_envelope(row.query)
            candidate = candidate_envelope(row.query)
            if candidate:
                raise ProviderFailure(
                    "RETIRED_GENERATION", "AI练习生成已停用，请从用户题库抽题"
                )
            if report:
                prompt_version = REPORT_PROMPT_VERSION
            elif candidate:
                prompt_version = CANDIDATE_PROMPT_VERSION
            owned_course(db, user_id, row.course_id, lock=True)
            validate_context(db, user_id, row.course_id, row.sources)
            validate_request_dependencies(db, row)
            s = get_user_settings(user_id)
            if s.llm_provider not in {"zhipu", "compatible"} or not s.zhipu_api_key.get_secret_value():
                raise ProviderFailure(
                    "NOT_CONFIGURED", "智谱配置已停用，请重新配置后预览"
                )
            if row.model != s.llm_model or row.endpoint != s.llm_endpoint:
                raise ProviderFailure(
                    "CONFIG_CHANGED", "模型配置已变化，请重新预览确认"
                )
            current = db.get(ProcessingJob, job_id)
            if current.status != "RUNNING" or current.lease_token != token:
                db.rollback()
                return True
            row.dispatched_at = utc_now()
            query, sources = row.query, row.sources
            db.commit()
            provider = ZhipuProvider(s)
            from ..services.m2_supplements import context

            provider.m2_supplement = context(sources)
            execution = Execution(db, job, row, token, s)
            provider.m2_execution = execution
            # No SQLite write lock is held while waiting on the remote service.
            if report and report.batched:
                from ..services.report_batches import run_step

                return run_step(db, job, row, token, provider, report)
            from ..services import qa_batches

            if qa_batches.batched(row):
                return qa_batches.run_step(db, job, row, token, provider)
            if candidate:
                output, status = generate_candidates(provider, candidate, sources)
            elif report:
                output, status = generate_report(provider, report, sources)
            else:
                output, status = provider.answer(query, sources)
                output["coverage"] = qa_batches.plan(row).get("coverage")
            from ..services.m2_supplements import attach_output

            attach_output(output, sources)
            execution.check_deadline()
        except HTTPException as failure:
            db.rollback()
            changed_config = str(failure.detail).startswith("本账户API配置")
            error = ProviderFailure(
                "CONFIG_CHANGED" if changed_config else "SOURCE_UNAVAILABLE",
                "本账户API配置已变化，请重新预览确认"
                if changed_config
                else "来源已删除、撤回或变化，未生成可用回答",
            )
        except ProviderFailure as failure:
            db.rollback()
            error = failure
        except Exception:
            db.rollback()
            error = ProviderFailure(
                "PROVIDER_ERROR", "真实AI处理失败，请检查配置或重新预览"
            )
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
            return True
        db.expire_all()
        job = db.get(ProcessingJob, job_id)
        row = db.get(RemoteQuery, job.resource_id)
        if not row or row.user_id != user_id:
            job.status, job.error = "CANCELLED", "AI请求已移除"
        else:
            try:
                owned_course(db, user_id, row.course_id)
                validate_context(db, user_id, row.course_id, row.sources)
                validate_request_dependencies(db, row)
            except HTTPException as failure:
                if error is None:
                    changed_config = str(failure.detail).startswith("本账户API配置")
                    error = ProviderFailure(
                        "CONFIG_CHANGED" if changed_config else "SOURCE_UNAVAILABLE",
                        "本账户API配置已变化，远程结果未采纳"
                        if changed_config
                        else "请求中的来源已失效，远程结果未采纳",
                    )
            if error:
                status = "provider_error"
                output = {
                    "message": error.message,
                    "error_code": error.code,
                    "citations": [],
                    "model": row.model,
                    "model_notice": "本次未生成可用结果，请查看具体原因；不会伪装成演示答案",
                    "provider_code": error.provider_code,
                    "retry_after_seconds": error.retry_after_seconds,
                }
                if report:
                    output.update(
                        {
                            "result_kind": "study_report",
                            "coverage": report.coverage,
                            "scope_version_ids": [
                                str(v) for v in report.scope_version_ids
                            ],
                        }
                    )
                elif candidate:
                    output.update(
                        {
                            "result_kind": "question_drafts",
                            "question_drafts": [],
                            "coverage": candidate.coverage,
                            "request": candidate.request.model_dump(mode="json"),
                            "exam_context": candidate.exam_context,
                        }
                    )
                job.status, job.error = "FAILED", error.message
            else:
                job.status, job.error, job.progress = "SUCCEEDED", None, 100
            output["execution"] = information(db, row)
            result = AIResult(
                user_id=user_id,
                course_id=row.course_id,
                query=report.goal
                if report
                else candidate.request.goal
                if candidate
                else row.query,
                status=status,
                model_mode="real",
                prompt_version=prompt_version,
                result_json=json.dumps(output, ensure_ascii=False),
            )
            db.add(result)
            db.flush()
            row.result_id = result.id
        job.lease_token = None
        job.lease_until = None
        db.commit()
        return True
