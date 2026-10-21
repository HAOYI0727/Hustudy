"""Atomic leaf-question split/merge; never rewrite prior attempt snapshots."""

import json
from fastapi import HTTPException
from sqlalchemy import select
from ..models import PastPaper, PastQuestion
from . import question_bank as bank
from .courses import owned_course
from .bank_markdown import normalize


def sync_review_status(db, papers):
    """Derive review state from all current leaves, after pending writes are flushed."""
    db.flush()
    for paper in {p.id: p for p in papers}.values():
        statuses = db.scalars(
            select(PastQuestion.status).where(
                PastQuestion.paper_id == paper.id,
                PastQuestion.user_id == paper.user_id,
                PastQuestion.status != "SUPERSEDED",
            )
        ).all()
        paper.review_status = (
            "CONFIRMED"
            if statuses and all(s == "CONFIRMED" for s in statuses)
            else "DRAFT"
        )
    db.flush()


def owned_question(db, user_id, question_id):
    q = db.scalar(
        select(PastQuestion).where(
            PastQuestion.user_id == user_id, PastQuestion.id == question_id
        )
    )
    if not q:
        raise HTTPException(404, "题目不存在")
    paper = db.get(PastPaper, q.paper_id)
    owned_course(db, user_id, paper.course_id, lock=True)
    bank.no_active_attempt(db, user_id, paper.course_id)
    db.refresh(q)
    if q.status == "SUPERSEDED":
        raise HTTPException(409, "原题已拆合，请重新载入当前题目")
    return q, paper


def split(db, user_id, q, paper, payload):
    if q.revision != payload.revision:
        raise HTTPException(409, "题目已变化，请先保留本地内容并刷新")
    old = json.loads(q.bank_data_json)
    if len(old.get("topic_ids", [])) > 5:
        raise HTTPException(422, "原题超过每题5个标签的上限，请先整理标签再拆分")
    result = []
    for n, part in enumerate(payload.parts, 1):
        if not part.strip() or len(part) > 20000:
            raise HTTPException(422, "每个子题应为1–20000字符")
        parsed = bank.parse_text(part)
        if len(parsed) != 1:
            raise HTTPException(422, "每个分段只能包含一个子题")
        item = parsed[0]
        data = {
            "content_format": "markdown",
            "options": [normalize(o) for o in item["options"]],
            "blank_answers": item["blank_answers"],
            "unique_answer": None,
            "topic_ids": old.get("topic_ids", []),
            "citations": old.get("citations", []),
            "explanation": normalize(item["explanation"]),
            "source_question_ids": [q.id],
            "parent_points": q.points,
            "source_images": old.get("source_images", []),
            "source_version_id": old.get("source_version_id"),
            "illustrations": old.get("illustrations", []),
            "images_reviewed": False,
        }
        child = PastQuestion(
            user_id=user_id,
            paper_id=paper.id,
            number=f"{q.number}-{n}",
            stem=normalize(item["stem"]),
            question_type=item["kind"],
            points=item["points"],
            answer=item["answer"],
            answer_source="user_provided" if item["answer"] else "unknown",
            topic_id=q.topic_id,
            bank_data_json=bank.encode(data),
        )
        db.add(child)
        result.append(child)
    q.status = "SUPERSEDED"
    q.revision += 1
    paper.review_status = "DRAFT"
    db.commit()
    return [bank.question_payload(child) for child in result]


def merge(db, user_id, course_id, payload):
    owned_course(db, user_id, course_id, lock=True)
    bank.no_active_attempt(db, user_id, course_id)
    ids = [str(i) for i in payload.question_ids]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "合并列表不能重复")
    rows = []
    for qid in ids:
        q, paper = owned_question(db, user_id, qid)
        if paper.course_id != course_id:
            raise HTTPException(404, "题目不属于当前课程")
        if q.revision != payload.revisions.get(q.id):
            raise HTTPException(409, "合并题目已有修订，请刷新后重选")
        rows.append(q)
    if len({q.paper_id for q in rows}) != 1:
        raise HTTPException(422, "只能合并同一份题库中的题目")
    topic_ids = []
    citations = []
    for q in rows:
        data = json.loads(q.bank_data_json)
        topic_ids.extend(data.get("topic_ids", []))
        for c in data.get("citations", []):
            if c not in citations:
                citations.append(c)
    topic_ids = list(dict.fromkeys(topic_ids))
    if len(topic_ids) > 5:
        raise HTTPException(422, "合并后标签超过5个，请先整理")
    source_images, illustrations = [], []
    for q in rows:
        data = json.loads(q.bank_data_json)
        for key, target in [
            ("source_images", source_images),
            ("illustrations", illustrations),
        ]:
            for image in data.get(key, []):
                if image not in target:
                    target.append(image)
    if len(illustrations) > 8:
        raise HTTPException(422, "合并后的插图超过8张，请先整理")
    merged = PastQuestion(
        user_id=user_id,
        paper_id=rows[0].paper_id,
        number=rows[0].number + "合并",
        stem=normalize(payload.stem),
        question_type="solution",
        points=None,
        answer_source="unknown",
        topic_id=topic_ids[0] if topic_ids else None,
        bank_data_json=bank.encode(
            {
                "topic_ids": topic_ids,
                "citations": citations,
                "options": [],
                "blank_answers": [],
                "unique_answer": None,
                "explanation": "",
                "content_format": "markdown",
                "source_question_ids": ids,
                "source_images": source_images,
                "source_version_id": json.loads(rows[0].bank_data_json).get(
                    "source_version_id"
                ),
                "illustrations": illustrations,
                "images_reviewed": False,
            }
        ),
    )
    db.add(merged)
    for q in rows:
        q.status = "SUPERSEDED"
        q.revision += 1
    paper.review_status = "DRAFT"
    db.commit()
    return bank.question_payload(merged)


