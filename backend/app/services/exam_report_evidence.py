"""M4 read-only report bridge; candidates and unreviewed mappings are excluded."""

import json
from fastapi import HTTPException
from .exam_analysis import inputs, source_status
from .bank_identity import active


def confirmed_evidence(db, user_id, course_id, sources, paper_ids=None):
    papers, topics, pool, _ = inputs(db, user_id, course_id)
    paper_map = {p.id: p for p in papers}
    if paper_ids is None:
        # General exercise banks are not evidence of a past examination.
        paper_ids = [
            p.id
            for p in papers
            if active(json.loads(p.bank_meta_json)) and p.review_status == "CONFIRMED"
        ]
    if not paper_ids:
        return []
    for identity in paper_ids:
        if (
            identity not in paper_map
            or paper_map[identity].review_status != "CONFIRMED"
            or not active(json.loads(paper_map[identity].bank_meta_json))
        ):
            raise HTTPException(409, "所选真题来源不存在或尚未完成题库核验")
    result = []
    for topic in topics:
        if topic.merged_into_id:
            continue
        citations = [
            c
            for c in json.loads(topic.sources_json).get("citations", [])
            if source_status(db, user_id, course_id, c)
            and any(
                c.get("version_id") == s["version_id"]
                and c.get("chunk_id") == s["source_id"]
                and c.get("quote")
                and c["quote"] in s["text"]
                for s in sources
            )
        ]
        if not citations:
            continue
        for question, data in pool:
            if (
                question.paper_id not in paper_ids
                or topic.id not in data.get("topic_ids", [])
                or data.get("topic_index", {}).get("selection_reviewed") is not True
            ):
                continue
            paper = paper_map.get(question.paper_id)
            if paper is None:
                continue
            result.append(
                dict(
                    topic_id=topic.id,
                    topic_name=topic.name,
                    topic_revision=topic.revision,
                    question_id=question.id,
                    question_revision=question.revision,
                    paper_id=paper.id,
                    paper_title=paper.title,
                    year=paper.year,
                    paper_hash=paper.content_hash,
                    identity_revision=json.loads(paper.bank_meta_json)
                    .get("exam_identity", {})
                    .get("revision", 0),
                    paper_metadata_revision=json.loads(paper.bank_meta_json).get(
                        "revision", 1
                    ),
                    provenance=json.loads(paper.bank_meta_json).get(
                        "provenance", "用户提供"
                    ),
                    citations=citations,
                )
            )
            if len(result) > 100:
                raise HTTPException(422, "所选范围的真题依据超过100项，请缩小资料范围")
    return result
