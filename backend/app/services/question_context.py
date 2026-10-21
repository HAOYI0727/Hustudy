"""Freeze complete explicit major-question context while sampling individual items."""

import json
from fastapi import HTTPException
from sqlalchemy import select
from ..models import PastQuestion, PastPaper
from ..repositories.materials import active_version, checked_chunk
from .bank_images import check_images
from .question_display import display_group, order_rows


def validate_sources(db, user_id, course_id, sources, images):
    for source in sources:
        if source.get("source_version_id"):
            active_version(db, source["source_version_id"], user_id, course_id)
        for c in source.get("citations", []):
            checked_chunk(
                db, c["version_id"], c["chunk_id"], c["quote"], user_id, course_id
            )
    for offset in range(0, len(images), 8):
        check_images(db, user_id, course_id, images[offset : offset + 8])


def attach_context(db, user_id, course_id, questions):
    ids = [q["source_question_id"] for q in questions if q.get("source_question_id")]
    selected = {
        q.id: q
        for q in db.scalars(
            select(PastQuestion).where(
                PastQuestion.user_id == user_id, PastQuestion.id.in_(ids)
            )
        ).all()
    }
    papers = {
        p.id: p
        for p in db.scalars(
            select(PastPaper).where(
                PastPaper.user_id == user_id,
                PastPaper.course_id == course_id,
                PastPaper.id.in_({q.paper_id for q in selected.values()}),
            )
        ).all()
    }
    rows = db.scalars(
        select(PastQuestion).where(
            PastQuestion.user_id == user_id, PastQuestion.paper_id.in_(papers)
        )
    ).all()
    rows = order_rows(rows)
    total = 0
    for snapshot in questions:
        q = selected.get(snapshot.get("source_question_id"))
        if not q or q.paper_id not in papers:
            continue  # Historical non-bank questions keep their original snapshot.
        paper_meta = json.loads(papers[q.paper_id].bank_meta_json)
        deleted = set(paper_meta.get("deleted_question_ids", []))
        deleted.update(
            r.id
            for r in rows
            if r.paper_id == q.paper_id
            and json.loads(r.bank_data_json).get("removed_by_user")
        )
        group = display_group(q.number, q.paper_id)
        if not group:
            continue
        # Superseded split ancestors retain the full original problem statement.
        ancestors, pending = set(), [q]
        while pending:
            item = pending.pop()
            for source_id in json.loads(item.bank_data_json).get(
                "source_question_ids", []
            ):
                parent = next(
                    (r for r in rows if r.id == source_id and r.paper_id == q.paper_id),
                    None,
                )
                if (
                    parent
                    and parent.id not in deleted
                    and parent.id not in ancestors
                    and parent.id != q.id
                ):
                    ancestors.add(parent.id)
                    pending.append(parent)
        deleted_in_group = any(
            r.id in deleted
            and (display_group(r.number, r.paper_id) or {}).get("key") == group["key"]
            for r in rows
            if r.paper_id == q.paper_id
        )
        if deleted_in_group and any(
            r.id in ancestors and r.stem.strip() not in q.stem for r in rows
        ):
            raise HTTPException(
                422,
                "大题部分子问已删除，无法安全补全完整上下文；请先将公共条件补入当前题干",
            )
        members = [
            r
            for r in rows
            if r.paper_id == q.paper_id
            and r.id != q.id
            and r.id not in deleted
            and (
                (
                    r.status != "SUPERSEDED"
                    and (display_group(r.number, r.paper_id) or {}).get("key")
                    == group["key"]
                )
                or (r.id in ancestors and not deleted_in_group)
            )
        ]
        if not members:
            continue
        if len(members) > 200:
            raise HTTPException(422, "同一大题的上下文过多，请先整理题号与公共条件")
        text, images, sources, seen = [], [], [], set()
        for row in members:
            data = json.loads(row.bank_data_json)
            if data.get("illustrations") and not data.get("images_reviewed"):
                raise HTTPException(422, "同一大题有尚未审核的插图，请先核对后抽题")
            body = row.stem
            if data.get("options"):
                body += "\n\n" + "\n".join(
                    f"{chr(65 + i)}. {s}" for i, s in enumerate(data["options"])
                )
            if body.strip() and body.strip() not in seen:
                text.append(f"### 原题 {row.number}\n\n{body}")
                seen.add(body.strip())
            sources.append(
                {
                    "source_version_id": data.get("source_version_id"),
                    "citations": data.get("citations", []),
                }
            )
            for image in data.get("illustrations", []):
                if image not in images and image not in snapshot.get(
                    "illustrations", []
                ):
                    images.append(image)
        context = "\n\n".join(text)
        total += len(context)
        if len(context) > 50000 or total > 500000 or len(images) > 40:
            raise HTTPException(
                422, "完整大题题干或插图超过预算，请减少题数或整理公共条件；未截断内容"
            )
        validate_sources(db, user_id, course_id, sources, images)
        snapshot.update(
            context_stem=context, context_illustrations=images, context_sources=sources
        )
    return questions
