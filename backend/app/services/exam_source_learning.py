"""M4 read adapter: frozen sources and bounded, answer-free review summaries."""

from sqlalchemy import select, func, case, or_, and_, true
from ..models import Mistake, ReviewTask
from ..repositories.source_links import json_references
from .exam_workspace import records
from .mistake_progress import mastered_since


def root():
    return case((func.json_valid(Mistake.detail_json), Mistake.detail_json), else_="{}")


def question():
    data = root()
    return case(
        (
            func.json_type(data, "$.question") == "object",
            func.json_extract(data, "$.question"),
        ),
        else_="{}",
    )


def reference(user_id, version_id, chunk_id):
    return json_references(question(), user_id, version_id, chunk_id)


def linked_records(user_id, course_id, version_id, chunk_id=None):
    matched = reference(user_id, version_id, chunk_id)
    if chunk_id is None:
        q = question()
        no_citations = or_(
            func.json_type(q, "$.citations").is_(None),
            and_(
                func.json_type(q, "$.citations") == "array",
                func.json_array_length(q, "$.citations") == 0,
            ),
        )
        matched = or_(
            matched,
            and_(
                func.json_extract(q, "$.source_version_id") == version_id, no_citations
            ),
        )
    return records(user_id, course_id)[1].where(matched)


def enrich(db, user_id, version_id, chunk_id, items, today):
    ids = [item["id"] for item in items if item["kind"] == "mistake"]
    if not ids:
        return items
    events = {identity: {"redoes": {}, "relapses": {}} for identity in ids}
    # Project event judgment fields only; a redo also contains the user's answer.
    for field in ("redoes", "relapses"):
        path = "$." + field
        mapping = case(
            (func.json_type(root(), path) == "object", func.json_extract(root(), path)),
            else_="{}",
        )
        entries = func.json_each(mapping).table_valued("key", "value", "type").alias()
        value = case((entries.c.type == "object", entries.c.value), else_="{}")
        rows = db.execute(
            select(
                Mistake.id,
                entries.c.key,
                func.json_extract(value, "$.status"),
                func.json_extract(value, "$.completed_at"),
                func.json_extract(value, "$.sequence"),
                func.json_type(value, "$.correct"),
            )
            .select_from(Mistake)
            .join(entries, true())
            .where(Mistake.id.in_(ids), Mistake.user_id == user_id)
        ).all()
        for identity, key, status, completed, sequence, correct_type in rows:
            events[identity][field][key] = dict(
                status=status,
                completed_at=completed,
                sequence=sequence or 0,
                correct=correct_type == "true",
            )
    reviews = {
        identity: dict(pending_count=count, due_count=due, next_due_date=next_date)
        for identity, count, due, next_date in db.execute(
            select(
                ReviewTask.mistake_id,
                func.count(),
                func.sum(case((ReviewTask.due_date <= today, 1), else_=0)),
                func.min(ReviewTask.due_date),
            )
            .where(
                ReviewTask.user_id == user_id,
                ReviewTask.mistake_id.in_(ids),
                ReviewTask.status == "PENDING",
            )
            .group_by(ReviewTask.mistake_id)
        ).all()
    }
    relations = dict(
        db.execute(
            select(Mistake.id, reference(user_id, version_id, chunk_id)).where(
                Mistake.user_id == user_id, Mistake.id.in_(ids)
            )
        ).all()
    )
    result = []
    for item in items:
        row = dict(item)
        if row["kind"] == "mistake":
            identity = row["id"]
            try:
                mastered = mastered_since(events[identity]) is not None
            except (ValueError, TypeError):
                mastered = None  # Unsupported historical judgment: never guess mastery.
            row["review"] = dict(
                mastered=mastered,
                **reviews.get(
                    identity, dict(pending_count=0, due_count=0, next_due_date=None)
                ),
            )
            row["source_relation"] = "citation" if relations[identity] else "version"
        result.append(row)
    return result
