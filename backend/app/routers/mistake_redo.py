"""Owned redo sessions appended to mistakes; original attempt snapshots stay intact."""

from copy import deepcopy
import json
from uuid import UUID
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import User, Mistake, ExamAttempt, ExamPaper, Course
from ..services.exam_retirement import check_mistake_course
from ..services import question_bank as bank
from ..services.mistake_progress import mastered_since, next_sequence

router = APIRouter(prefix="/api/v1", tags=["mistake-redo"])


class Start(BaseModel):
    request_id: UUID


class Submit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str | list[str] | bool | None = None

    @field_validator("answer")
    @classmethod
    def bounded(cls, value):
        values = value if isinstance(value, list) else [value]
        if len(values) > 30 or any(
            isinstance(v, str) and len(v) > 20000 for v in values
        ):
            raise ValueError("答案过长")
        return value


class Judge(BaseModel):
    correct: bool


def owned(db, user_id, mid):
    check_mistake_course(db, user_id, mid, lock=True)
    row = db.scalar(
        select(Mistake).where(Mistake.id == mid, Mistake.user_id == user_id)
    )
    db.refresh(row)
    data = json.loads(row.detail_json)
    if data.get("removed_from_bank"):
        raise HTTPException(404, "此错题已移出错题库")
    return row, data


def public(record):
    q = bank.public_question(record["question"])
    if record["status"] != "IN_PROGRESS":
        q.update(
            answer=record["question"].get("answer"),
            blank_answers=record["question"].get("blank_answers", []),
            explanation=record["question"].get("explanation", ""),
        )
    return {k: v for k, v in record.items() if k != "question"} | {"question": q}


def save(db, row, data):
    row.detail_json = bank.encode(data)
    db.commit()


@router.get("/mistakes/daily-progress")
def daily(
    goal: int = Query(3, ge=0, le=1000),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    today = bank.utc_now().astimezone(ZoneInfo(user.timezone)).date()
    rows = db.scalars(
        select(Mistake)
        .join(ExamAttempt, Mistake.attempt_id == ExamAttempt.id)
        .join(ExamPaper, ExamAttempt.paper_id == ExamPaper.id)
        .join(Course, ExamPaper.course_id == Course.id)
        .where(
            Mistake.user_id == user.id,
            Course.user_id == user.id,
            Course.deleted_at.is_(None),
        )
    ).all()
    active = set()
    completed = set()
    for row in rows:
        data = json.loads(row.detail_json)
        success = mastered_since(data)
        if not data.get("removed_from_bank") and success is None:
            active.add(row.id)
        if success and success.astimezone(ZoneInfo(user.timezone)).date() == today:
            completed.add(row.id)
    target = min(goal, len(active | completed))
    done = len(completed)
    return {
        "date": today.isoformat(),
        "goal": goal,
        "target": target,
        "completed": done,
        "available": len(active),
        "done": done >= target,
        "remaining_ids": sorted(active - completed),
        "completed_ids": sorted(completed),
    }


@router.post("/mistakes/{mid}/redoes")
def start(
    mid: str,
    payload: Start,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row, data = owned(db, user.id, mid)
    items = data.setdefault("redoes", {})
    key = str(payload.request_id)
    if key in items:
        return public(items[key])
    if sum(v["status"] == "IN_PROGRESS" for v in items.values()) >= 20:
        raise HTTPException(409, "未完成重做较多，请先完成已打开的题目")
    q = deepcopy(data["question"])
    from ..services.bank_question_types import normalize_snapshot

    normalize_snapshot(q)
    q.setdefault("type", "solution")
    q.setdefault("points", 1)
    q.setdefault("id", row.question_id)
    if q.get("type") == "single_choice" and len(q.get("options", [])) == 4:
        order = list(range(4))
        bank.RNG.shuffle(order)
        q["options"] = [q["options"][i] for i in order]
        if q.get("answer") in list("ABCD"):
            q["answer"] = "ABCD"[order.index("ABCD".index(q["answer"]))]
    record = {
        "id": key,
        "question": q,
        "status": "IN_PROGRESS",
        "answer": None,
        "grading": None,
        "correct": None,
    }
    items[key] = record
    save(db, row, data)
    return public(record)


@router.post("/mistakes/{mid}/redoes/{rid}/submit")
def submit(
    mid: str,
    rid: str,
    payload: Submit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row, data = owned(db, user.id, mid)
    record = data.get("redoes", {}).get(rid)
    if not record:
        raise HTTPException(404, "重做记录不存在")
    if record["status"] != "IN_PROGRESS":
        if record["answer"] != payload.answer:
            raise HTTPException(409, "本次重做已提交，不能覆盖")
        return public(record)
    grading = bank.grade(record["question"], payload.answer)
    if not grading["submitted"]:
        raise HTTPException(422, "请先作答再提交重做")
    record["answer"] = payload.answer
    record["grading"] = grading
    if record["grading"]["automatic"]:
        sequence = next_sequence(data)
        record.update(
            status="COMPLETED",
            correct=record["grading"]["status"] == "correct",
            completed_at=bank.utc_now().isoformat(),
            sequence=sequence,
        )
    else:
        record["status"] = "NEEDS_SELF_REVIEW"
    save(db, row, data)
    return public(record)


@router.post("/mistakes/{mid}/redoes/{rid}/judge")
def judge(
    mid: str,
    rid: str,
    payload: Judge,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row, data = owned(db, user.id, mid)
    record = data.get("redoes", {}).get(rid)
    if not record:
        raise HTTPException(404, "重做记录不存在")
    if record["status"] == "IN_PROGRESS":
        raise HTTPException(409, "请先提交本次答案")
    if record["grading"]["automatic"]:
        raise HTTPException(422, "此题已有自动判定")
    if record["status"] == "COMPLETED":
        if record["correct"] != payload.correct:
            raise HTTPException(409, "本次已判断，不能重复覆盖")
        return public(record)
    sequence = next_sequence(data)
    record.update(
        status="COMPLETED",
        correct=payload.correct,
        completed_at=bank.utc_now().isoformat(),
        sequence=sequence,
    )
    save(db, row, data)
    return public(record)


@router.delete("/mistakes/{mid}")
def remove(mid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row, data = owned(db, user.id, mid)
    if mastered_since(data) is None:
        raise HTTPException(409, "重做正确后才可移出，或继续保留")
    data["removed_from_bank"] = True
    save(db, row, data)
    return {"status": "removed"}
