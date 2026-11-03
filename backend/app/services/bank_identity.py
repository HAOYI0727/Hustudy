"""Owner-confirmed exam identity, independent of question-content review."""

import json
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from ..models import PastPaper
from ..models.base import utc_now
from . import question_bank as bank
from .courses import owned_course


def validate(value):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - {
        "kind",
        "confirmed",
        "revision",
        "confirmed_at",
    }:
        raise ValueError("真题身份结构不合法")
    if (
        value.get("kind") not in {"exercise", "past_exam"}
        or type(value.get("confirmed")) is not bool
    ):
        raise ValueError("真题身份或确认状态不合法")
    if value["kind"] == "exercise" and value["confirmed"]:
        raise ValueError("普通练习不能确认真题身份")
    revision = value.get("revision", 0)  # legacy v1 snapshots remain readable
    if type(revision) is not int or revision < 0:
        raise ValueError("身份修订号不合法")
    stamp = value.get("confirmed_at")
    if stamp is not None:
        try:
            valid = (
                isinstance(stamp, str)
                and datetime.fromisoformat(stamp).tzinfo is not None
            )
        except ValueError:
            valid = False
        if not valid or not value["confirmed"]:
            raise ValueError("身份确认时间不合法")
    return value


def active(meta):
    try:
        identity = validate(meta.get("exam_identity"))
    except ValueError:
        return False
    return bool(identity and identity["kind"] == "past_exam" and identity["confirmed"])


def prepare(row, payload):
    meta = json.loads(row.bank_meta_json)
    expected = payload.pop("expected_revision")
    if meta.get("deleted_by_user"):
        raise HTTPException(404, "题库已删除")
    if meta.get("revision", 1) != expected:
        raise HTTPException(409, "题库元数据已变化，请保留输入并刷新后重试")
    previous = dict(meta)
    title = payload.pop("title").strip() if "title" in payload else row.title
    if not title:
        raise HTTPException(422, "题库名称不能为空")
    year = payload.pop("year", row.year)
    requested = payload.pop("exam_identity", None)
    relevant_changed = year != row.year or any(
        payload.get(k, meta.get(k, "用户提供" if k == "provenance" else ""))
        != meta.get(k, "用户提供" if k == "provenance" else "")
        for k in ("variant", "provenance")
    )
    meta.update(payload)
    identity = meta.get("exam_identity")
    if requested is not None:
        try:
            validate(requested)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        if requested["confirmed"] and meta.get("provenance", "用户提供").strip() in {
            "",
            "用户提供",
        }:
            raise HTTPException(422, "确认真题前请填写具体来源说明")
    if relevant_changed and requested and requested["confirmed"]:
        raise HTTPException(422, "请先保存年份、卷别和来源变化，再重新确认真题身份")
    if requested is not None or (relevant_changed and identity is not None):
        target = requested or {
            "kind": identity.get("kind", "exercise") if identity else "exercise",
            "confirmed": False,
        }
        # Changing provenance requires a separate fresh identity confirmation.
        if relevant_changed:
            target = target | {"confirmed": False}
        old_pair = (
            (identity.get("kind"), identity.get("confirmed"))
            if identity
            else (None, False)
        )
        if old_pair != (target["kind"], target["confirmed"]) or (
            relevant_changed and identity and identity.get("confirmed")
        ):
            meta["exam_identity"] = dict(
                kind=target["kind"],
                confirmed=target["confirmed"],
                revision=(identity or {}).get("revision", 0) + 1,
                confirmed_at=utc_now().isoformat() if target["confirmed"] else None,
            )
    if meta != previous or year != row.year or title != row.title:
        meta["revision"] = expected + 1
    return title, year, meta


def edit_batch(db, user_id, course_id, items):
    owned_course(db, user_id, course_id, lock=True)
    bank.no_active_attempt(db, user_id, course_id)
    ids = [str(item["paper_id"]) for item in items]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "批量题库不能重复")
    rows = db.scalars(
        select(PastPaper)
        .where(
            PastPaper.id.in_(ids),
            PastPaper.user_id == user_id,
            PastPaper.course_id == course_id,
        )
        .execution_options(populate_existing=True)
    ).all()
    if len(rows) != len(ids):
        raise HTTPException(404, "所选题库不存在或不属于当前课程")
    prepared = []
    by_id = {row.id: row for row in rows}
    for item in items:
        row = by_id[str(item["paper_id"])]
        payload = {k: v for k, v in item.items() if k != "paper_id"}
        target_id = payload.get("duplicate_of")
        if target_id:
            target = db.scalar(
                select(PastPaper).where(
                    PastPaper.id == str(target_id),
                    PastPaper.user_id == user_id,
                    PastPaper.course_id == course_id,
                )
            )
            if not target or json.loads(target.bank_meta_json).get("deleted_by_user"):
                raise HTTPException(404, "代表试卷不存在")
            if target.id == row.id or json.loads(target.bank_meta_json).get(
                "duplicate_of"
            ):
                raise HTTPException(422, "重复材料必须指向独立代表卷")
        prepared.append((row, *prepare(row, payload)))
    # Also validate the final graph when several representative decisions change together.
    resulting = {row.id: meta for row, _, _, meta in prepared}
    for row, _, _, meta in prepared:
        if meta.get("duplicate_of") in resulting and resulting[
            meta["duplicate_of"]
        ].get("duplicate_of"):
            raise HTTPException(422, "批量决定不能形成重复代表链或循环")
    for row, title, year, meta in prepared:
        row.title, row.year, row.bank_meta_json = title, year, bank.encode(meta)
    db.commit()
    return {
        "changed": len(prepared),
        "revisions": {row.id: meta.get("revision", 1) for row, _, _, meta in prepared},
    }
