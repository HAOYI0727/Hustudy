"""Shared read orchestration for one authorized M1 version or chunk."""

from fastapi import HTTPException
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, union_all
from ..core.database import begin_read_snapshot
from ..models import Document, DocumentChunk
from ..models.base import utc_now
from ..repositories.materials import active_version
from . import note_workspace, study_workspace, topic_learning, exam_source_learning

KINDS = ("note", "qa", "report", "topic", "mistake")


def links(db, user, version_id, chunk_id, kind, q, offset, limit):
    user_id = user.id
    begin_read_snapshot(db)
    version = active_version(db, version_id, user_id)
    document = db.get(Document, version.document_id)
    if document.library_scope != "material":
        raise HTTPException(404, "资料版本不存在或不可访问")
    if chunk_id is not None and not db.scalar(
        select(DocumentChunk.id).where(
            DocumentChunk.id == chunk_id,
            DocumentChunk.version_id == version_id,
            DocumentChunk.user_id == user_id,
        )
    ):
        raise HTTPException(404, "原文片段不存在或不属于当前版本")
    rows = union_all(
        *(
            adapter.linked_records(user_id, document.course_id, version_id, chunk_id)
            for adapter in (
                note_workspace,
                study_workspace,
                topic_learning,
                exam_source_learning,
            )
        )
    ).subquery()
    query = select(rows)
    if q.strip():
        query = query.where(func.instr(func.lower(rows.c.title), q.strip().lower()) > 0)
    matched = query.subquery()
    counts = dict.fromkeys(KINDS, 0)
    counts.update(
        dict(
            db.execute(
                select(matched.c.kind, func.count()).group_by(matched.c.kind)
            ).all()
        )
    )
    selected = select(matched)
    if kind != "all":
        selected = selected.where(matched.c.kind == kind)
    items = (
        db.execute(
            selected.order_by(
                matched.c.updated_at.desc(),
                matched.c.kind,
                matched.c.id,
            )
            .offset(offset)
            .limit(limit)
        )
        .mappings()
        .all()
    )
    today = datetime.now(ZoneInfo(user.timezone)).date().isoformat()
    return dict(
        course_id=document.course_id,
        document_id=document.id,
        version_id=version_id,
        chunk_id=chunk_id,
        items=exam_source_learning.enrich(
            db, user_id, version_id, chunk_id, items, today
        ),
        today=today,
        timezone=user.timezone,
        counts=counts,
        total=sum(counts.values()) if kind == "all" else counts[kind],
        offset=offset,
        limit=limit,
        checked_at=utc_now(),
    )
