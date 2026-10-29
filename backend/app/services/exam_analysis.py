"""M4 deterministic historical statistics, input fingerprints and discovery bridges."""

import hashlib
import json
from .topic_tree import active_clause
from fastapi import HTTPException
from sqlalchemy import select
from ..models import (
    Topic,
    PastPaper,
    PastQuestion,
    ExamAnalysisReport,
    ExamAttempt,
    ExamPaper,
    Mistake,
)
from ..repositories.materials import checked_chunk
from .courses import owned_course
from . import question_bank as bank
from . import topic_tree
from .search import search_chunks
from .note_search import search_notes
from .asset_organization import asset_page


def topic(db, user_id, topic_id, *, lock=False):
    row = db.scalar(
        select(Topic).where(
            active_clause(), Topic.user_id == user_id, Topic.id == topic_id
        )
    )
    if not row:
        raise HTTPException(404, "知识标签不存在")
    owned_course(db, user_id, row.course_id, lock=lock)
    if row.merged_into_id:
        raise HTTPException(
            409,
            {
                "message": "该标签已合并，请使用目标标签",
                "target_id": row.merged_into_id,
            },
        )
    if lock:
        db.refresh(row)
    return row


def checked_revision(row, revision):
    if row.revision != revision:
        raise HTTPException(
            409,
            {"message": "知识标签已更新，请重新载入", "server_revision": row.revision},
        )


def delete_topic(db, user_id, row, revision):
    checked_revision(row, revision)
    bank.no_active_attempt(db, user_id, row.course_id)
    topics = db.scalars(
        select(Topic).where(
            active_clause(), Topic.user_id == user_id, Topic.course_id == row.course_id
        )
    ).all()
    removed = {row.id}
    for _ in range(len(topics)):
        before = len(removed)
        removed.update(t.id for t in topics if t.merged_into_id in removed)
        if len(removed) == before:
            break
    parent = topic_tree.parent_id(row)
    for t in topics:
        if t.id in removed:
            data = json.loads(t.sources_json)
            data.update(deleted_by_user=True, deleted_at=bank.utc_now().isoformat())
            t.sources_json = bank.encode(data)
            t.revision += 1
        elif topic_tree.parent_id(t) in removed:
            topic_tree.write_parent(t, parent)
            t.revision += 1
    questions = db.scalars(
        select(PastQuestion)
        .join(PastPaper)
        .where(
            PastQuestion.user_id == user_id,
            PastPaper.course_id == row.course_id,
            PastQuestion.status != "SUPERSEDED",
        )
    ).all()
    affected = 0
    for q in questions:
        data = json.loads(q.bank_data_json)
        old_ids = data.get("topic_ids", [q.topic_id] if q.topic_id else [])
        if removed.intersection(old_ids) or q.topic_id in removed:
            data["topic_ids"] = [tid for tid in old_ids if tid not in removed]
            index = data.get("topic_index", {})
            if index:
                index["existing"] = [
                    v
                    for v in index.get("existing", [])
                    if v.get("topic_id") not in removed
                ]
            q.bank_data_json = bank.encode(data)
            q.topic_id = data["topic_ids"][0] if data["topic_ids"] else None
            q.revision += 1
            affected += 1
    db.commit()
    return {"status": "deleted", "id": row.id, "affected_questions": affected}


def rename_topic(db, user_id, row, payload):
    checked_revision(row, payload.revision)
    bank.no_active_attempt(db, user_id, row.course_id)
    name = payload.name.strip()
    aliases = list(
        dict.fromkeys(
            v.strip()
            for v in [*payload.aliases, row.name]
            if v.strip() and v.strip() != name
        )
    )
    if not name or any(len(a) > 240 for a in aliases) or len(aliases) > 30:
        raise HTTPException(422, "名称/别名长度或数量不合法")
    if db.scalar(
        select(Topic.id).where(
            active_clause(),
            Topic.user_id == user_id,
            Topic.course_id == row.course_id,
            Topic.id != row.id,
            Topic.merged_into_id.is_(None),
            Topic.name == name,
        )
    ):
        raise HTTPException(409, "同名标签已存在，请使用合并")
    if "parent_id" in payload.model_fields_set:
        parent = str(payload.parent_id) if payload.parent_id else None
        topic_tree.check_parent(db, user_id, row.course_id, row.id, parent)
        topic_tree.write_parent(row, parent)
    row.name, row.aliases_json = name, bank.encode(aliases)
    row.revision += 1
    db.commit()
    return row


