"""M1 bounded, read-only source interface for M2; no model or note access."""

import hashlib
import json
from fastapi import HTTPException
from sqlalchemy import select, text, func
from ..models import Document, DocumentVersion, DocumentChunk
from ..repositories.materials import active_version, indexable_source
from .courses import owned_course
from .search import tokenize


def select_report_context(db, user_id, course_id, version_ids, chunk_ids=None):
    """Read-only M1 interface: deterministic bounded material, no keyword guessing."""
    owned_course(db, user_id, course_id)
    if chunk_ids:
        valid = set(
            db.scalars(
                select(DocumentChunk.id)
                .join(DocumentVersion)
                .where(
                    DocumentChunk.id.in_(chunk_ids),
                    DocumentChunk.version_id.in_(version_ids),
                    DocumentChunk.user_id == user_id,
                    DocumentVersion.user_id == user_id,
                    indexable_source(),
                )
            )
        )
        if valid != set(chunk_ids):
            raise HTTPException(404, "片段不存在、未就绪或超出所选版本范围")
    sources, coverage, budget = [], [], 8000
    for version_id in dict.fromkeys(version_ids):
        version = active_version(db, version_id, user_id, course_id)
        document = db.get(Document, version.document_id)
        statement = (
            select(DocumentChunk)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .where(
                DocumentChunk.version_id == version_id,
                DocumentChunk.user_id == user_id,
                indexable_source(),
                func.length(func.trim(DocumentChunk.text)) > 0,
            )
        )
        total, characters = db.execute(
            statement.with_only_columns(
                func.count(),
                func.coalesce(func.sum(func.length(DocumentChunk.text)), 0),
            )
        ).one()
        selected, sent = 0, 0
        if chunk_ids:
            statement = statement.where(DocumentChunk.id.in_(chunk_ids))
        for chunk in db.scalars(
            statement.order_by(DocumentChunk.ordinal, DocumentChunk.id).limit(
                max(0, 6 - len(sources))
            )
        ):
            content = chunk.text[: min(2000, budget)]
            if not content.strip():
                continue
            sources.append(
                {
                    "source_id": chunk.id,
                    "version_id": version.id,
                    "document_id": document.id,
                    "document_name": document.name,
                    "version_no": version.version_no,
                    "locator": {
                        "type": chunk.locator_type,
                        "value": chunk.locator_value,
                    },
                    "source_kind": chunk.source_kind,
                    "text": content,
                    "sha256": hashlib.sha256(content.encode()).hexdigest(),
                }
            )
            budget -= len(content)
            selected += 1
            sent += len(content)
            if budget <= 0:
                break
        coverage.append(
            {
                "version_id": version_id,
                "document_name": document.name,
                "total_chunks": total,
                "selected_chunks": selected,
                "total_chars": characters,
                "sent_chars": sent,
                "truncated": sent < characters,
            }
        )
    return sources, {
        "versions": coverage,
        "truncated": any(item["truncated"] for item in coverage),
        "notice": "仅依据下方实际发送片段；不保证覆盖整章或整份课程。",
    }


def validate_context(db, user_id, course_id, sources):
    owned_course(db, user_id, course_id)
    for source in sources:
        active_version(db, source["version_id"], user_id, course_id)
        chunk = db.scalar(
            select(DocumentChunk)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .where(
                DocumentChunk.id == source["source_id"],
                DocumentChunk.version_id == source["version_id"],
                DocumentChunk.user_id == user_id,
                DocumentVersion.user_id == user_id,
                indexable_source(),
            )
        )
        if (
            not chunk
            or source["text"] not in chunk.text
            or (
                "chunk_start" in source
                and chunk.text[
                    source["chunk_start"] : source["chunk_start"] + len(source["text"])
                ]
                != source["text"]
            )
            or hashlib.sha256(source["text"].encode()).hexdigest() != source["sha256"]
        ):
            raise HTTPException(409, "来源已变化或不再有效，请重新预览")


def select_context(db, user_id, course_id, query, version_ids, chunk_ids):
    owned_course(db, user_id, course_id)
    for version_id in version_ids:
        active_version(db, version_id, user_id, course_id)
    if chunk_ids:
        rows = db.execute(
            select(DocumentChunk, DocumentVersion, Document)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                DocumentChunk.id.in_(chunk_ids),
                DocumentChunk.user_id == user_id,
                DocumentVersion.user_id == user_id,
                Document.user_id == user_id,
                Document.course_id == course_id,
                Document.deleted_at.is_(None),
                indexable_source(),
            )
        ).all()
        if len(rows) != len(set(chunk_ids)) or (
            version_ids and any(v.id not in version_ids for _, v, _ in rows)
        ):
            raise HTTPException(404, "选中片段不存在、未就绪或超出版本范围")
        records = [
            {
                "source_id": c.id,
                "version_id": v.id,
                "document_id": d.id,
                "document_name": d.name,
                "version_no": v.version_no,
                "locator": {"type": c.locator_type, "value": c.locator_value},
                "source_kind": c.source_kind,
                "text": c.text[:2000],
            }
            for c, v, d in rows
        ]
    else:
        terms = list(dict.fromkeys(tokenize(query)))[:60]
        if not terms:
            return []
        match = " OR ".join('"' + term + '"' for term in terms)
        records = [
            dict(row)
            for row in db.execute(
                text("""SELECT c.id AS source_id,c.version_id,d.id AS document_id,
            d.name AS document_name,v.version_no,c.locator_type,c.locator_value,c.source_kind,substr(c.text,1,2000) AS text
            FROM chunk_search JOIN document_chunks c ON c.id=chunk_search.chunk_id
            JOIN document_versions v ON v.id=c.version_id JOIN documents d ON d.id=v.document_id
            WHERE chunk_search MATCH :q AND c.user_id=:u AND v.user_id=:u AND d.user_id=:u
            AND d.course_id=:course AND d.deleted_at IS NULL
            AND ((c.source_kind='extracted' AND v.parse_status='SUCCEEDED' AND v.index_status='SUCCEEDED')
                OR (c.source_kind='manual_transcript' AND EXISTS (SELECT 1 FROM manual_transcripts mt WHERE mt.chunk_id=c.id AND mt.user_id=:u AND mt.status='CONFIRMED')))
            AND (:scoped=0 OR v.id IN (SELECT value FROM json_each(:versions)))
            AND (:scoped=1 OR v.version_no=(SELECT MAX(v2.version_no) FROM document_versions v2 WHERE v2.document_id=d.id))
            ORDER BY bm25(chunk_search),c.id LIMIT 6"""),
                {
                    "q": match,
                    "u": user_id,
                    "course": course_id,
                    "scoped": int(bool(version_ids)),
                    "versions": json.dumps(version_ids),
                },
            ).mappings()
        ]
        for row in records:
            row["locator"] = {
                "type": row.pop("locator_type"),
                "value": row.pop("locator_value"),
            }
    budget, result = 8000, []
    for row in records:
        row["text"] = row["text"][:budget]
        if not row["text"].strip():
            continue
        budget -= len(row["text"])
        row["sha256"] = hashlib.sha256(row["text"].encode()).hexdigest()
        result.append(row)
        if budget <= 0:
            break
    return result
