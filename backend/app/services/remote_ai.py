"""Owned, immutable previews and consented real-model jobs."""

from datetime import timedelta
import json
from fastapi import HTTPException
from sqlalchemy import select, func, update, delete
from ..models import AIResult, RemoteQuery, ProcessingJob
from ..models.base import utc_now
from ..core.config import get_user_settings
from ..schemas.ai import AIResultResponse
from ..schemas.material import JobResponse
from ..schemas.remote_ai import RemoteQueryResponse
from .courses import owned_course
from .ai_context import validate_context
from .ai_material_scope import full_context, report_batches
from ..repositories.materials import checked_chunk
from ..schemas.study_reports import REQUEST_PREFIX, ReportEnvelope, report_envelope
from ..schemas.question_drafts import CANDIDATE_PREFIX, candidate_envelope
from .exam_ai_context import validate_candidate_context


def provider_status(user_id):
    s = get_user_settings(user_id)
    return {
        "provider": "智谱开放平台",
        "configured": s.llm_provider == "zhipu"
        and bool(s.zhipu_api_key.get_secret_value()),
        "model": s.llm_model,
        "endpoint": s.llm_endpoint,
        "checked_at": "2026-10-17" if s.llm_model == "glm-5.3-flash" else "2026-10-14",
        "documentation_url": (
            "https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash"
            if s.llm_model == "glm-5.3-flash"
            else "https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash"
        ),
        "policy_status": "保留期限、训练用途和远程删除能力未核实；请在智谱控制台核对适用协议",
        "policy_entry_url": "https://open.bigmodel.cn/console",
        "max_context_chars": 240000,
        "max_output_tokens": 2048,
    }


def owned_query(db, user_id, query_id):
    row = db.scalar(
        select(RemoteQuery).where(
            RemoteQuery.id == query_id, RemoteQuery.user_id == user_id
        )
    )
    if not row:
        raise HTTPException(404, "AI请求不存在")
    owned_course(db, user_id, row.course_id)
    return row


def response(db, row):
    from .report_batches import progress
    from .ai_result_reuse import find_reusable
    from .m2_execution import information
    from . import qa_batches

    job = db.get(ProcessingJob, row.job_id) if row.job_id else None
    result = (
        db.scalar(
            select(AIResult).where(
                AIResult.id == row.result_id, AIResult.user_id == row.user_id
            )
        )
        if row.result_id
        else None
    )
    validated = validated_result(db, result) if result else None
    report = report_envelope(row.query)
    candidate = candidate_envelope(row.query)
    return RemoteQueryResponse(
        id=row.id,
        course_id=row.course_id,
        query=report.goal
        if report
        else candidate.request.goal
        if candidate
        else row.query,
        request_kind="study_report"
        if report
        else "question_drafts"
        if candidate
        else "qa",
        report_scope=report.model_dump(mode="json") if report else None,
        qa_scope=qa_batches.plan(row) or None,
        candidate_scope=candidate.model_dump(mode="json") if candidate else None,
        batch_progress=qa_batches.progress(db, row)
        if qa_batches.batched(row)
        else progress(db, row),
        model=row.model,
        endpoint=row.endpoint,
        expires_at=row.expires_at,
        consented_at=row.consented_at,
        dispatched_at=row.dispatched_at,
        sources=row.sources,
        job=JobResponse.model_validate(job, from_attributes=True) if job else None,
        result=validated,
        reusable_result=find_reusable(db, row) if not row.job_id else None,
        execution=information(db, row),
    )