def merge_topic(db, user_id, row, payload):
    checked_revision(row, payload.revision)
    target = topic(db, user_id, str(payload.target_id), lock=True)
    checked_revision(target, payload.target_revision)
    if target.id == row.id or target.course_id != row.course_id:
        raise HTTPException(422, "只能合并同课程不同的有效标签")
    bank.no_active_attempt(db, user_id, row.course_id)
    aliases = list(
        dict.fromkeys(
            [*json.loads(target.aliases_json), row.name, *json.loads(row.aliases_json)]
        )
    )
    if len(aliases) > 30:
        raise HTTPException(422, "合并后别名超过30个，请先整理别名")
    target.aliases_json = bank.encode(aliases)
    citations = json.loads(target.sources_json).get("citations", [])
    for citation in json.loads(row.sources_json).get("citations", []):
        if citation not in citations:
            citations.append(citation)
    if len(citations) > 20:
        raise HTTPException(422, "合并后资料依据超过20条，请先整理")
    links = {
        t.id: topic_tree.parent_id(t)
        for t in topic_tree.rows(db, user_id, row.course_id)
    }
    if target.id in topic_tree.expand(db, user_id, row.course_id, [row.id]):
        raise HTTPException(422, "不能把父标签合并到其子标签")
    children = [
        t
        for t in topic_tree.rows(db, user_id, row.course_id)
        if topic_tree.parent_id(t) == row.id
    ]
    links.pop(row.id, None)
    for child in children:
        links[child.id] = target.id
    try:
        topic_tree.validate_links(links)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    for child in children:
        topic_tree.write_parent(child, target.id)
        child.revision += 1
    target.sources_json = bank.encode(
        json.loads(target.sources_json) | {"citations": citations}
    )
    target.revision += 1
    row.merged_into_id = target.id
    row.revision += 1
    questions = db.scalars(
        select(PastQuestion)
        .join(PastPaper)
        .where(PastQuestion.user_id == user_id, PastPaper.course_id == row.course_id)
    ).all()
    for q in questions:
        data = json.loads(q.bank_data_json)
        ids = data.get("topic_ids", [])
        if row.id in ids:
            data["topic_ids"] = list(
                dict.fromkeys(target.id if t == row.id else t for t in ids)
            )
            q.bank_data_json = bank.encode(data)
            q.revision += 1
        if q.topic_id == row.id:
            q.topic_id = target.id
    db.commit()
    return target


def source_status(db, user_id, course_id, citation):
    try:
        checked_chunk(
            db,
            citation["version_id"],
            citation["chunk_id"],
            citation["quote"],
            user_id,
            course_id,
        )
        return True
    except (HTTPException, KeyError):
        return False


def inputs(db, user_id, course_id):
    owned_course(db, user_id, course_id)
    papers = db.scalars(
        select(PastPaper)
        .where(PastPaper.user_id == user_id, PastPaper.course_id == course_id)
        .order_by(PastPaper.id)
    ).all()
    papers = [
        p for p in papers if not json.loads(p.bank_meta_json).get("deleted_by_user")
    ]
    topics = db.scalars(
        select(Topic)
        .where(active_clause(), Topic.user_id == user_id, Topic.course_id == course_id)
        .order_by(Topic.id)
    ).all()
    questions = db.scalars(
        select(PastQuestion)
        .join(PastPaper)
        .where(
            PastQuestion.user_id == user_id,
            PastPaper.course_id == course_id,
            PastPaper.id.in_([p.id for p in papers]),
        )
        .order_by(PastQuestion.id)
    ).all()
    pool = bank.eligible_questions(db, user_id, course_id, deduplicate=True)
    fingerprint = {
        "papers": [
            (p.id, p.year, p.review_status, p.content_hash, p.bank_meta_json)
            for p in papers
        ],
        "questions": [
            (q.id, q.revision, q.status, q.points, q.bank_data_json) for q in questions
        ],
        "topics": [
            (t.id, t.revision, t.name, t.aliases_json, t.sources_json, t.merged_into_id)
            for t in topics
        ],
        "eligible": [q.id for q, _ in pool],
        "sources": [
            (
                t.id,
                [
                    source_status(db, user_id, course_id, c)
                    for c in json.loads(t.sources_json).get("citations", [])
                ],
            )
            for t in topics
        ],
    }
    return (
        papers,
        topics,
        pool,
        hashlib.sha256(bank.encode(fingerprint).encode()).hexdigest(),
    )