def save_question(db, user_id, question_id, payload, *, commit=True, course_id=None):
    question = db.scalar(
        select(PastQuestion).where(
            PastQuestion.id == question_id, PastQuestion.user_id == user_id
        )
    )
    if not question:
        raise HTTPException(404, "题目不存在")
    paper = db.get(PastPaper, question.paper_id)
    if course_id is not None and paper.course_id != course_id:
        raise HTTPException(404, "题目不属于当前课程")
    owned_course(db, user_id, paper.course_id, lock=True)
    bank.no_active_attempt(db, user_id, paper.course_id)
    db.refresh(question)
    if question.status == "SUPERSEDED":
        raise HTTPException(409, "原题已拆合，请编辑当前题目")
    if question.revision != payload.revision:
        raise HTTPException(
            409,
            {
                "message": "题目已被修改，请保留本地内容后重新载入",
                "server_revision": question.revision,
            },
        )
    bank.topic_rows(db, user_id, paper.course_id, payload.topic_ids)
    old = json.loads(question.bank_data_json)
    if payload.question_type == "solution" and (
        payload.blank_answers or payload.unique_answer is not None
    ):
        from .bank_question_types import solution_reference

        payload = payload.model_copy(
            update={
                "question_type": "solution",
                "answer": solution_reference(payload.answer, payload.blank_answers),
                "unique_answer": None,
                "blank_answers": [],
            }
        )
    from ..services.bank_images import check_images

    images = check_images(
        db,
        user_id,
        paper.course_id,
        payload.illustrations
        if payload.illustrations is not None
        else old.get("illustrations", []),
    )
    from ..services.bank_markdown import normalize

    payload = payload.model_copy(
        update={
            "stem": normalize(payload.stem),
            "options": [normalize(o) for o in payload.options],
            "explanation": normalize(payload.explanation),
        }
    )
    same_input = (
        question.stem == payload.stem.strip()
        and old.get("options", []) == payload.options
    )
    previous_status = question.status
    previous = (
        question.stem,
        question.question_type,
        question.answer or None,
        question.points,
        old.get("options", []),
        old.get("unique_answer"),
        old.get("blank_answers", []),
        old.get("topic_ids", [question.topic_id] if question.topic_id else []),
        old.get("explanation", ""),
        old.get("illustrations", []),
        bool(old.get("images_reviewed", False)),
    )
    question.stem, question.question_type, question.answer, question.points = (
        payload.stem.strip(),
        payload.question_type,
        normalize(payload.answer)
        if payload.question_type == "solution"
        else payload.answer,
        payload.points,
    )
    question.answer_source = "user_confirmed" if payload.answer else "unknown"
    ids = list(dict.fromkeys(str(t) for t in payload.topic_ids))
    question.topic_id = ids[0] if ids else None
    question.bank_data_json = bank.encode(
        old
        | {
            "content_format": "markdown",
            "options": payload.options,
            "unique_answer": payload.unique_answer,
            "blank_answers": payload.blank_answers,
            "topic_ids": ids,
            "topic_index": (old.get("topic_index", {}) | {"selection_reviewed": True})
            if same_input
            else {},
            "explanation": payload.explanation,
            "citations": old.get("citations", []),
            "illustrations": images,
            "images_reviewed": payload.images_reviewed,
            "content_profile": "user_corrected"
            if question.stem != "待补充题干（仅答案或解析）"
            else old.get("content_profile"),
        }
    )
    question.revision += 1
    current = (
        question.stem,
        question.question_type,
        question.answer or None,
        question.points,
        payload.options,
        payload.unique_answer,
        payload.blank_answers,
        ids,
        payload.explanation,
        images,
        payload.images_reviewed,
    )
    question.status = previous_status if previous == current else "DRAFT"
    sync_review_status(db, [paper])
    if commit:
        db.commit()
    return bank.question_payload(question)
