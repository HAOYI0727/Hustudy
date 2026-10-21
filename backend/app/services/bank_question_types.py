"""Retire source fill-in questions without rewriting any exam/attempt snapshots."""

import json
from sqlalchemy import select
from ..models import PastQuestion


def solution_reference(answer, blanks):
    return answer or (" || ".join(str(v) for v in blanks) if blanks else None)


def normalize_snapshot(question):
    if question.get("type") == "fill_blank":
        question["type"] = "solution"
        question["answer"] = solution_reference(
            question.get("answer"), question.get("blank_answers", [])
        )
        question.pop("unique_answer", None)
        question.pop("blank_answers", None)
        question.pop("blank_count", None)
    return question


def convert_sources(db, question_ids=None):
    query = select(PastQuestion).where(PastQuestion.question_type == "fill_blank")
    if question_ids is not None:
        query = query.where(PastQuestion.id.in_(question_ids))
    rows = db.scalars(query).all()
    for q in rows:
        data = json.loads(q.bank_data_json)
        q.question_type = "solution"
        q.answer = solution_reference(q.answer, data.get("blank_answers", []))
        data["retired_fill_blank"] = {
            "blank_answers": data.get("blank_answers", []),
            "unique_answer": data.get("unique_answer"),
        }
        data["blank_answers"], data["unique_answer"] = [], None
        q.bank_data_json = json.dumps(data, ensure_ascii=False)
        q.revision += 1
    db.flush()
    return len(rows)


def upgrade_local_sources():
    from datetime import datetime, timezone
    from pathlib import Path
    import sqlite3
    from ..core.database import SessionLocal, engine

    with SessionLocal() as db:
        if not db.scalar(
            select(PastQuestion.id)
            .where(PastQuestion.question_type == "fill_blank")
            .limit(1)
        ):
            return
    # SQLite online backup includes committed WAL pages.
    if engine.url.database and engine.url.database != ":memory:":
        path = Path(engine.url.database)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        with (
            sqlite3.connect(str(path)) as source,
            sqlite3.connect(str(path) + f".pre-fill-retirement-{stamp}.bak") as target,
        ):
            source.backup(target)
    with SessionLocal() as db:
        convert_sources(db)
        db.commit()
