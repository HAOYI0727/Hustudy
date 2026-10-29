"""Explicit attempt removal with its mistakes, review plans and relapse links."""

import json
from fastapi import HTTPException
from sqlalchemy import delete, select
from ..models import ExamAttempt, Mistake, ReviewTask
from .exam_retirement import check_attempt_course


def remove(db, user_id, attempt_id, confirm):
    if not confirm:
        raise HTTPException(422, "请确认一并删除关联错题与复习计划")
    check_attempt_course(db, user_id, attempt_id, lock=True)
    attempt = db.get(ExamAttempt, attempt_id)
    mistakes = db.scalars(
        select(Mistake).where(
            Mistake.user_id == user_id,
            Mistake.attempt_id == attempt_id,
        )
    ).all()
    ids = [m.id for m in mistakes]
    plans = db.execute(
        delete(ReviewTask).where(
            ReviewTask.user_id == user_id,
            ReviewTask.mistake_id.in_(ids),
        )
    ).rowcount
    # A later wrong answer can be recorded as a relapse on an earlier mistake.
    # Remove only events belonging to this attempt, preserving other progress.
    for row in db.scalars(
        select(Mistake).where(
            Mistake.user_id == user_id,
            Mistake.attempt_id != attempt_id,
        )
    ):
        data = json.loads(row.detail_json)
        events = data.get("relapses", {})
        kept = {
            key: value
            for key, value in events.items()
            if value.get("attempt_id") != attempt_id
        }
        if len(kept) != len(events):
            data["relapses"] = kept
            row.detail_json = json.dumps(data, ensure_ascii=False)
    for row in mistakes:
        db.delete(row)
    db.flush()
    db.delete(attempt)
    db.commit()
    return {
        "deleted": True,
        "mistakes_deleted": len(ids),
        "review_tasks_deleted": plans,
    }
