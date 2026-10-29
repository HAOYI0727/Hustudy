"""Owned M2 execution windows; durable counters, never raw model responses."""

import json
import time
from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, uuid5
from fastapi import HTTPException
from sqlalchemy import update, select, literal
from ..models import AIResult, ProcessingJob, RemoteQuery
from ..models.base import utc_now
from ..core.config import get_user_settings
from ..schemas.study_reports import report_envelope
from ..ai.providers import ProviderFailure, PROMPT_VERSION
from .ai_material_scope import report_batches
from .ai_context import validate_context
from .courses import owned_course

VERSION = "m2-execution-v1"
REPAIR_PROMPT_VERSION = "m2-structure-repair-v1"
WINDOW_SECONDS = 120
MAX_REPAIR_CHARS = 16000


def record_id(query_id):
    return str(uuid5(NAMESPACE_URL, f"hustudy/execution/{query_id}"))


def owned_record(db, row):
    record = db.get(AIResult, record_id(row.id))
    if record and (record.user_id != row.user_id or record.course_id != row.course_id):
        raise HTTPException(404, "处理记录不可访问")
    return record


def repair_limit(row):
    policy = row.sources[0].get("execution_policy", {}) if row.sources else {}
    value = policy.get("max_structure_repairs", 0)
    return value if type(value) is int and 0 <= value <= 2 else 0


def new_state(db, row, previous=None):
    report = report_envelope(row.query)
    batches = (
        report_batches(row.sources) if report and report.batched else [row.sources]
    )
    if report and report.batched:
        from .report_batches import checkpoint_id

        batches = [
            batch
            for i, batch in enumerate(batches)
            if not (step := db.get(AIResult, checkpoint_id(row.id, i)))
            or step.status != "grounded"
        ]
    from . import qa_batches

    synthesis_chars = 0
    if qa_batches.batched(row):
        batches = [
            batch
            for batch, step in zip(
                report_batches(row.sources), qa_batches.checkpoints(db, row)
            )
            if not qa_batches.done(step, row)
        ]
        # Reserve the bounded synthesis stage as well as all remaining scans.
        synthesis_chars = 128000
    used = (previous or {}).get("repairs_used", 0)
    remaining = max(0, repair_limit(row) - used)
    units = len(batches) + int(bool(synthesis_chars))
    calls = units + remaining
    largest = max(
        synthesis_chars,
        max((sum(len(s["text"]) for s in b) for b in batches), default=0),
    )
    from .m2_supplements import note_chars

    supplement_chars = note_chars(row.sources)
    return {
        "version": VERSION,
        "repair_prompt_version": REPAIR_PROMPT_VERSION,
        "budget_seconds": WINDOW_SECONDS,
        "max_structure_repairs": repair_limit(row),
        "repairs_used": used,
        "total_calls": (previous or {}).get("total_calls", 0),
        "window_number": (previous or {}).get("window_number", 0) + 1,
        "window_started_at": None,
        "deadline_at": None,
        "window_calls": 0,
        "window_call_limit": calls,
        # Data characters, excluding fixed system/schema instructions. Query
        # allowance covers the JSON-encoded goal/mode; no extra sources allowed.
        "input_chars_used": 0,
        "input_chars_limit": sum(len(s["text"]) for b in batches for s in b)
        + synthesis_chars
        + 13000 * units
        + remaining * (largest + 13000 + MAX_REPAIR_CHARS)
        + calls * supplement_chars,
        "output_tokens_reserved": 0,
        "output_tokens_limit": calls * (6000 if report else 2048),
        "phase": "awaiting_dispatch",
        "usage": (previous or {}).get("usage", {}),
    }


def information(db, row):
    record = owned_record(db, row)
    state = json.loads(record.result_json) if record else new_state(db, row)
    remaining = WINDOW_SECONDS
    if state.get("deadline_at"):
        remaining = max(
            0,
            (datetime.fromisoformat(state["deadline_at"]) - utc_now()).total_seconds(),
        )
    return {**state, "remaining_seconds": round(remaining, 1)}


def reset_window(db, row):
    record = owned_record(db, row)
    if record:
        record.result_json = json.dumps(
            new_state(db, row, json.loads(record.result_json))
        )


