"""Shared read orchestrator: module adapters own their tables and semantics."""

from ..core.database import begin_read_snapshot
from ..models.base import utc_now
from .courses import owned_course
from . import material_workspace, note_workspace, study_workspace, exam_workspace
from sqlalchemy import select, func, union_all

ADAPTERS = {
    "materials": material_workspace.summary,
    "notes": note_workspace.summary,
    "study": study_workspace.summary,
    "practice": exam_workspace.summary,
}
RECORD_KINDS = ("material", "note", "qa", "report", "attempt", "mistake")


def records(db, user, course_id, kind, q, offset, limit):
    begin_read_snapshot(db)
    owned_course(db, user.id, course_id)
    rows = union_all(
        material_workspace.records(user.id, course_id),
        note_workspace.records(user.id, course_id),
        study_workspace.records(user.id, course_id),
        *exam_workspace.records(user.id, course_id),
    ).subquery()
    matched = select(rows)
    if q.strip():
        # Literal substring search: %, _ and SQL-looking text are ordinary text.
        matched = matched.where(func.instr(func.lower(rows.c.title), q.strip().lower()) > 0)
    matched = matched.subquery()
    counts = dict.fromkeys(RECORD_KINDS, 0)
    counts.update(dict(db.execute(
        select(matched.c.kind, func.count()).group_by(matched.c.kind)
    ).all()))
    selected = select(matched)
    if kind != "all":
        selected = selected.where(matched.c.kind == kind)
    items = db.execute(selected.order_by(
        matched.c.updated_at.desc(), matched.c.kind, matched.c.id,
    ).offset(offset).limit(limit)).mappings().all()
    return {
        "course_id": course_id, "items": items,
        "total": sum(counts.values()) if kind == "all" else counts[kind],
        "counts": counts, "offset": offset, "limit": limit, "checked_at": utc_now(),
    }


def section(db, user, course_id, domain):
    begin_read_snapshot(db)
    owned_course(db, user.id, course_id)
    return {
        "course_id": course_id,
        "domain": domain,
        "checked_at": utc_now(),
        **ADAPTERS[domain](db, user, course_id),
    }
