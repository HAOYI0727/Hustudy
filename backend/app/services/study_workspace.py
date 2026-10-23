"""M2-owned result metadata, excluding retired question generation."""

from sqlalchemy import select, func, case, literal
from ..models import AIResult
from .workspace_record_query import metadata_query
from ..repositories.source_links import json_references


def records(user_id, course_id):
    report = AIResult.prompt_version.contains("study-report")
    # Goals are plain text in current results; do not expose any legacy envelope.
    title = case(
        (AIResult.query.startswith("hustudy:"), literal("已保存的学习结果")),
        (report, literal("学习报告 · ") + func.substr(AIResult.query, 1, 160)),
        else_=func.substr(AIResult.query, 1, 160),
    )
    return metadata_query(
        AIResult.id,
        title,
        case((report, "report"), else_="qa"),
        AIResult.status,
        AIResult.updated_at,
    ).where(
        AIResult.user_id == user_id,
        AIResult.course_id == course_id,
        func.coalesce(func.json_extract(AIResult.result_json, "$.result_kind"), "")
        != "question_drafts",
    )


def linked_records(user_id, course_id, version_id, chunk_id=None):
    return records(user_id, course_id).where(
        AIResult.status == "grounded",
        func.coalesce(func.json_extract(AIResult.result_json, "$.partial"), 0) != 1,
        json_references(AIResult.result_json, user_id, version_id, chunk_id),
    )


def summary(db, user, course_id):
    scope = (
        AIResult.user_id == user.id,
        AIResult.course_id == course_id,
        func.coalesce(func.json_extract(AIResult.result_json, "$.result_kind"), "")
        != "question_drafts",
    )

    def count(*extra):
        return (
            db.scalar(select(func.count()).select_from(AIResult).where(*scope, *extra))
            or 0
        )

    rows = db.execute(
        select(
            AIResult.id,
            func.substr(AIResult.query, 1, 160).label("title"),
            AIResult.status,
            AIResult.prompt_version,
            AIResult.updated_at,
        )
        .where(*scope)
        .order_by(AIResult.updated_at.desc(), AIResult.id)
        .limit(6)
    ).all()
    return {
        "counts": {
            "total": count(),
            "grounded": count(AIResult.status == "grounded"),
            "failed": count(AIResult.status == "provider_error"),
        },
        "recent": [
            dict(
                id=row.id,
                title=row.title,
                kind="report" if "study-report" in row.prompt_version else "qa",
                status=row.status,
                updated_at=row.updated_at,
            )
            for row in rows
        ],
    }