def expire_queued(db):
    """An expired between-batch window must stop even while another AI is busy."""
    from .report_batches import collection
    from ..schemas.study_reports import REPORT_PROMPT_VERSION

    rows = db.execute(
        select(RemoteQuery, ProcessingJob, AIResult)
        .join(ProcessingJob, ProcessingJob.id == RemoteQuery.job_id)
        .join(AIResult, AIResult.query == literal("execution:") + RemoteQuery.id)
        .where(
            ProcessingJob.type == "AI_ANALYSIS",
            ProcessingJob.status == "QUEUED",
            ProcessingJob.user_id == RemoteQuery.user_id,
            AIResult.user_id == RemoteQuery.user_id,
            AIResult.course_id == RemoteQuery.course_id,
            AIResult.prompt_version == VERSION,
        )
    ).all()
    for row, job, record in rows:
        if record.id != record_id(row.id):
            continue
        state = json.loads(record.result_json)
        if (
            not state.get("deadline_at")
            or datetime.fromisoformat(state["deadline_at"]) > utc_now()
        ):
            continue
        changed = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job.id,
                ProcessingJob.status == "QUEUED",
            )
            .values(
                status="FAILED",
                lease_token=None,
                lease_until=None,
                error="本次确认的120秒处理预算已用尽；已完成部分保留",
            )
            .execution_options(synchronize_session=False)
        )
        if not changed.rowcount:
            continue
        report = report_envelope(row.query)
        from . import qa_batches

        body = (
            collection(db, row, report)
            if report
            else qa_batches.collection(db, row)
            if qa_batches.batched(row)
            else {"citations": []}
        )
        state.update(phase="budget_exhausted", last_error_code="TASK_BUDGET_EXCEEDED")
        record.result_json = json.dumps(state)
        body.update(
            message="本次确认的120秒处理预算已用尽；已完成部分保留，请明确确认后继续",
            error_code="TASK_BUDGET_EXCEEDED",
            partial=bool(body.get("study_report_sections")) or qa_batches.batched(row),
            execution={**state, "remaining_seconds": 0},
        )
        result = AIResult(
            user_id=row.user_id,
            course_id=row.course_id,
            query=report.goal if report else row.query,
            status="provider_error",
            model_mode="real",
            prompt_version=REPORT_PROMPT_VERSION if report else PROMPT_VERSION,
            result_json=json.dumps(body, ensure_ascii=False),
        )
        db.add(result)
        db.flush()
        row.result_id = result.id


