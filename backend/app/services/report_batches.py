"""Durable report steps stored as private AIResult checkpoints, no extra network merge."""

import json
from uuid import NAMESPACE_URL, uuid5
from fastapi import HTTPException
from sqlalchemy import select, update
from ..models import AIResult, ProcessingJob
from ..models.base import utc_now
from ..ai.providers import ProviderFailure
from ..ai.study_reports import generate_report
from ..schemas.study_reports import REPORT_PROMPT_VERSION, report_envelope
from .ai_material_scope import report_batches
from .ai_context import validate_context
from .courses import owned_course

CHECKPOINT_VERSION = "m2-report-checkpoint-v1"


def checkpoint_id(query_id, number):
    return str(uuid5(NAMESPACE_URL, f"hustudy/report/{query_id}/{number}"))


def checkpoints(db, row):
    return [
        db.get(AIResult, checkpoint_id(row.id, i))
        for i in range(len(report_batches(row.sources)))
    ]


def progress(db, row):
    report = report_envelope(row.query)
    if not report or not report.batched:
        return None
    steps = checkpoints(db, row)
    return {
        "total": len(steps),
        "completed": sum(bool(s and s.status == "grounded") for s in steps),
        "max_calls": len(steps),
        "chars": sum(len(s["text"]) for s in row.sources),
    }


def collection(db, row, report):
    sections, citations, usage = [], {}, {}
    for i, step in enumerate(checkpoints(db, row), 1):
        if not step or step.status != "grounded":
            continue
        data = json.loads(step.result_json)
        sections.append({"title": f"第{i}部分", "report": data["study_report"]})
        for citation in data["citations"]:
            citations[
                (citation["chunk_id"], citation["quote_hash"], citation["start_offset"])
            ] = citation
        for key, value in data.get("usage", {}).items():
            usage[key] = usage.get(key, 0) + value
    body = {
        "result_kind": "study_report",
        "model": row.model,
        "study_mode": report.study_mode,
        "review_status": "UNREVIEWED",
        "study_report_sections": sections,
        "citations": list(citations.values()),
        "coverage": report.coverage,
        "scope_version_ids": [str(v) for v in report.scope_version_ids],
        "model_notice": "分批学习报告 · 各部分独立依据原文生成，未作跨部分AI综合，仍需人工核实",
        "prompt_version": REPORT_PROMPT_VERSION,
        "usage": usage,
        "answer": "\n\n".join(
            f"# 第{i}部分\n\n{json.loads(step.result_json)['answer']}"
            for i, step in enumerate(checkpoints(db, row), 1)
            if step and step.status == "grounded"
        ),
    }
    from .m2_supplements import attach_output

    attach_output(body, row.sources)
    return body