def validated_result(db, result):
    body = json.loads(result.result_json)

    def refresh_citations(value):
        if isinstance(value, list):
            for item in value:
                refresh_citations(item)
        elif isinstance(value, dict):
            if {"version_id", "chunk_id", "quote"} <= value.keys():
                refresh_citation(value)
            else:
                for key, item in value.items():
                    # Frozen module inputs are compared byte-for-byte with their
                    # readers; do not inject dynamic citation fields into them.
                    if key != "m2_supplement":
                        refresh_citations(item)

    def refresh_citation(citation):
        try:
            checked_chunk(
                db,
                citation["version_id"],
                citation["chunk_id"],
                citation["quote"],
                result.user_id,
                result.course_id,
            )
            citation["availability"] = "active"
        except (HTTPException, KeyError):
            citation["availability"] = "unavailable"

    refresh_citations(body)
    from .m2_supplements import KEY, validate as validate_supplements

    if body.get(KEY):
        try:
            validate_supplements(
                db, result.user_id, result.course_id, [{KEY: body[KEY]}]
            )
            body["dependency_status"] = "active"
        except HTTPException:
            body["dependency_status"] = "stale"

    def refresh_labels(value):
        if isinstance(value, list):
            for item in value:
                refresh_labels(item)
        elif isinstance(value, dict):
            if value.get("origin") in ("teacher_mark", "observed_exam"):
                value["availability"] = (
                    "unavailable"
                    if body.get("dependency_status") == "stale"
                    else "active"
                )
            for item in value.values():
                refresh_labels(item)

    refresh_labels(body)
    if body.get("result_kind") == "question_drafts" and "exam_context" in body:
        try:
            validate_candidate_context(
                db, result.user_id, result.course_id, body["exam_context"]
            )
            body["dependency_status"] = "active"
        except HTTPException:
            body["dependency_status"] = "stale"
    return AIResultResponse(
        id=result.id,
        course_id=result.course_id,
        query=result.query,
        status=result.status,
        model_mode=result.model_mode,
        result=body,
    )


