"""M1-authorized topic evidence and bounded keyword candidates."""

import json
from fastapi import HTTPException
from sqlalchemy import select, func
from ..models import Document, DocumentVersion, PastPaper
from ..repositories.materials import checked_chunk
from .search import search_chunks


def evidence(db, user_id, course_id, row):
    sources = []
    for citation in json.loads(row.sources_json).get("citations", [])[:20]:
        item = dict(
            version_id=citation.get("version_id"),
            chunk_id=citation.get("chunk_id"),
            availability="unavailable",
        )
        try:
            chunk = checked_chunk(
                db,
                item["version_id"],
                item["chunk_id"],
                citation.get("quote", ""),
                user_id,
                course_id,
                lock_course=False,
            )
            version = db.get(DocumentVersion, chunk.version_id)
            doc = db.get(Document, version.document_id)
            item.update(
                availability="active",
                document_id=doc.id,
                title=doc.name,
                version_no=version.version_no,
                locator=chunk.locator_value,
                quote=citation["quote"],
            )
        except HTTPException:
            pass
        sources.append(item)
    return sources


def candidates(db, user_id, course_id, sources, terms):
    excluded = set(
        db.scalars(
            select(func.json_extract(PastPaper.bank_meta_json, "$.version_id")).where(
                PastPaper.user_id == user_id, PastPaper.course_id == course_id
            )
        )
    )
    seen = {s["chunk_id"] for s in sources}
    items = []
    for term in terms[:3]:
        for match in search_chunks(db, user_id, course_id, term[:40], latest_only=True):
            if match["chunk_id"] in seen or match["version_id"] in excluded:
                continue
            seen.add(match["chunk_id"])
            items.append(
                dict(
                    document_id=match["document_id"],
                    version_id=match["version_id"],
                    chunk_id=match["chunk_id"],
                    title=match["document_name"],
                    version_no=match["version_no"],
                    locator=match["locator_value"],
                    quote=match["text"][:300],
                )
            )
            if len(items) == 6:
                return items
    return items