def run_step(db, job, row, token, provider, report):
    def guard():
        changed = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job.id,
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_token == token,
                ProcessingJob.lease_until > utc_now(),
            )
            .values(progress=ProcessingJob.progress)
            .execution_options(synchronize_session=False)
        )
        return bool(changed.rowcount)

    if not guard():
        db.rollback()
        return True
    batches = report_batches(row.sources)
    steps = checkpoints(db, row)
    index = next(
        (i for i, step in enumerate(steps) if not step or step.status != "grounded"),
        None,
    )
    if index is None:
        raise ProviderFailure("INVALID_OUTPUT", "报告步骤已完成，请读取已保存结果")
    checkpoint = steps[index]
    if checkpoint is None:
        checkpoint = AIResult(
            id=checkpoint_id(row.id, index),
            user_id=row.user_id,
            course_id=row.course_id,
            query=f"report-step:{row.id}:{index}",
            status="provider_error",
            model_mode="real",
            prompt_version=CHECKPOINT_VERSION,
            result_json=json.dumps({"phase": "dispatching"}),
        )
        db.add(checkpoint)
    else:
        checkpoint.result_json = json.dumps({"phase": "dispatching"})
    row.dispatched_at = utc_now()
    db.commit()
    output, error = None, None
    try:
        output, status = generate_report(provider, report, batches[index])
        if execution := getattr(provider, "m2_execution", None):
            execution.check_deadline()
        if status != "grounded":
            raise ProviderFailure(
                "INSUFFICIENT_EVIDENCE",
                "该批资料不足以生成完整教学报告；已完成部分保留",
            )
    except ProviderFailure as failure:
        error = failure
    except Exception:
        error = ProviderFailure(
            "PROVIDER_ERROR", "本批生成失败；已完成部分保留，请检查后确认续跑"
        )
    db.expire_all()
    if not guard():
        db.rollback()
        return True
    current = db.get(ProcessingJob, job.id)
    try:
        owned_course(db, row.user_id, row.course_id, lock=True)
        validate_context(db, row.user_id, row.course_id, row.sources)
        from .remote_ai import validate_request_dependencies

        validate_request_dependencies(db, row)
    except HTTPException:
        error = ProviderFailure(
            "SOURCE_UNAVAILABLE", "资料已撤回或改变，本批结果未采纳"
        )
    checkpoint = db.get(AIResult, checkpoint_id(row.id, index))
    from .m2_execution import information

    if error:
        checkpoint.status = "provider_error"
        checkpoint.result_json = json.dumps(
            {"phase": "failed", "error_code": error.code, "message": error.message},
            ensure_ascii=False,
        )
        current.status, current.error = (
            "FAILED",
            f"第{index + 1}/{len(batches)}批：{error.message}",
        )
        body = collection(db, row, report)
        body["execution"] = information(db, row)
        body.update(
            {
                "message": current.error,
                "error_code": error.code,
                "provider_code": error.provider_code,
                "retry_after_seconds": error.retry_after_seconds,
                "partial": bool(body["study_report_sections"]),
            }
        )
        result = AIResult(
            user_id=row.user_id,
            course_id=row.course_id,
            query=report.goal,
            status="insufficient_evidence"
            if error.code == "INSUFFICIENT_EVIDENCE"
            and not body["study_report_sections"]
            else "provider_error",
            model_mode="real",
            prompt_version=REPORT_PROMPT_VERSION,
            result_json=json.dumps(body, ensure_ascii=False),
        )
        db.add(result)
        db.flush()
        row.result_id = result.id
    else:
        checkpoint.status = "grounded"
        output["execution"] = information(db, row)
        checkpoint.result_json = json.dumps(output, ensure_ascii=False)
        db.flush()
        done = sum(bool(s and s.status == "grounded") for s in checkpoints(db, row))
        current.progress = round(done / len(batches) * 100)
        if done < len(batches):
            current.status, current.error = "QUEUED", None
            body = collection(db, row, report)
            body["execution"] = information(db, row)
            body.update(
                {
                    "partial": True,
                    "error_code": "PARTIAL_REPORT",
                    "message": f"已完成{done}/{len(batches)}批，以下仅为已完成部分",
                }
            )
            draft_id = str(uuid5(NAMESPACE_URL, f"hustudy/report/{row.id}/progress"))
            draft = db.get(AIResult, draft_id)
            if draft is None:
                draft = AIResult(
                    id=draft_id,
                    user_id=row.user_id,
                    course_id=row.course_id,
                    query=report.goal,
                    status="insufficient_evidence",
                    model_mode="real",
                    prompt_version="m2-report-progress-v1",
                    result_json="{}",
                )
                db.add(draft)
            draft.result_json = json.dumps(body, ensure_ascii=False)
            db.flush()
            row.result_id = draft.id
        else:
            body = collection(db, row, report)
            body["execution"] = information(db, row)
            body["grounded"] = True
            # Preserve the established single-report shape for small materials.
            if len(batches) == 1:
                body["study_report"] = body.pop("study_report_sections")[0]["report"]
            result = AIResult(
                user_id=row.user_id,
                course_id=row.course_id,
                query=report.goal,
                status="grounded",
                model_mode="real",
                prompt_version=REPORT_PROMPT_VERSION,
                result_json=json.dumps(body, ensure_ascii=False),
            )
            db.add(result)
            db.flush()
            row.result_id = result.id
            current.status, current.error = "SUCCEEDED", None
    current.lease_token = current.lease_until = None
    db.commit()
    return True


def resume(db, row):
    from ..core.config import get_user_settings
    from .remote_ai import response

    owned_course(db, row.user_id, row.course_id, lock=True)
    report = report_envelope(row.query)
    job = db.get(ProcessingJob, row.job_id) if row.job_id else None
    settings = get_user_settings(row.user_id)
    if (
        not report
        or not report.batched
        or not job
        or job.status not in {"FAILED", "CANCELLED"}
    ):
        raise HTTPException(409, "仅已停止的分批报告可确认续跑")
    if (
        settings.llm_provider != "zhipu"
        or not settings.zhipu_api_key.get_secret_value()
        or row.model != settings.llm_model
        or row.endpoint != settings.llm_endpoint
    ):
        raise HTTPException(409, "模型配置已变化，请重新预览")
    validate_context(db, row.user_id, row.course_id, row.sources)
    from .remote_ai import validate_request_dependencies

    validate_request_dependencies(db, row)
    active = db.scalar(
        select(ProcessingJob.id).where(
            ProcessingJob.user_id == row.user_id,
            ProcessingJob.type == "AI_ANALYSIS",
            ProcessingJob.status.in_(["RUNNING", "QUEUED"]),
        )
    )
    if active:
        raise HTTPException(409, "已有AI任务，请等待完成后续跑")
    state = progress(db, row)
    if state["completed"] == state["total"]:
        raise HTTPException(409, "全部批次已完成")
    job.status, job.error = "QUEUED", None
    job.max_attempts = job.attempt_count + state["total"] - state["completed"]
    row.consented_at = utc_now()
    from .m2_execution import reset_window

    reset_window(db, row)
    db.commit()
    return response(db, row)
