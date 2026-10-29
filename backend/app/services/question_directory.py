"""M4 bounded presentation index; detailed question content stays on demand."""

import json
from fastapi import HTTPException
from sqlalchemy import select, func
from ..core.database import begin_read_snapshot
from ..models import PastPaper, PastQuestion
from .courses import owned_course
from . import question_bank as bank


def scope(user_id, course_id):
    return (
        PastQuestion.user_id == user_id,
        PastPaper.user_id == user_id,
        PastPaper.course_id == course_id,
        PastQuestion.status != "SUPERSEDED",
    )


def page(db, user_id, course_id, offset, limit):
    begin_read_snapshot(db)
    owned_course(db, user_id, course_id)
    bank.no_active_attempt(db, user_id, course_id)
    query = select(PastQuestion).join(PastPaper).where(*scope(user_id, course_id))
    total = (
        db.scalar(query.with_only_columns(func.count(), maintain_column_froms=True))
        or 0
    )
    rows = db.execute(
        query.with_only_columns(
            PastQuestion.id,
            PastQuestion.paper_id,
            PastQuestion.number,
            PastQuestion.stem,
            PastQuestion.question_type,
            PastQuestion.status,
            PastQuestion.revision,
            PastQuestion.topic_id,
            func.json_extract(PastQuestion.bank_data_json, "$.topic_ids").label(
                "topic_ids"
            ),
            func.json_extract(PastQuestion.bank_data_json, "$.options").label(
                "options"
            ),
            func.json_extract(PastQuestion.bank_data_json, "$.illustrations").label(
                "illustrations"
            ),
            func.json_extract(PastQuestion.bank_data_json, "$.source_images").label(
                "source_images"
            ),
        )
        .order_by(
            PastPaper.created_at.desc(),
            PastPaper.id,
            PastQuestion.created_at,
            PastQuestion.id,
        )
        .offset(offset)
        .limit(limit)
    ).all()
    items = []

    for row in rows:
        topics = (
            json.loads(row.topic_ids)
            if row.topic_ids
            else [row.topic_id]
            if row.topic_id
            else []
        )
        fingerprint = bank.question_fingerprint(row.stem)
        items.append(
            dict(
                id=row.id,
                paper_id=row.paper_id,
                number=row.number,
                stem=" ".join(row.stem.split())[:70],
                question_type=row.question_type,
                status=row.status,
                revision=row.revision,
                topic_id=row.topic_id,
                bank_data={"topic_ids": topics},
                fingerprint=fingerprint,
            )
        )
    return dict(items=items, total=total, offset=offset, limit=limit)


def detail(db, user_id, question_id):
    row = db.scalar(
        select(PastQuestion)
        .join(PastPaper)
        .where(
            PastQuestion.id == question_id,
            PastQuestion.user_id == user_id,
            PastPaper.user_id == user_id,
            PastQuestion.status != "SUPERSEDED",
        )
    )
    if row is None:
        raise HTTPException(404, "题目不存在或已移出")
    paper = db.get(PastPaper, row.paper_id)
    owned_course(db, user_id, paper.course_id)
    bank.no_active_attempt(db, user_id, paper.course_id)
    return bank.question_payload(row) | {"paper_id": row.paper_id}
