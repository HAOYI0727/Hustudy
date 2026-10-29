"""Read-only course graph; no body loading or inference from unsaved drafts."""

from fastapi import HTTPException
from sqlalchemy import case, func, or_, select, union

from ..core.database import begin_read_snapshot
from ..models import Note, NoteLink
from .courses import owned_course
from .note_catalog import columns

EDGE_LIMIT = 400


def note_graph(db, user_id, course_id, query, link_state, focus_note_id, limit):
    begin_read_snapshot(db)
    owned_course(db, user_id, course_id)
    query = query.strip()
    if focus_note_id and (query or link_state != "all"):
        raise HTTPException(422, "聚焦笔记时请清空标题和关联状态筛选")

    notes = (
        select(*columns())
        .where(
            Note.user_id == user_id,
            Note.course_id == course_id,
            Note.deleted.is_(False),
        )
        .cte("graph_notes")
    )
    note_ids = select(notes.c.id)
    # Legacy links can be repeated, self-referential, or point at a deleted note.
    # Check both endpoints before counting; never use stale link labels as titles.
    links = (
        select(
            NoteLink.source_note_id.label("source_id"),
            NoteLink.target_note_id.label("target_id"),
        )
        .where(
            NoteLink.user_id == user_id,
            NoteLink.source_note_id != NoteLink.target_note_id,
            NoteLink.source_note_id.in_(note_ids),
            NoteLink.target_note_id.in_(note_ids),
        )
        .distinct()
        .cte("graph_links")
    )
    incoming = (
        select(links.c.target_id, func.count().label("count"))
        .group_by(links.c.target_id)
        .cte("graph_incoming")
    )
    outgoing = (
        select(links.c.source_id, func.count().label("count"))
        .group_by(links.c.source_id)
        .cte("graph_outgoing")
    )
    incoming_count = func.coalesce(incoming.c.count, 0)
    outgoing_count = func.coalesce(outgoing.c.count, 0)
    scope = (
        select(
            notes,
            incoming_count.label("incoming_count"),
            outgoing_count.label("outgoing_count"),
        )
        .outerjoin(incoming, incoming.c.target_id == notes.c.id)
        .outerjoin(outgoing, outgoing.c.source_id == notes.c.id)
    )
    if focus_note_id:
        if not db.scalar(select(notes.c.id).where(notes.c.id == focus_note_id)):
            raise HTTPException(404, "笔记不存在")
        neighbors = union(
            select(links.c.source_id).where(links.c.target_id == focus_note_id),
            select(links.c.target_id).where(links.c.source_id == focus_note_id),
        )
        scope = scope.where(or_(notes.c.id == focus_note_id, notes.c.id.in_(neighbors)))
    else:
        if query:
            scope = scope.where(notes.c.title.icontains(query, autoescape=True))
        if link_state == "linked":
            scope = scope.where(incoming_count + outgoing_count > 0)
        elif link_state == "isolated":
            scope = scope.where(incoming_count + outgoing_count == 0)
    scope = scope.cte("graph_scope")
    scope_ids = select(scope.c.id)
    total_nodes = db.scalar(select(func.count()).select_from(scope)) or 0
    total_edges = (
        db.scalar(
            select(func.count())
            .select_from(links)
            .where(links.c.source_id.in_(scope_ids), links.c.target_id.in_(scope_ids))
        )
        or 0
    )
    order = [scope.c.updated_at.desc(), scope.c.id]
    if focus_note_id:
        order.insert(0, case((scope.c.id == focus_note_id, 0), else_=1))
    nodes = db.execute(select(scope).order_by(*order).limit(limit)).mappings().all()
    shown_ids = [node["id"] for node in nodes]
    edges = (
        db.execute(
            select(links)
            .where(links.c.source_id.in_(shown_ids), links.c.target_id.in_(shown_ids))
            .order_by(links.c.source_id, links.c.target_id)
            .limit(EDGE_LIMIT)
        )
        .mappings()
        .all()
        if shown_ids
        else []
    )
    return {
        "course_id": course_id,
        "focus_note_id": focus_note_id,
        "nodes": nodes,
        "edges": edges,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "node_limit": limit,
        "edge_limit": EDGE_LIMIT,
        "nodes_truncated": total_nodes > len(nodes),
        "edges_truncated": total_edges > len(edges),
    }
