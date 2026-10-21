"""Revision-checked reversible removal; exam/attempt snapshots are never edited."""

import hashlib
import json
from fastapi import HTTPException
from sqlalchemy import select, update
from pydantic import BaseModel, Field, ConfigDict
from ..models import PastPaper, PastQuestion, ProcessingJob
from .courses import owned_course
from . import question_bank as bank


class Restore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revisions: dict[str, int] = Field(default_factory=dict, max_length=5000)
    paper_revision: int | None = None
    paper_id: str | None = None


class RemovePaper(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    question_snapshot: str = Field(min_length=64, max_length=64)


def question_rows(db, paper_id):
    return db.scalars(
        select(PastQuestion)
        .where(PastQuestion.paper_id == paper_id, PastQuestion.status != "SUPERSEDED")
        .order_by(PastQuestion.id)
    ).all()


def snapshot(rows):
    return hashlib.sha256(
        bank.encode([(q.id, q.revision) for q in rows]).encode()
    ).hexdigest()


def remove_paper(db, user_id, paper_id, payload):
    p = db.scalar(
        select(PastPaper).where(PastPaper.id == paper_id, PastPaper.user_id == user_id)
    )
    if not p:
        raise HTTPException(404, "题库不存在")
    owned_course(db, user_id, p.course_id, lock=True)
    bank.no_active_attempt(db, user_id, p.course_id)
    db.refresh(p)
    meta = json.loads(p.bank_meta_json)
    questions = question_rows(db, paper_id)
    if (
        meta.get("deleted_by_user")
        or payload.revision != meta.get("revision", 1)
        or snapshot(questions) != payload.question_snapshot
    ):
        raise HTTPException(409, "题库或题目已变化，请刷新后再删除")
    if len(questions) > 5000:
        raise HTTPException(422, "本次最多删除5000题，请分批处理")
    revisions = {}
    for q in questions:
        data = json.loads(q.bank_data_json)
        data["removed_by_user"] = True
        q.bank_data_json = bank.encode(data)
        q.status, q.revision = "SUPERSEDED", q.revision + 1
        revisions[q.id] = q.revision
    meta.update(
        deleted_by_user=True,
        revision=meta.get("revision", 1) + 1,
        deleted_question_ids=list(revisions),
    )
    p.bank_meta_json = bank.encode(meta)
    p.review_status = "DRAFT"
    db.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.user_id == user_id,
            ProcessingJob.resource_id == paper_id,
            ProcessingJob.type.in_(["BANK_OCR", "BANK_EXTRACT"]),
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
        .values(
            status="CANCELLED", lease_token=None, lease_until=None, error="题库已删除"
        )
    )
    db.commit()
    return {
        "changed": len(questions),
        "revisions": revisions,
        "paper_id": paper_id,
        "paper_revision": meta["revision"],
    }


def restore(db, user_id, course_id, payload):
    owned_course(db, user_id, course_id, lock=True)
    bank.no_active_attempt(db, user_id, course_id)
    rows = db.scalars(
        select(PastQuestion).where(
            PastQuestion.user_id == user_id, PastQuestion.id.in_(payload.revisions)
        )
    ).all()
    if len(rows) != len(payload.revisions):
        raise HTTPException(404, "题目不存在")
    for q in rows:
        p = db.get(PastPaper, q.paper_id)
        if p.course_id != course_id or (payload.paper_id and p.id != payload.paper_id):
            raise HTTPException(404, "题目不属于当前题库")
        if (
            q.revision != payload.revisions[q.id]
            or q.status != "SUPERSEDED"
            or not json.loads(q.bank_data_json).get("removed_by_user")
        ):
            raise HTTPException(409, "题目已变化或不是用户删除的题目，不能撤销")
    if payload.paper_id:
        p = db.scalar(
            select(PastPaper).where(
                PastPaper.id == payload.paper_id,
                PastPaper.user_id == user_id,
                PastPaper.course_id == course_id,
            )
        )
        if not p:
            raise HTTPException(404, "题库不存在")
        meta = json.loads(p.bank_meta_json)
        if (
            not meta.get("deleted_by_user")
            or meta.get("revision", 1) != payload.paper_revision
            or set(meta.get("deleted_question_ids", [])) != set(payload.revisions)
        ):
            raise HTTPException(409, "题库删除记录已经变化，不能撤销")
        meta.pop("deleted_by_user", None)
        meta.pop("deleted_question_ids", None)
        meta["revision"] = meta.get("revision", 1) + 1
        p.bank_meta_json = bank.encode(meta)
        p.review_status = "DRAFT"
    elif not rows:
        raise HTTPException(422, "请选择要恢复的题目")
    for q in rows:
        p = db.get(PastPaper, q.paper_id)
        if json.loads(p.bank_meta_json).get("deleted_by_user"):
            raise HTTPException(409, "所属题库已删除，请撤销整份题库删除")
        data = json.loads(q.bank_data_json)
        data.pop("removed_by_user", None)
        q.bank_data_json = bank.encode(data)
        q.status, q.revision = "DRAFT", q.revision + 1
        p.review_status = "DRAFT"
    db.commit()
    return {"restored": len(rows)}
