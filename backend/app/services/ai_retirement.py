"""M2 integration interface for course removal, without altering provider logic."""

from sqlalchemy import delete, select, func, update, text
from ..models import AIResult, RemoteQuery, ProcessingJob


def course_ai_counts(db, user_id, course_id):
    return {
        "ai_results": db.scalar(
            select(func.count())
            .select_from(AIResult)
            .where(AIResult.user_id == user_id, AIResult.course_id == course_id)
        ),
        "remote_queries": db.scalar(
            select(func.count())
            .select_from(RemoteQuery)
            .where(RemoteQuery.user_id == user_id, RemoteQuery.course_id == course_id)
        ),
    }


def retire_course_ai(db, user_id, course_id):
    jobs = select(RemoteQuery.job_id).where(
        RemoteQuery.user_id == user_id, RemoteQuery.course_id == course_id
    )
    db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.user_id == user_id,
            ProcessingJob.id.in_(jobs),
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
        .values(
            status="CANCELLED", lease_token=None, lease_until=None, error="课程已删除"
        )
        .execution_options(synchronize_session=False)
    )
    db.execute(
        delete(RemoteQuery)
        .where(RemoteQuery.user_id == user_id, RemoteQuery.course_id == course_id)
        .execution_options(synchronize_session=False)
    )
    db.execute(
        delete(AIResult)
        .where(AIResult.user_id == user_id, AIResult.course_id == course_id)
        .execution_options(synchronize_session=False)
    )


def cancel_source_queries(db, user_id, version_ids=None, chunk_id=None):
    if version_ids is not None:
        matches = text(
            "EXISTS (SELECT 1 FROM json_each(remote_queries.sources) s WHERE json_extract(s.value,'$.version_id') IN (SELECT value FROM json_each(:versions)))"
        )
        import json

        jobs = (
            select(RemoteQuery.job_id)
            .where(RemoteQuery.user_id == user_id, matches)
            .params(versions=json.dumps(version_ids))
        )
    else:
        matches = text(
            "EXISTS (SELECT 1 FROM json_each(remote_queries.sources) s WHERE json_extract(s.value,'$.source_id')=:chunk)"
        )
        jobs = (
            select(RemoteQuery.job_id)
            .where(RemoteQuery.user_id == user_id, matches)
            .params(chunk=chunk_id)
        )
    db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.user_id == user_id,
            ProcessingJob.type == "AI_ANALYSIS",
            ProcessingJob.id.in_(jobs),
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
        .values(
            status="CANCELLED",
            lease_token=None,
            lease_until=None,
            error="AI来源已删除或撤回",
        )
        .execution_options(synchronize_session=False)
    )
