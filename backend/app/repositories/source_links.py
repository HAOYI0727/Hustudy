"""SQL equivalents of the existing checked_chunk boundary for read-only links."""

from sqlalchemy import select, func, and_, or_, case
from ..models import DocumentChunk, ManualTranscript

# Python str.strip whitespace, including ideographic spaces in historical excerpts.
STRIP_CHARS = "\t\n\v\f\r \x1c\x1d\x1e\x1f\x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"


def valid_reference(user_id, version_id, identity, quote, chunk_id=None):
    manual = (
        select(ManualTranscript.id)
        .where(
            ManualTranscript.chunk_id == DocumentChunk.id,
            ManualTranscript.user_id == user_id,
            ManualTranscript.status.in_(["CONFIRMED", "SUPERSEDED"]),
        )
        .exists()
    )
    query = select(DocumentChunk.id).where(
        DocumentChunk.id == identity,
        DocumentChunk.version_id == version_id,
        DocumentChunk.user_id == user_id,
        func.length(func.trim(quote, STRIP_CHARS)) > 0,
        func.instr(DocumentChunk.text, quote) > 0,
        or_(DocumentChunk.source_kind != "manual_transcript", manual),
    )
    if chunk_id is not None:
        query = query.where(DocumentChunk.id == chunk_id)
    return query.correlate_except(DocumentChunk).exists()


def json_references(column, user_id, version_id, chunk_id=None):
    # Ignore unsupported historical shapes rather than guessing nested citations.
    root = case((func.json_valid(column), column), else_="{}")
    citations = case(
        (
            func.json_type(root, "$.citations") == "array",
            func.json_extract(root, "$.citations"),
        ),
        else_="[]",
    )
    entries = func.json_each(citations).table_valued("value", "type").alias()
    entry = case((entries.c.type == "object", entries.c.value), else_="{}")
    return (
        select(1)
        .select_from(entries)
        .where(
            and_(
                func.json_extract(entry, "$.version_id") == version_id,
                func.json_type(entry, "$.quote") == "text",
                valid_reference(
                    user_id,
                    version_id,
                    func.json_extract(entry, "$.chunk_id"),
                    func.json_extract(entry, "$.quote"),
                    chunk_id,
                ),
            )
        )
        .exists()
    )