def create_report(db, user_id, course_id):
    owned_course(db, user_id, course_id, lock=True)
    papers, topics, pool, digest = inputs(db, user_id, course_id)
    pmap = {p.id: p for p in papers}
    included = {q.paper_id for q, _ in pool}
    question_years = {q.id: data.get("year", pmap[q.paper_id].year) for q, data in pool}
    years = {year for year in question_years.values() if year is not None}
    known = sum(q.points is not None for q, _ in pool)
    total = sum(q.points or 0 for q, _ in pool)
    rows = []
    for t in topics:
        if t.merged_into_id:
            continue
        descendants = topic_tree.expand(db, user_id, course_id, [t.id])
        matched = [q for q, data in pool if descendants.intersection(data["topic_ids"])]
        primary = [
            q for q, data in pool if data["topic_ids"] and data["topic_ids"][0] == t.id
        ]
        seen_years = {
            question_years[q.id] for q in matched if question_years[q.id] is not None
        }
        points = sum(q.points or 0 for q in primary)
        rows.append(
            {
                "id": t.id,
                "name": t.name,
                "question_ids": [q.id for q in matched],
                "count": len(matched),
                "involvement_rate": len(matched) / len(pool) if pool else None,
                "years": sorted(seen_years),
                "year_rate": len(seen_years) / len(years) if years else None,
                "primary_known_points": points,
                "points_rate": points / total if total else None,
            }
        )
    report = {
        "algorithm": "confirmed-bank-stats-v1",
        "paper_ids": sorted(included),
        "sample_count": len(included),
        "all_papers": len(papers),
        "pending_papers": sum(p.review_status != "CONFIRMED" for p in papers),
        "question_count": len(pool),
        "known_years": sorted(years),
        "unknown_years": sum(
            any(question_years[q.id] is None for q, _ in pool if q.paper_id == pid)
            for pid in included
        ),
        "unknown_points": len(pool) - known,
        "known_points": total,
        "known_points_coverage": known / len(pool) if pool else None,
        "topics": rows,
        "input_revisions": {q.id: q.revision for q, _ in pool},
        "input_papers": [
            {
                "id": pid,
                "year": pmap[pid].year,
                "hash": pmap[pid].content_hash,
                "variant": json.loads(pmap[pid].bank_meta_json).get("variant", ""),
            }
            for pid in sorted(included)
        ],
        "input_topics": {t.id: t.revision for t in topics},
        "by_type": {k: sum(q.question_type == k for q, _ in pool) for k in bank.KINDS},
    }
    row = ExamAnalysisReport(
        user_id=user_id,
        course_id=course_id,
        input_hash=digest,
        report_json=bank.encode(report),
    )
    db.add(row)
    db.commit()
    return report_payload(db, user_id, row.id)


def report_payload(db, user_id, report_id):
    row = db.scalar(
        select(ExamAnalysisReport).where(
            ExamAnalysisReport.user_id == user_id, ExamAnalysisReport.id == report_id
        )
    )
    if not row:
        raise HTTPException(404, "统计报告不存在")
    owned_course(db, user_id, row.course_id)
    _, _, _, digest = inputs(db, user_id, row.course_id)
    if digest != row.input_hash and row.status != "STALE":
        row.status = "STALE"
        db.commit()
    return {
        "id": row.id,
        "course_id": row.course_id,
        "status": row.status,
        "created_at": row.created_at,
        "report": json.loads(row.report_json),
    }


