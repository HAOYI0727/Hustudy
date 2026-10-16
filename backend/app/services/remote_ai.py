"""Owned, immutable previews and consented real-model jobs."""

from datetime import timedelta
import json
from fastapi import HTTPException
from sqlalchemy import select, func, update, delete
from ..models import AIResult, RemoteQuery, ProcessingJob
from ..models.base import utc_now
from ..core.config import get_settings
from ..schemas.ai import AIResultResponse
from ..schemas.material import JobResponse
from ..schemas.remote_ai import RemoteQueryResponse
from .courses import owned_course
from .ai_context import select_context, validate_context
from ..repositories.materials import checked_chunk


def provider_status():
    s = get_settings()
    return {
        "provider": "智谱开放平台",
        "configured": s.llm_provider == "zhipu"
        and bool(s.zhipu_api_key.get_secret_value()),
        "model": s.llm_model,
        "endpoint": s.llm_endpoint,
        "checked_at": "2026-10-14",
        "documentation_url": "https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash",
        "policy_status": "保留期限、训练用途和远程删除能力未核实；请在智谱控制台核对适用协议",
        "policy_entry_url": "https://open.bigmodel.cn/console",
        "max_context_chars": 8000,
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
    return RemoteQueryResponse(
        id=row.id,
        course_id=row.course_id,
        query=row.query,
        model=row.model,
        endpoint=row.endpoint,
        expires_at=row.expires_at,
        consented_at=row.consented_at,
        dispatched_at=row.dispatched_at,
        sources=row.sources,
        job=JobResponse.model_validate(job, from_attributes=True) if job else None,
        result=validated,
    )


def validated_result(db, result):
    body = json.loads(result.result_json)
    for citation in body.get("citations", []):
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
    return AIResultResponse(
        id=result.id,
        course_id=result.course_id,
        query=result.query,
        status=result.status,
        model_mode=result.model_mode,
        result=body,
    )


def preview(db, user_id, course_id, payload):
    owned_course(db, user_id, course_id, lock=True)
    if not provider_status()["configured"]:
        raise HTTPException(409, "后端尚未配置智谱密钥")
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
    sources = select_context(
        db,
        user_id,
        course_id,
        payload.query,
        [str(v) for v in payload.version_ids],
        [str(c) for c in payload.chunk_ids],
    )
    if not sources:
        raise HTTPException(
            409, "当前范围没有可用关键词证据；不会发送远程请求，请选择资料或片段"
        )
    s = get_settings()
    key = s.zhipu_api_key.get_secret_value()
    if key and (
        key in payload.query or any(key in source["text"] for source in sources)
    ):
        raise HTTPException(422, "问题或片段包含当前服务密钥，请移除后重试")
    row = RemoteQuery(
        user_id=user_id,
        course_id=course_id,
        query=payload.query,
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
    owned_course(db, user_id, row.course_id, lock=True)
    row = owned_query(db, user_id, query_id)
    if row.job_id:
        return response(db, row)
    s = get_settings()
    if (
        row.expires_at <= utc_now()
        or not provider_status()["configured"]
        or row.model != s.llm_model
        or row.endpoint != s.llm_endpoint
    ):
        raise HTTPException(409, "预览已过期或配置已改变，请重新预览")
    validate_context(db, user_id, row.course_id, row.sources)
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
        user_id=user_id, type="AI_ANALYSIS", resource_id=row.id, max_attempts=1
    )
    db.add(job)
    db.flush()
    row.job_id = job.id
    row.consented_at = utc_now()
    db.commit()
    db.refresh(row)
    return response(db, row)


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