def preview(
    db, user_id, course_id, payload, *, report_request=None, candidate_request=None
):
    owned_course(db, user_id, course_id, lock=True)
    if payload.query.startswith((REQUEST_PREFIX, CANDIDATE_PREFIX)):
        raise HTTPException(422, "问题使用了系统保留前缀")
    if not provider_status(user_id)["configured"]:
        raise HTTPException(409, "当前账户尚未配置智谱密钥，请前往API接入保存个人Key")
    db.execute(
        delete(RemoteQuery).where(
            RemoteQuery.user_id == user_id,
            RemoteQuery.course_id == course_id,
            RemoteQuery.job_id.is_(None),
            RemoteQuery.expires_at < utc_now(),
        )
    )
    if (
        db.scalar(
            select(func.count())
            .select_from(RemoteQuery)
            .where(
                RemoteQuery.user_id == user_id,
                RemoteQuery.course_id == course_id,
                RemoteQuery.job_id.is_(None),
            )
        )
        >= 20
    ):
        raise HTTPException(409, "未确认预览已达20条，请等待旧预览过期")
    query = payload.query
    if candidate_request:
        raise HTTPException(
            410, "练习题已改为用户题库随机抽题，请使用question-bank/draw"
        )
    elif report_request:
        sources, coverage = full_context(
            db,
            user_id,
            course_id,
            [str(v) for v in report_request.version_ids],
            [str(c) for c in report_request.chunk_ids],
        )
        coverage["batch_count"] = len(report_batches(sources))
        envelope = ReportEnvelope(
            goal=report_request.goal,
            scope_version_ids=list(dict.fromkeys(report_request.version_ids)),
            chunk_ids=report_request.chunk_ids,
            study_mode=report_request.study_mode,
            coverage=coverage,
            batched=True,
        )
        query = REQUEST_PREFIX + envelope.model_dump_json()
    else:
        from .qa_batches import select_sources

        sources = select_sources(
            db,
            user_id,
            course_id,
            payload.query,
            [str(v) for v in payload.version_ids],
            [str(c) for c in payload.chunk_ids],
        )
    if not sources:
        raise HTTPException(
            409,
            {
                "message": "所选范围没有可用原文；不会发送远程请求，请补充资料或确认补录",
                "status": "insufficient_evidence",
            },
        )
    if not report_request and not candidate_request:
        # Persist the explicit QA selection as well as retrieved text. Two different
        # filters can yield identical evidence; they are still different requests.
        sources[0]["request_scope"] = {
            "version_ids": [str(v) for v in payload.version_ids],
            "chunk_ids": [str(c) for c in payload.chunk_ids],
        }
    sources[0]["execution_policy"] = {
        "version": 1,
        "max_structure_repairs": (report_request or payload).max_structure_repairs,
        "budget_seconds": 120,
    }
    from .m2_supplements import freeze, context

    freeze(
        db, user_id, course_id, sources, report_request or payload, bool(report_request)
    )
    s = get_user_settings(user_id)
    from ..core.account_connection import binding

    sources[0]["account_credential"] = binding(s)
    key = s.zhipu_api_key.get_secret_value()
    if key and (
        key in query
        or any(key in source["text"] for source in sources)
        or key in json.dumps(context(sources), ensure_ascii=False)
    ):
        raise HTTPException(422, "问题或片段包含当前服务密钥，请移除后重试")
    row = RemoteQuery(
        user_id=user_id,
        course_id=course_id,
        query=query,
        sources=sources,
        model=s.llm_model,
        endpoint=s.llm_endpoint,
        expires_at=utc_now() + timedelta(minutes=15),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return response(db, row)


def confirm(db, user_id, query_id):
    row = owned_query(db, user_id, query_id)
    if candidate_envelope(row.query):
        raise HTTPException(410, "旧AI练习生成已停用，请从用户题库抽题")
    owned_course(db, user_id, row.course_id, lock=True)
    row = owned_query(db, user_id, query_id)
    if row.job_id:
        return response(db, row)
    s = get_user_settings(user_id)
    if (
        row.expires_at <= utc_now()
        or not provider_status(user_id)["configured"]
        or row.model != s.llm_model
        or row.endpoint != s.llm_endpoint
    ):
        raise HTTPException(409, "预览已过期或配置已改变，请重新预览")
    validate_context(db, user_id, row.course_id, row.sources)
    validate_request_dependencies(db, row)
    active = db.scalar(
        select(ProcessingJob.id)
        .join(RemoteQuery, RemoteQuery.job_id == ProcessingJob.id)
        .where(
            RemoteQuery.course_id == row.course_id,
            RemoteQuery.user_id == user_id,
            ProcessingJob.user_id == user_id,
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
    )
    if active:
        raise HTTPException(409, "当前课程已有排队或运行中的真实AI任务")
    job = ProcessingJob(
        user_id=user_id,
        type="AI_ANALYSIS",
        resource_id=row.id,
        max_attempts=(
            len(report_batches(row.sources)) + 1
            if row.sources[0].get("qa_plan", {}).get("batched")
            else len(report_batches(row.sources))
            if (report_envelope(row.query) and report_envelope(row.query).batched)
            else 1
        ),
    )
    db.add(job)
    db.flush()
    row.job_id = job.id
    row.consented_at = utc_now()
    db.commit()
    db.refresh(row)
    return response(db, row)


def validate_request_dependencies(db, row):
    from .m2_supplements import validate, context

    from ..core.account_connection import binding

    settings = get_user_settings(row.user_id)
    if not row.sources or row.sources[0].get("account_credential") != binding(settings):
        raise HTTPException(
            409, "本账户API配置已变化或旧共享预览已失效，请重新预览并确认"
        )
    saved = context(row.sources)
    if (
        report_envelope(row.query)
        and saved.get("version") == 1
        and (saved.get("teacher_marks") or saved.get("exam_paper_ids"))
    ):
        raise HTTPException(
            409, "旧手动标签来源预览已停用，请重新预览以自动检测阅读标记和真题关联"
        )
    validate(db, row.user_id, row.course_id, row.sources)
    candidate = candidate_envelope(row.query)
    if candidate:
        validate_candidate_context(
            db, row.user_id, row.course_id, candidate.exam_context
        )


def cancel(db, user_id, query_id):
    row = owned_query(db, user_id, query_id)
    owned_course(db, user_id, row.course_id, lock=True)
    row = owned_query(db, user_id, query_id)
    if row.job_id:
        changed = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == row.job_id,
                ProcessingJob.user_id == user_id,
                ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
            )
            .values(
                status="CANCELLED",
                lease_token=None,
                lease_until=None,
                error="用户取消AI任务",
            )
            .execution_options(synchronize_session=False)
        )
        if (
            not changed.rowcount
            and db.get(ProcessingJob, row.job_id).status != "CANCELLED"
        ):
            raise HTTPException(409, "任务已结束，不能取消历史结果")
    else:
        row.expires_at = utc_now()
    db.commit()
    db.expire_all()
    return response(db, owned_query(db, user_id, query_id))
