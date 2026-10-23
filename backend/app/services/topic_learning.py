"""M4 metadata adapter. Counts describe records, never mastery or draw eligibility."""

import json
from fastapi import HTTPException
from sqlalchemy import select, func
from ..models import Topic, PastPaper, PastQuestion, Mistake
from .topic_tree import active_clause
from .exam_retirement import mistakes_in_course
from .mistake_progress import mastered_since
from .workspace_record_query import metadata_query
from ..repositories.source_links import json_references


def linked_records(user_id, course_id, version_id, chunk_id=None):
    return metadata_query(
        Topic.id, Topic.name, "topic", "LINKED", Topic.updated_at
    ).where(
        Topic.user_id == user_id,
        Topic.course_id == course_id,
        Topic.merged_into_id.is_(None),
        active_clause(),
        json_references(Topic.sources_json, user_id, version_id, chunk_id),
    )


class TopicIndex:
    def __init__(self, db, user_id, course_id):
        self.rows = db.execute(
            select(
                Topic.id,
                Topic.name,
                Topic.aliases_json,
                Topic.revision,
                Topic.merged_into_id,
                func.json_extract(Topic.sources_json, "$.hierarchy.parent_id").label(
                    "parent_id"
                ),
            )
            .where(
                Topic.user_id == user_id, Topic.course_id == course_id, active_clause()
            )
            .order_by(Topic.id)
            .limit(2001)
        ).all()
        if len(self.rows) > 2000:
            raise HTTPException(422, "知识点超过2000个，请先整理课程范围")
        self.by_id = {t.id: t for t in self.rows}
        self.visible = [t for t in self.rows if not t.merged_into_id]
        self.parents = {t.id: t.parent_id for t in self.visible}

    def canonical(self, value):
        seen = set()
        while value in self.by_id and value not in seen:
            seen.add(value)
            row = self.by_id[value]
            if not row.merged_into_id:
                return value
            value = row.merged_into_id
        return None

    def ancestors(self, ids):
        result = set()
        for value in ids:
            value = self.canonical(value)
            seen = set()
            while value and value not in seen:
                seen.add(value)
                result.add(value)
                value = self.canonical(self.parents.get(value))
        return result

    def metadata(self, row):
        return dict(
            id=row.id,
            name=row.name,
            aliases=json.loads(row.aliases_json),
            parent_id=self.parents.get(row.id),
            revision=row.revision,
        )


def record_status(db, user_id, course_id, index):
    counts = {t.id: dict(confirmed=0, pending=0, needs_review=0) for t in index.visible}
    questions = db.execute(
        select(
            PastQuestion.status,
            PastQuestion.topic_id,
            func.json_extract(PastQuestion.bank_data_json, "$.topic_ids").label(
                "topic_ids"
            ),
        )
        .join(PastPaper)
        .where(
            PastQuestion.user_id == user_id,
            PastPaper.user_id == user_id,
            PastPaper.course_id == course_id,
            PastQuestion.status != "SUPERSEDED",
            func.coalesce(
                func.json_extract(PastPaper.bank_meta_json, "$.deleted_by_user"), 0
            )
            == 0,
        )
        .limit(20001)
    ).all()
    if len(questions) > 20000:
        raise HTTPException(422, "题库超过20000条记录，请先整理课程范围")
    for q in questions:
        ids = (
            json.loads(q.topic_ids)
            if q.topic_ids
            else [q.topic_id]
            if q.topic_id
            else []
        )
        for tid in index.ancestors(ids):
            counts[tid]["confirmed" if q.status == "CONFIRMED" else "pending"] += 1
    mistakes = db.execute(
        select(
            Mistake.id,
            Mistake.updated_at,
            func.json_extract(Mistake.detail_json, "$.question.topic_ids").label(
                "topic_ids"
            ),
            func.json_extract(Mistake.detail_json, "$.question.topic_id").label(
                "topic_id"
            ),
            func.json_extract(Mistake.detail_json, "$.redoes").label("redoes"),
            func.json_extract(Mistake.detail_json, "$.relapses").label("relapses"),
        )
        .where(
            Mistake.id.in_(mistakes_in_course(user_id, course_id)),
            func.coalesce(
                func.json_extract(Mistake.detail_json, "$.removed_from_bank"), 0
            )
            != 1,
        )
        .order_by(Mistake.updated_at.desc(), Mistake.id)
        .limit(20001)
    ).all()
    if len(mistakes) > 20000:
        raise HTTPException(422, "错题超过20000条记录，请先整理课程范围")
    related = []
    for m in mistakes:
        needs_review = (
            mastered_since(
                dict(
                    redoes=json.loads(m.redoes or "{}"),
                    relapses=json.loads(m.relapses or "{}"),
                )
            )
            is None
        )
        ids = json.loads(m.topic_ids) if m.topic_ids else []
        scope = index.ancestors(ids or ([m.topic_id] if m.topic_id else []))
        if needs_review:
            for tid in scope:
                counts[tid]["needs_review"] += 1
        related.append(
            dict(
                id=m.id, updated_at=m.updated_at, scope=scope, needs_review=needs_review
            )
        )
    return counts, related
