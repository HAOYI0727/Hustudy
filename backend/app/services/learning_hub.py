"""Read-only course orchestrator; learning evidence stays in its owning module."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select, func
from ..core.database import begin_read_snapshot
from ..models import ReviewTask, Topic
from ..models.base import utc_now
from .courses import owned_course
from .topic_learning import TopicIndex, record_status
from . import topic_sources, note_learning


def context(db, user, course_id):
    begin_read_snapshot(db)
    owned_course(db, user.id, course_id)
    index = TopicIndex(db, user.id, course_id)
    return index, *record_status(db, user.id, course_id, index)


def directory(db, user, course_id, query, state, offset, limit):
    index, counts, _ = context(db, user, course_id)
    rows = []
    for row in index.visible:
        item = index.metadata(row) | counts[row.id]
        if (
            query.strip().casefold()
            not in (row.name + " " + " ".join(item["aliases"])).casefold()
        ):
            continue
        if state == "needs_review" and not item["needs_review"]:
            continue
        if state == "without_questions" and item["confirmed"]:
            continue
        rows.append(item)
    rows.sort(key=lambda r: (-bool(r["needs_review"]), r["name"].casefold(), r["id"]))
    return dict(
        items=rows[offset : offset + limit],
        total=len(rows),
        offset=offset,
        limit=limit,
        checked_at=utc_now(),
        course_id=course_id,
    )


def detail(db, user, course_id, topic_id):
    index, counts, mistakes = context(db, user, course_id)
    row = index.by_id.get(topic_id)
    if row is None:
        raise HTTPException(404, "知识点不存在或不在当前课程")
    if row.merged_into_id:
        target = index.canonical(row.id)
        if not target:
            raise HTTPException(404, "合并后的知识点已不可用")
        raise HTTPException(
            409, dict(message="知识点已合并，请明确打开目标", target_id=target)
        )
    sources = topic_sources.evidence(db, user.id, course_id, db.get(Topic, topic_id))
    terms = [row.name, *json.loads(row.aliases_json)]
    related = [m for m in mistakes if topic_id in m["scope"]]
    matches = [m for m in related if m["needs_review"]]
    match_ids = func.json_each(json.dumps([m["id"] for m in related])).table_valued(
        "value"
    )
    reviews = select(ReviewTask).where(
        ReviewTask.user_id == user.id,
        ReviewTask.status == "PENDING",
        ReviewTask.mistake_id.in_(select(match_ids.c.value)),
    )
    today = datetime.now(ZoneInfo(user.timezone)).date().isoformat()
    total = db.scalar(select(func.count()).select_from(reviews.subquery())) or 0
    plans = db.scalars(
        reviews.order_by(ReviewTask.due_date, ReviewTask.id).limit(6)
    ).all()
    return dict(
        course_id=course_id,
        topic=index.metadata(row),
        counts=counts[row.id],
        sources=sources,
        candidates=topic_sources.candidates(db, user.id, course_id, sources, terms),
        notes=note_learning.related_notes(db, user.id, course_id, sources, terms),
        mistakes=[dict(id=m["id"], updated_at=m["updated_at"]) for m in matches[:6]],
        reviews=[
            dict(id=r.id, title=r.title, due_date=r.due_date, mistake_id=r.mistake_id)
            for r in plans
        ],
        review_total=total,
        today=today,
        timezone=user.timezone,
        checked_at=utc_now(),
    )
