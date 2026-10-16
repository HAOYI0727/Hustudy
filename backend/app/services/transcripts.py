"""M1 manual source workflow. Only explicit confirmation creates a source chunk."""

import hashlib
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from ..models import (
    Citation,
    Document,
    DocumentChunk,
    DocumentVersion,
    ManualTranscript,
)
from ..models.base import utc_now
from ..repositories.materials import active_version
from .assets import preview_source
from .search import tokenize


def owned_transcript(db, transcript_id, user_id):
    row = db.scalar(
        select(ManualTranscript).where(
            ManualTranscript.id == transcript_id, ManualTranscript.user_id == user_id
        )
    )
    if not row:
        raise HTTPException(404, "补录记录不存在")
    active_version(db, row.version_id, user_id)
    return row


def check_page(db, version_id, user_id, page):
    version = active_version(db, version_id, user_id)
    if Path(version.original_filename).suffix.lower() != ".pdf":
        raise HTTPException(422, "人工页补录目前只支持原始 PDF")
    document = db.get(Document, version.document_id)
    preview_source(db, user_id, document.course_id, version_id, page)
    return version


def conflict(db, transcript_id, user_id):
    row = owned_transcript(db, transcript_id, user_id)
    raise HTTPException(
        409,
        {
            "message": "补录已被更新或确认，请保留本地文字并核对服务器记录",
            "server_text": row.text,
            "server_revision": row.revision,
            "server_status": row.status,
        },
    )


def check_budget(db, version_id, body, exclude_id=None):
    statement = select(
        func.count(), func.coalesce(func.sum(func.length(ManualTranscript.text)), 0)
    ).where(ManualTranscript.version_id == version_id)
    if exclude_id:
        statement = statement.where(ManualTranscript.id != exclude_id)
    count, length = db.execute(statement).one()
    if (not exclude_id and count >= 500) or length + len(body) > 2_000_000:
        raise HTTPException(422, "本版本补录超过 500 条或 200 万字预算")


def create_draft(db, user_id, version_id, payload):
    version = active_version(db, version_id, user_id)
    # Serialize per-version writes before checking page history and budgets.
    db.execute(
        update(DocumentVersion)
        .where(DocumentVersion.id == version.id)
        .values(updated_at=version.updated_at)
    )
    db.expire_all()
    check_page(db, version_id, user_id, payload.page)
    if payload.supersedes_id:
        parent = owned_transcript(db, payload.supersedes_id, user_id)
        if (
            parent.version_id != version_id
            or parent.page != payload.page
            or parent.status != "CONFIRMED"
        ):
            raise HTTPException(409, "修订必须指向同版本、同页的当前确认补录")
    elif db.scalar(
        select(ManualTranscript.id).where(
            ManualTranscript.version_id == version_id,
            ManualTranscript.page == payload.page,
            ManualTranscript.status == "CONFIRMED",
        )
    ):
        raise HTTPException(409, "这一页已有确认补录，请从当前记录创建修订")
    check_budget(db, version_id, payload.text)
    row = ManualTranscript(
        user_id=user_id,
        version_id=version_id,
        page=payload.page,
        text=payload.text,
        text_hash=hashlib.sha256(payload.text.encode()).hexdigest(),
        supersedes_id=payload.supersedes_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_draft(db, user_id, transcript_id, payload):
    row = owned_transcript(db, transcript_id, user_id)
    claimed = db.execute(
        update(ManualTranscript)
        .where(
            ManualTranscript.id == row.id,
            ManualTranscript.user_id == user_id,
            ManualTranscript.status == "DRAFT",
            ManualTranscript.revision == payload.revision,
        )
        .values(
            text=payload.text,
            text_hash=hashlib.sha256(payload.text.encode()).hexdigest(),
            revision=ManualTranscript.revision + 1,
        )
    )
    if claimed.rowcount != 1:
        db.rollback()
        conflict(db, transcript_id, user_id)
    db.expire_all()
    check_budget(db, row.version_id, payload.text, transcript_id)
    db.commit()
    db.refresh(row)
    return row


def confirm_draft(db, user_id, transcript_id, revision):
    row = owned_transcript(db, transcript_id, user_id)
    claimed = db.execute(
        update(ManualTranscript)
        .where(
            ManualTranscript.id == row.id,
            ManualTranscript.user_id == user_id,
            ManualTranscript.status == "DRAFT",
            ManualTranscript.revision == revision,
        )
        .values(revision=ManualTranscript.revision + 1)
    )
    if claimed.rowcount != 1:
        db.rollback()
        row = owned_transcript(db, transcript_id, user_id)
        if row.status in ("CONFIRMED", "SUPERSEDED") and row.revision == revision + 1:
            return row  # A retry returns the same immutable confirmation/chunk.
        conflict(db, transcript_id, user_id)
    db.expire_all()
    check_page(db, row.version_id, user_id, row.page)
    if row.supersedes_id:
        replaced = db.execute(
            update(ManualTranscript)
            .where(
                ManualTranscript.id == row.supersedes_id,
                ManualTranscript.user_id == user_id,
                ManualTranscript.version_id == row.version_id,
                ManualTranscript.page == row.page,
                ManualTranscript.status == "CONFIRMED",
            )
            .values(status="SUPERSEDED", revision=ManualTranscript.revision + 1)
        )
        if replaced.rowcount != 1:
            db.rollback()
            raise HTTPException(
                409, "本页确认记录已变化，当前草稿保留，请重新核对修订来源"
            )
    elif db.scalar(
        select(ManualTranscript.id).where(
            ManualTranscript.version_id == row.version_id,
            ManualTranscript.page == row.page,
            ManualTranscript.status == "CONFIRMED",
        )
    ):
        db.rollback()
        raise HTTPException(409, "本页已有其他确认补录，当前草稿保留")
    chunk = DocumentChunk(
        user_id=user_id,
        version_id=row.version_id,
        ordinal=1_000_000 + row.page,
        locator_type="page",
        locator_value=str(row.page),
        text=row.text,
        start_offset=0,
        end_offset=len(row.text),
        source_kind="manual_transcript",
    )
    db.add(chunk)
    db.flush()
    row.status, row.chunk_id, row.confirmed_by, row.confirmed_at = (
        "CONFIRMED",
        chunk.id,
        user_id,
        utc_now(),
    )
    db.execute(
        text("INSERT INTO chunk_search(chunk_id,tokens) VALUES (:id,:tokens)"),
        {"id": chunk.id, "tokens": " ".join(tokenize(str(row.page) + "\n" + row.text))},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "本页确认发生冲突，草稿保留") from exc
    db.refresh(row)
    return row


def withdraw(db, user_id, transcript_id, revision):
    row = owned_transcript(db, transcript_id, user_id)
    result = db.execute(
        update(ManualTranscript)
        .where(
            ManualTranscript.id == row.id,
            ManualTranscript.user_id == user_id,
            ManualTranscript.revision == revision,
            ManualTranscript.status != "WITHDRAWN",
        )
        .values(status="WITHDRAWN", revision=ManualTranscript.revision + 1)
    )
    if result.rowcount != 1:
        db.rollback()
        conflict(db, transcript_id, user_id)
    if row.chunk_id:
        from .ai_retirement import cancel_source_queries

        cancel_source_queries(db, user_id, chunk_id=row.chunk_id)
        db.execute(
            update(Citation)
            .where(Citation.chunk_id == row.chunk_id, Citation.user_id == user_id)
            .values(availability="unavailable")
        )
        db.execute(
            text("DELETE FROM chunk_search WHERE chunk_id=:id"), {"id": row.chunk_id}
        )
    db.commit()
    db.refresh(row)
    return row
