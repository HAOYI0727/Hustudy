"""Read-only complete bounded material snapshots; never silently take a prefix."""

import hashlib
from fastapi import HTTPException
from sqlalchemy import select
from ..models import Document, DocumentChunk, DocumentVersion
from ..repositories.materials import active_version, indexable_source
from .courses import owned_course


def full_context(
    db,
    user_id,
    course_id,
    version_ids,
    chunk_ids=(),
    *,
    max_chars=240000,
    max_chunks=400,
):
    owned_course(db, user_id, course_id)
    selected_ids = set(chunk_ids)
    found, sources, versions, chars, count, warnings = set(), [], [], 0, 0, []
    for version_id in dict.fromkeys(version_ids):
        version = active_version(db, version_id, user_id, course_id)
        document = db.get(Document, version.document_id)
        rows = db.scalars(
            select(DocumentChunk)
            .join(DocumentVersion, DocumentVersion.id == DocumentChunk.version_id)
            .where(
                DocumentChunk.version_id == version.id,
                DocumentChunk.user_id == user_id,
                indexable_source(),
            )
            .order_by(DocumentChunk.ordinal, DocumentChunk.id)
        )
        total = total_chars = included = sent = 0
        for chunk in rows:
            if not chunk.text.strip():
                continue
            total += 1
            total_chars += len(chunk.text)
            if selected_ids and chunk.id not in selected_ids:
                continue
            found.add(chunk.id)
            included += 1
            count += 1
            chars += len(chunk.text)
            sent += len(chunk.text)
            if chars > max_chars or count > max_chunks:
                raise HTTPException(
                    422,
                    f"本次范围超过{max_chunks}段或{max_chars}字符，请按章节减少所选资料；没有发送或截断正文",
                )
            for start in range(0, len(chunk.text), 2000):
                content = chunk.text[start : start + 2000]
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
                        "chunk_start": start,
                        "sha256": hashlib.sha256(content.encode()).hexdigest(),
                    }
                )
        versions.append(
            {
                "version_id": version.id,
                "document_name": document.name,
                "total_chunks": total,
                "selected_chunks": included,
                "total_chars": total_chars,
                "sent_chars": sent,
                "truncated": sent < total_chars,
            }
        )
        if not total:
            warnings.append(
                f"{document.name}：没有就绪的可提取正文，请检查解析状态；扫描图片或公式可能需要人工补录。"
            )
    if selected_ids and found != selected_ids:
        raise HTTPException(404, "片段不存在、未就绪或超出所选资料范围")
    return sources, {
        "versions": versions,
        "warnings": warnings,
        "truncated": any(v["truncated"] for v in versions),
        "notice": "仅分析预览中列出的可提取正文；图片、扫描文字和复杂公式不保证完整。",
    }


def report_batches(sources):
    batches, batch, chars = [], [], 0
    for source in sources:
        if batch and (chars + len(source["text"]) > 8000 or len(batch) >= 32):
            batches.append(batch)
            batch, chars = [], 0
        batch.append(source)
        chars += len(source["text"])
    if batch:
        batches.append(batch)
    return batches
