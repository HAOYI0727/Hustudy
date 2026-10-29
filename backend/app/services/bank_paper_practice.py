"""Complete source papers, without random sampling or silent omissions."""

import json
from fastapi import HTTPException
from sqlalchemy import select
from ..models import ExamBlueprint, ExamPaper, PastPaper, PastQuestion
from . import question_bank as bank
from .courses import owned_course
from .question_display import order_rows, display_group

MAX_QUESTIONS = 500


def papers(db, user_id, course_id):
    owned_course(db, user_id, course_id)
    eligible = {
        q.id
        for q, _ in bank.eligible_questions(db, user_id, course_id, deduplicate=False)
    }
    rows = db.scalars(
        select(PastQuestion)
        .join(PastPaper)
        .where(
            PastPaper.user_id == user_id,
            PastPaper.course_id == course_id,
            PastQuestion.user_id == user_id,
            PastQuestion.status != "SUPERSEDED",
        )
    ).all()
    counts = {}
    units = {}
    for q in rows:
        total, valid = counts.get(q.paper_id, (0, 0))
        counts[q.paper_id] = (total + 1, valid + (q.id in eligible))
        group = display_group(q.number, q.paper_id)
        units.setdefault(q.paper_id, set()).add(group["key"] if group else q.id)
    result = []
    for p in db.scalars(
        select(PastPaper)
        .where(
            PastPaper.user_id == user_id,
            PastPaper.course_id == course_id,
        )
        .order_by(PastPaper.created_at.desc(), PastPaper.id)
        .limit(200)
    ):
        if json.loads(p.bank_meta_json).get("deleted_by_user"):
            continue
        total, valid = counts.get(p.id, (0, 0))
        reason = (
            "试卷尚未确认"
            if p.review_status != "CONFIRMED"
            else "试卷没有有效题目"
            if total == 0
            else f"{total - valid}题待确认或来源失效，请先校正"
            if valid != total
            else f"超过整卷练习{MAX_QUESTIONS}题上限"
            if total > MAX_QUESTIONS
            else ""
        )
        result.append(
            {
                "id": p.id,
                "title": p.title,
                "year": p.year,
                "question_count": total,
                "major_question_count": len(units.get(p.id, set())),
                "eligible_count": valid,
                "available": not reason,
                "reason": reason,
            }
        )
    return result


def create(db, user_id, course_id, source_id, payload):
    owned_course(db, user_id, course_id, lock=True)
    source = db.scalar(
        select(PastPaper).where(
            PastPaper.id == source_id,
            PastPaper.user_id == user_id,
            PastPaper.course_id == course_id,
        )
    )
    if not source or json.loads(source.bank_meta_json).get("deleted_by_user"):
        raise HTTPException(404, "试卷不存在或已移除")
    key = str(payload.request_id)
    config = payload.model_dump(mode="json") | {
        "source_paper_id": source_id,
        "practice_mode": "whole_paper",
    }
    existing = db.get(ExamBlueprint, key)
    if existing:
        if existing.user_id != user_id or existing.course_id != course_id:
            raise HTTPException(404, "练习请求不可访问")
        if json.loads(existing.config_json) != config:
            raise HTTPException(409, "同一练习请求不能更改条件")
        paper = db.scalar(
            select(ExamPaper).where(
                ExamPaper.blueprint_id == key, ExamPaper.user_id == user_id
            )
        )
        if paper:
            return paper
    bank.no_active_attempt(db, user_id, course_id)
    rows = db.scalars(
        select(PastQuestion)
        .where(
            PastQuestion.paper_id == source_id,
            PastQuestion.user_id == user_id,
            PastQuestion.status != "SUPERSEDED",
        )
        .order_by(PastQuestion.created_at, PastQuestion.id)
    ).all()
    eligible = {
        q.id: data
        for q, data in bank.eligible_questions(
            db, user_id, course_id, paper_id=source_id, deduplicate=False
        )
    }
    if (
        source.review_status != "CONFIRMED"
        or not rows
        or any(q.id not in eligible for q in rows)
    ):
        raise HTTPException(
            422, "整卷题目须全部确认且来源有效，请先完成题库校正；不会跳过题目"
        )
    if len(rows) > MAX_QUESTIONS:
        raise HTTPException(422, f"整卷练习最多{MAX_QUESTIONS}题，不会截断试卷")
    questions = [
        bank.shuffled_question(q, eligible[q.id], shuffle_options=False)
        | {"source_number": q.number, "practice_unit": "major"}
        for q in order_rows(rows)
    ]
    from .question_context import attach_context

    attach_context(db, user_id, course_id, questions)
    title = f"{source.title[:230]} · 整卷练习"
    db.add(
        ExamBlueprint(
            id=key,
            user_id=user_id,
            course_id=course_id,
            name=title,
            config_json=bank.encode(config),
        )
    )
    paper = ExamPaper(
        user_id=user_id,
        course_id=course_id,
        blueprint_id=key,
        title=title,
        mode="question_bank",
        questions_json=bank.encode(questions),
    )
    db.add(paper)
    db.commit()
    return paper