def gaps(db, user_id, report_id):
    response = report_payload(db, user_id, report_id)
    course_id = response["course_id"]
    papers, topics, _, _ = inputs(db, user_id, course_id)
    excluded = {json.loads(p.bank_meta_json).get("version_id") for p in papers}
    attempts = db.scalars(
        select(ExamAttempt)
        .join(ExamPaper)
        .where(
            ExamAttempt.user_id == user_id,
            ExamPaper.course_id == course_id,
            ExamAttempt.status != "IN_PROGRESS",
        )
    ).all()
    topic_map = {t.id: t for t in topics}

    def canonical(tid):
        seen = set()
        while tid in topic_map and topic_map[tid].merged_into_id and tid not in seen:
            seen.add(tid)
            tid = topic_map[tid].merged_into_id
        return tid

    from .mistake_progress import mastered_since

    mistakes = db.scalars(
        select(Mistake.detail_json)
        .join(ExamAttempt, ExamAttempt.id == Mistake.attempt_id)
        .join(ExamPaper, ExamPaper.id == ExamAttempt.paper_id)
        .where(
            Mistake.user_id == user_id,
            ExamPaper.user_id == user_id,
            ExamPaper.course_id == course_id,
        )
    ).all()
    current = [
        json.loads(value)
        for value in mistakes
        if not json.loads(value).get("removed_from_bank")
    ]
    descendant_ids = {
        t.id: topic_tree.expand(db, user_id, course_id, [t.id])
        for t in topics
        if not t.merged_into_id
    }
    matrix = []
    for t in topics:
        if t.merged_into_id:
            continue
        confirmed = [
            c
            for c in json.loads(t.sources_json).get("citations", [])
            if source_status(db, user_id, course_id, c)
        ]
        material_matches, note_matches, image_matches = {}, {}, {}
        # Bounded name/alias discovery; candidates remain unconfirmed.
        for term in [t.name, *json.loads(t.aliases_json)][:4]:
            for item in search_chunks(
                db, user_id, course_id, term[:40], latest_only=True
            ):
                if item["version_id"] not in excluded:
                    material_matches.setdefault(item["chunk_id"], item)
            for item in search_notes(db, user_id, course_id, term, limit=3)["items"]:
                note_matches.setdefault(item["id"], item)
            for item in asset_page(
                db, user_id, course_id, term, None, "all", "newest", 0, 3
            ).items:
                image_matches.setdefault(item.id, item)
        candidates = list(material_matches.values())[:3]
        notes = list(note_matches.values())[:3]
        images = list(image_matches.values())[:3]
        judged = errors = 0
        for a in attempts:
            snapshot = json.loads(a.snapshot_json)
            grades = json.loads(a.grading_json)
            for q in snapshot.get("questions", []):
                if not descendant_ids[t.id].intersection(
                    {canonical(tid) for tid in q.get("topic_ids", [])}
                ):
                    continue
                g = grades.get(q["id"], {})
                if g.get("automatic") or "self_correct" in g:
                    judged += 1
                    errors += g.get("status") in {
                        "incorrect",
                        "unanswered",
                        "self_incorrect",
                    }
        matrix.append(
            {
                "id": t.id,
                "name": t.name,
                "revision": t.revision,
                "confirmed_sources": confirmed,
                "material_candidates": [
                    {
                        "version_id": r["version_id"],
                        "chunk_id": r["chunk_id"],
                        "document_id": r["document_id"],
                        "name": r["document_name"],
                        "quote": r["text"][:300],
                    }
                    for r in candidates
                ],
                "notes": [{"id": n["id"], "title": n["title"]} for n in notes],
                "images": [
                    {"id": image.id, "name": image.name, "alt": image.alt}
                    for image in images
                ],
                "match_status": "confirmed"
                if confirmed
                else "candidate"
                if candidates
                else "unmatched",
                "mastery": "unknown"
                if not judged
                else "needs_review"
                if errors
                else "no_recorded_errors",
                "judged_count": judged,
                "error_count": errors,
                "current_pending": sum(
                    mastered_since(m) is None
                    for m in current
                    if descendant_ids[t.id].intersection(
                        {
                            canonical(tid)
                            for tid in m.get("question", {}).get("topic_ids", [])
                        }
                    )
                ),
                "current_mastered": sum(
                    mastered_since(m) is not None
                    for m in current
                    if descendant_ids[t.id].intersection(
                        {
                            canonical(tid)
                            for tid in m.get("question", {}).get("topic_ids", [])
                        }
                    )
                ),
            }
        )
    return {"report_id": report_id, "status": response["status"], "topics": matrix}
