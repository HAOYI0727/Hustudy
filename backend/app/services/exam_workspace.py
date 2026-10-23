"""M4-owned workspace and frozen mistake sources; no answer serialization."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select, func
from ..models import (
    ExamPaper,
    ExamAttempt,
    PastPaper,
    PastQuestion,
    Mistake,
    ReviewTask,
)
from ..core.database import begin_read_snapshot
from ..repositories.materials import active_version, active_document, checked_chunk
from .exam_retirement import (
    check_mistake_course,
    attempts_in_course,
    mistakes_in_course,
)
from .workspace_record_query import metadata_query


def records(user_id, course_id):
    attempts = metadata_query(
        ExamAttempt.id, ExamPaper.title, "attempt", ExamAttempt.status,
        ExamAttempt.updated_at,
    ).join(ExamPaper, ExamPaper.id == ExamAttempt.paper_id).where(
        ExamAttempt.id.in_(attempts_in_course(user_id, course_id)),
        ExamPaper.user_id == user_id,
    )
    mistakes = metadata_query(
        Mistake.id, ExamPaper.title, "mistake", "SAVED", Mistake.updated_at,
    ).join(ExamAttempt, ExamAttempt.id == Mistake.attempt_id).join(
        ExamPaper, ExamPaper.id == ExamAttempt.paper_id,
    ).where(
        Mistake.id.in_(mistakes_in_course(user_id, course_id)),
        ExamPaper.user_id == user_id,
        func.coalesce(func.json_extract(Mistake.detail_json, "$.removed_from_bank"), 0)
        != 1,
    )
    return attempts, mistakes


def summary(db, user, course_id):
    papers = select(PastPaper.id).where(
        PastPaper.user_id == user.id, PastPaper.course_id == course_id
    )
    questions = select(PastQuestion.id).where(
        PastQuestion.user_id == user.id,
        PastQuestion.paper_id.in_(papers),
        PastQuestion.status != "SUPERSEDED",
    )
    attempts = select(ExamAttempt.id).where(
        ExamAttempt.id.in_(attempts_in_course(user.id, course_id))
    )
    live_mistakes = select(Mistake.id).where(
        Mistake.id.in_(mistakes_in_course(user.id, course_id)),
        func.coalesce(func.json_extract(Mistake.detail_json, "$.removed_from_bank"), 0)
        != 1,
    )

    def count(query):
        return db.scalar(select(func.count()).select_from(query.subquery())) or 0

    today = datetime.now(ZoneInfo(user.timezone)).date().isoformat()
    recent = db.execute(
        select(
            ExamAttempt.id, ExamAttempt.status, ExamAttempt.updated_at, ExamPaper.title
        )
        .join(ExamPaper, ExamPaper.id == ExamAttempt.paper_id)
        .where(ExamAttempt.id.in_(attempts), ExamPaper.user_id == user.id)
        .order_by(
            (ExamAttempt.status == "IN_PROGRESS").desc(),
            ExamAttempt.updated_at.desc(),
            ExamAttempt.id,
        )
        .limit(6)
    ).all()
    return {
        "counts": {
            "papers": count(papers),
            "questions": count(questions),
            "confirmed": count(questions.where(PastQuestion.status == "CONFIRMED")),
            "pending": count(questions.where(PastQuestion.status != "CONFIRMED")),
            "attempts": count(attempts),
            "in_progress": count(attempts.where(ExamAttempt.status == "IN_PROGRESS")),
            "mistakes": count(live_mistakes),
            "due_reviews": count(
                select(ReviewTask.id).where(
                    ReviewTask.user_id == user.id,
                    ReviewTask.mistake_id.in_(live_mistakes),
                    ReviewTask.status == "PENDING",
                    ReviewTask.due_date <= today,
                )
            ),
        },
        "recent": [
            dict(
                id=row.id,
                title=row.title,
                kind="attempt",
                status=row.status,
                updated_at=row.updated_at,
            )
            for row in recent
        ],
    }


def mistake_sources(db, user, mistake_id):
    begin_read_snapshot(db)
    course = check_mistake_course(db, user.id, mistake_id)
    row = db.scalar(
        select(Mistake).where(Mistake.id == mistake_id, Mistake.user_id == user.id)
    )
    data = json.loads(row.detail_json)
    if data.get("removed_from_bank"):
        raise HTTPException(404, "错题已移出")
    question = data.get("question", {})
    items, seen = [], set()
    for source in question.get("citations", [])[:50]:
        version_id, chunk_id = source.get("version_id"), source.get("chunk_id", "")
        if not version_id or (version_id, chunk_id) in seen:
            continue
        seen.add((version_id, chunk_id))
        item = dict(
            version_id=version_id,
            chunk_id=chunk_id,
            title="原始引用已不可用",
            availability="unavailable",
        )
        try:
            checked_chunk(
                db,
                version_id,
                chunk_id,
                source.get("quote", ""),
                user.id,
                course.id,
                lock_course=False,
            )
            version = active_version(db, version_id, user.id, course.id)
            document = active_document(db, version.document_id, user.id)
            item.update(
                document_id=document.id,
                title=document.name,
                locator=str(
                    source.get("locator", {}).get(
                        "value", source.get("locator_value", "")
                    )
                ),
                availability="active",
            )
        except HTTPException:
            pass
        items.append(item)
    version_id = question.get("source_version_id")
    if (
        version_id
        and not any(item["version_id"] == version_id for item in items)
        and len(items) < 50
    ):
        item = dict(
            version_id=version_id,
            title="原始题库资料已不可用",
            availability="unavailable",
        )
        try:
            version = active_version(db, version_id, user.id, course.id)
            document = active_document(db, version.document_id, user.id)
            item.update(
                document_id=document.id, title=document.name, availability="active"
            )
        except HTTPException:
            pass
        items.append(item)
    return {"course_id": course.id, "items": items}
