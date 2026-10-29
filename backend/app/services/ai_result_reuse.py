"""Conservative reuse of complete, owned results. Never dispatches a provider."""

from fastapi import HTTPException
from sqlalchemy import select
from ..core.config import get_user_settings
from ..models import AIResult, ProcessingJob, RemoteQuery
from ..models.base import utc_now
from ..ai.providers import PROMPT_VERSION
from ..schemas.question_drafts import candidate_envelope, CANDIDATE_PROMPT_VERSION
from ..schemas.study_reports import report_envelope, REPORT_PROMPT_VERSION
from .ai_context import validate_context
from ..repositories.materials import active_version


def find_reusable(db, row, result_id=None):
    from .remote_ai import validated_result, validate_request_dependencies

    settings = get_user_settings(row.user_id)
    if (
        row.job_id
        or row.expires_at <= utc_now()
        or settings.llm_provider not in {"zhipu", "compatible"}
        or row.model != settings.llm_model
        or row.endpoint != settings.llm_endpoint
    ):
        return None
    try:
        validate_context(db, row.user_id, row.course_id, row.sources)
        validate_request_dependencies(db, row)
        for source in row.sources:
            for version_id in source.get("request_scope", {}).get("version_ids", []):
                active_version(db, version_id, row.user_id, row.course_id)
    except HTTPException:
        return None
    prompt = (
        REPORT_PROMPT_VERSION if report_envelope(row.query)
        else CANDIDATE_PROMPT_VERSION if candidate_envelope(row.query)
        else PROMPT_VERSION
    )
    query = (
        select(RemoteQuery, AIResult)
        .join(AIResult, AIResult.id == RemoteQuery.result_id)
        .join(ProcessingJob, ProcessingJob.id == RemoteQuery.job_id)
        .where(
            RemoteQuery.user_id == row.user_id,
            RemoteQuery.course_id == row.course_id,
            RemoteQuery.query == row.query,
            RemoteQuery.model == row.model,
            RemoteQuery.endpoint == row.endpoint,
            AIResult.user_id == row.user_id,
            AIResult.course_id == row.course_id,
            AIResult.status == "grounded",
            AIResult.model_mode == "real",
            AIResult.prompt_version == prompt,
            ProcessingJob.user_id == row.user_id,
            ProcessingJob.resource_id == RemoteQuery.id,
            ProcessingJob.type == "AI_ANALYSIS",
            ProcessingJob.status == "SUCCEEDED",
        )
        .order_by(AIResult.created_at.desc(), AIResult.id.desc())
        .limit(100)
    )
    if result_id is not None:
        query = query.where(AIResult.id == result_id)
    for previous, result in db.execute(query):
        if previous.sources != row.sources:
            continue
        validated = validated_result(db, result)
        body = validated.result
        if body.get("partial") or body.get("dependency_status") == "stale":
            continue

        def active(value):
            if isinstance(value, list):
                return all(active(item) for item in value)
            if isinstance(value, dict):
                if {"version_id", "chunk_id", "quote"} <= value.keys():
                    return value.get("availability") == "active"
                return all(active(item) for item in value.values())
            return True

        if active(body):
            return validated
    return None


def reuse(db, user_id, query_id, result_id):
    from .remote_ai import owned_query
    from .courses import owned_course

    row = owned_query(db, user_id, query_id)
    owned_course(db, user_id, row.course_id, lock=True)
    result = find_reusable(db, row, result_id)
    if result is None:
        raise HTTPException(409, "已有结果不再匹配或来源已变化，请重新预览后选择")
    return result
