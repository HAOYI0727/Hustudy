"""Frozen supplemental inputs and server-derived report labels; no model authority."""

import json
from fastapi import HTTPException
from .note_ai_sources import selected_notes
from .exam_report_evidence import confirmed_evidence
from .reading_report_evidence import teacher_emphases

KEY = "m2_supplement"
ORIGINS = {
    "ai_suggestion": "AI建议",
    "teacher_mark": "教师强调",
    "observed_exam": "已确认真题",
}


def context(sources):
    return sources[0].get(KEY, {}) if sources else {}


def freeze(db, user_id, course_id, sources, selection, is_report):
    notes = selected_notes(db, user_id, course_id, selection.note_ids)
    marks = teacher_emphases(db, user_id, course_id, sources) if is_report else []
    exams = confirmed_evidence(db, user_id, course_id, sources) if is_report else []
    if notes or is_report:
        sources[0][KEY] = dict(
            version=2,
            automatic_report_sources=is_report,
            notes=notes,
            teacher_marks=marks,
            exam_evidence=exams,
            # Enough original scope to recheck historical empty/changed evidence.
            evidence_scope=[
                dict(
                    version_id=s["version_id"], source_id=s["source_id"], text=s["text"]
                )
                for s in sources
            ]
            if is_report
            else [],
        )


def validate(db, user_id, course_id, sources):
    saved = context(sources)
    if not saved:
        return
    from ..repositories.materials import checked_chunk

    if saved.get("version") == 2 and saved.get("automatic_report_sources"):
        scope = saved["evidence_scope"]
        if teacher_emphases(db, user_id, course_id, scope) != saved["teacher_marks"]:
            raise HTTPException(409, "阅读标记已变化，请重新预览报告")
        if confirmed_evidence(db, user_id, course_id, scope) != saved["exam_evidence"]:
            raise HTTPException(409, "真题关联已变化，请重新预览报告")

    for mark in saved["teacher_marks"]:
        checked_chunk(
            db, mark["version_id"], mark["chunk_id"], mark["quote"], user_id, course_id
        )
    if (
        selected_notes(db, user_id, course_id, [n["id"] for n in saved["notes"]])
        != saved["notes"]
    ):
        raise HTTPException(409, "补充笔记已修改，请重新预览并确认")
    if saved.get("exam_paper_ids"):
        scope = sources
        if "version_id" not in sources[0]:
            scope = [
                dict(
                    version_id=c["version_id"], source_id=c["chunk_id"], text=c["quote"]
                )
                for e in saved["exam_evidence"]
                for c in e["citations"]
            ]
        current = confirmed_evidence(
            db, user_id, course_id, scope, saved["exam_paper_ids"]
        )
        if any(e not in current for e in saved["exam_evidence"]):
            raise HTTPException(409, "真题依据或知识点映射已变化，请重新预览")


def model_notes(sources):
    # No note content is treated as an original excerpt/Citation.
    return context(sources).get("notes", [])


def note_chars(sources):
    return (
        len(json.dumps(model_notes(sources), ensure_ascii=False))
        if model_notes(sources)
        else 0
    )


def overlaps(citation, version_id, chunk_id, quote):
    return (
        citation["version_id"] == version_id
        and citation["chunk_id"] == chunk_id
        and (quote in citation["quote"] or citation["quote"] in quote)
    )


def apply_labels(report, saved):
    """Called only after strict original-evidence validation. Never trust model origins."""
    for topic in report["topics"]:
        by_kind = {label["kind"]: label for label in topic["labels"]}
        grouped = {}
        for mark in saved.get("teacher_marks", []):
            if any(
                overlaps(c, mark["version_id"], mark["chunk_id"], mark["quote"])
                for c in topic["citations"]
            ):
                grouped.setdefault(mark["kind"], []).append(mark)
        for kind, marks in grouped.items():
            by_kind[kind] = dict(
                kind=kind,
                origin="teacher_mark",
                reason=marks[0]["reason"],
                evidence=marks,
                availability="active",
                notice="教师强调由本人记录确认，平台未向教师独立核实",
            )
        exams = [
            e
            for e in saved.get("exam_evidence", [])
            if any(
                overlaps(c, s["version_id"], s["chunk_id"], s["quote"])
                for c in topic["citations"]
                for s in e["citations"]
            )
        ]
        if exams:
            label = dict(
                kind="exam",
                origin="observed_exam",
                reason="已核验题库中存在与该原文知识点关联的题目；不代表未来必考或高频。",
                evidence=exams,
                availability="active",
                notice="真题身份和知识点关联依据用户提供并确认的题库记录",
            )
            # Preserve both independently supported origins for the same kind.
            if by_kind.get("exam", {}).get("origin") == "teacher_mark":
                topic["labels"] = list(by_kind.values()) + [label]
                continue
            by_kind["exam"] = label
        topic["labels"] = list(by_kind.values())


def attach_output(body, sources):
    if context(sources):
        body[KEY] = context(sources)
        body["supplement_notice"] = (
            "个人笔记是本人核对的补充资料，不等同课件原文或教师确认；引用仍仅核对实际发送课件。"
        )
