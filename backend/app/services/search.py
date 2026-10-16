
"""Versioned Chinese character/bigram tokenization, separate from source offsets."""

import re
import json
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..core.database import begin_read_snapshot

TOKENIZER_VERSION = "zh-bigram-v1"


def tokenize(value: str) -> list[str]:
    tokens = []
    for match in re.finditer(r"[\u3400-\u9fff]+|[a-zA-Z0-9_]+", value.lower()):
        part = match.group()
        if "\u3400" <= part[0] <= "\u9fff":
            tokens.extend(part)
            tokens.extend(part[i : i + 2] for i in range(len(part) - 1))
        else:
            tokens.append(part)
    return tokens


def index_version(db: Session, version_id: str) -> None:
    db.execute(
        text(
            "DELETE FROM chunk_search WHERE chunk_id IN (SELECT id FROM document_chunks WHERE version_id=:v)"
        ),
        {"v": version_id},
    )
    rows = db.execute(
        text("SELECT id, text, locator_value FROM document_chunks WHERE version_id=:v"),
        {"v": version_id},
    ).all()
    for chunk_id, body, locator in rows:
        db.execute(
            text("INSERT INTO chunk_search(chunk_id,tokens) VALUES (:id,:tokens)"),
            {"id": chunk_id, "tokens": " ".join(tokenize(locator + "\n" + body))},
        )


_SEARCH_FROM = """FROM chunk_search JOIN document_chunks c ON c.id=chunk_search.chunk_id
JOIN document_versions v ON v.id=c.version_id JOIN documents d ON d.id=v.document_id
LEFT JOIN manual_transcripts mt ON mt.chunk_id=c.id AND mt.user_id=c.user_id
WHERE chunk_search MATCH :match AND c.user_id=:user AND d.user_id=:user AND v.user_id=:user
  AND d.course_id=:course AND d.deleted_at IS NULL
  AND ((c.source_kind='extracted' AND v.parse_status='SUCCEEDED' AND v.index_status='SUCCEEDED')
       OR (c.source_kind='manual_transcript' AND mt.status='CONFIRMED'))
  AND (:category IS NULL OR d.category=:category)
  AND (:tag IS NULL OR EXISTS (SELECT 1 FROM json_each(d.tags) WHERE value=:tag))
  AND (:latest=0 OR v.version_no=(SELECT MAX(v2.version_no) FROM document_versions v2 WHERE v2.document_id=d.id))"""


def _parameters(user_id, course_id, query, category, tag, latest_only):
    from fastapi import HTTPException

    terms = list(dict.fromkeys(tokenize(query)))
    if len(terms) > 100:
        raise HTTPException(422, "关键词过长，请缩短查询（最多100个检索词）")
    return {
        "match": " AND ".join('"' + term + '"' for term in terms),
        "user": user_id,
        "course": course_id,
        "category": category.strip() if category is not None else None,
        "tag": tag.strip() if tag is not None else None,
        "latest": int(latest_only),
    }


def _rows(db, parameters, offset, limit):
    rows = (
        db.execute(
            text(
                """SELECT c.id AS chunk_id, c.version_id, d.id AS document_id,
      d.name AS document_name, d.category, d.tags, v.version_no, c.locator_type,
      c.locator_value, c.text, c.source_kind, mt.id AS transcript_id,
      -bm25(chunk_search) AS score """
                + _SEARCH_FROM
                + " ORDER BY bm25(chunk_search), c.id LIMIT :limit OFFSET :offset"
            ),
            {**parameters, "limit": limit, "offset": offset},
        )
        .mappings()
        .all()
    )
    return [{**row, "tags": json.loads(row["tags"])} for row in rows]


def search_chunks(
    db: Session,
    user_id: str,
    course_id: str,
    query: str,
    *,
    category: str | None = None,
    tag: str | None = None,
    latest_only: bool = False,
):
    """Existing bounded interface, retained for API consumers."""
    parameters = _parameters(user_id, course_id, query, category, tag, latest_only)
    return _rows(db, parameters, 0, 50) if parameters["match"] else []


def search_page(
    db: Session,
    user_id: str,
    course_id: str,
    query: str,
    *,
    category: str | None = None,
    tag: str | None = None,
    latest_only: bool = False,
    offset: int = 0,
    limit: int = 12,
):
    from ..core.search_excerpt import excerpt

    begin_read_snapshot(db)

    parameters = _parameters(user_id, course_id, query, category, tag, latest_only)
    total = (
        db.scalar(text("SELECT COUNT(*) " + _SEARCH_FROM), parameters)
        if parameters["match"]
        else 0
    )
    rows = _rows(db, parameters, offset, limit) if total else []
    for row in rows:
        row["excerpt"] = excerpt(row.pop("text"), query)
    return {"items": rows, "total": total, "offset": offset, "limit": limit}