class Execution:
    def __init__(self, db, job, row, token, settings):
        self.db, self.job, self.row, self.token, self.settings = (
            db,
            job,
            row,
            token,
            settings,
        )
        self.record = owned_record(db, row)
        self.state = (
            json.loads(self.record.result_json) if self.record else new_state(db, row)
        )
        self.monotonic_deadline = None

    def remaining(self):
        if not self.state["deadline_at"]:
            return WINDOW_SECONDS
        remaining = (
            datetime.fromisoformat(self.state["deadline_at"]) - utc_now()
        ).total_seconds()
        if self.monotonic_deadline is None:
            self.monotonic_deadline = time.monotonic() + max(0, remaining)
        return max(0, min(remaining, self.monotonic_deadline - time.monotonic()))

    def check_deadline(self):
        if self.remaining() <= 0:
            raise ProviderFailure(
                "TASK_BUDGET_EXCEEDED",
                "本次确认的120秒处理预算已用尽；已完成部分保留，不再自动调用",
            )

    def guard(self):
        from .remote_ai import validate_request_dependencies

        changed = self.db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == self.job.id,
                ProcessingJob.user_id == self.row.user_id,
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_token == self.token,
                ProcessingJob.lease_until > utc_now(),
            )
            .values(progress=ProcessingJob.progress)
            .execution_options(synchronize_session=False)
        )
        if not changed.rowcount:
            self.db.rollback()
            raise ProviderFailure(
                "TASK_STOPPED", "任务已取消或运行身份已失效，未继续发送"
            )
        try:
            owned_course(self.db, self.row.user_id, self.row.course_id)
            validate_context(
                self.db, self.row.user_id, self.row.course_id, self.row.sources
            )
            validate_request_dependencies(self.db, self.row)
        except HTTPException as failure:
            self.db.rollback()
            changed_config = str(failure.detail).startswith("本账户API配置")
            raise ProviderFailure(
                "CONFIG_CHANGED" if changed_config else "SOURCE_UNAVAILABLE",
                "本账户API配置已变化，请重新预览确认"
                if changed_config
                else "来源已失效，未继续发送",
            ) from None
        settings = get_user_settings(self.row.user_id)
        if (
            settings.llm_provider not in {"zhipu", "compatible"}
            or settings.llm_model != self.row.model
            or settings.llm_endpoint != self.row.endpoint
            or settings.zhipu_api_key.get_secret_value()
            != self.settings.zhipu_api_key.get_secret_value()
        ):
            self.db.rollback()
            raise ProviderFailure("CONFIG_CHANGED", "模型连接已变化，请重新预览确认")

    def save(self):
        if self.record is None:
            self.record = AIResult(
                id=record_id(self.row.id),
                user_id=self.row.user_id,
                course_id=self.row.course_id,
                query=f"execution:{self.row.id}",
                status="insufficient_evidence",
                model_mode="real",
                prompt_version=VERSION,
                result_json="{}",
            )
            self.db.add(self.record)
        self.record.result_json = json.dumps(self.state)
        self.db.commit()

    def before_call(self, query, sources, max_tokens, repair_content=None):
        self.guard()
        if not self.state["window_started_at"]:
            start = utc_now()
            self.state["window_started_at"] = start.isoformat()
            self.state["deadline_at"] = (
                start + timedelta(seconds=WINDOW_SECONDS)
            ).isoformat()
        self.check_deadline()
        size = (
            len(query)
            + sum(len(s["text"]) for s in sources)
            + len(repair_content or "")
        )
        from .m2_supplements import note_chars

        size += note_chars(self.row.sources)
        if (
            self.state["window_calls"] >= self.state["window_call_limit"]
            or self.state["input_chars_used"] + size > self.state["input_chars_limit"]
            or self.state["output_tokens_reserved"] + max_tokens
            > self.state["output_tokens_limit"]
        ):
            raise ProviderFailure(
                "TASK_BUDGET_EXCEEDED",
                "本次确认的调用或输入输出预算已用尽；不会继续发送",
            )
        if repair_content is not None:
            if self.state["repairs_used"] >= self.state["max_structure_repairs"]:
                raise ProviderFailure("REPAIR_LIMIT", "已达到本次授权的结构修复次数")
            self.state["repairs_used"] += 1
        self.state["total_calls"] += 1
        self.state["window_calls"] += 1
        self.state["input_chars_used"] += size
        self.state["output_tokens_reserved"] += max_tokens
        self.state["last_output_token_limit"] = max_tokens
        self.state["phase"] = (
            "repairing" if repair_content is not None else "generating"
        )
        self.save()  # Release SQLite locks before waiting for the model.

    def can_repair(self, failure):
        content = getattr(failure, "repair_content", None)
        return (
            failure.code in {"INVALID_JSON", "INVALID_OUTPUT"}
            and isinstance(content, str)
            and 0 < len(content) <= MAX_REPAIR_CHARS
            and self.state["repairs_used"] < self.state["max_structure_repairs"]
        )

    def success(self, usage):
        self.guard()
        self.check_deadline()
        if usage.get("completion_tokens", 0) > self.state["last_output_token_limit"]:
            raise ProviderFailure(
                "TASK_BUDGET_EXCEEDED",
                "模型报告的输出token超过本次调用预算，未采纳结果",
            )
        for key, value in usage.items():
            self.state["usage"][key] = self.state["usage"].get(key, 0) + value
        self.state["phase"] = "generated"
        self.save()

    def failure(self, code):
        self.guard()
        self.state["phase"] = (
            "budget_exhausted" if code == "TASK_BUDGET_EXCEEDED" else "failed"
        )
        self.state["last_error_code"] = code
        self.save()

    def info(self):
        return {**self.state, "remaining_seconds": round(self.remaining(), 1)}
