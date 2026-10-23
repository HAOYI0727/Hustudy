"""A common projection only; each module supplies its own ownership predicates."""

from sqlalchemy import String, literal, select


def metadata_query(identity, title, kind, status, updated_at, document=None, version=None):
    return select(
        identity.label("id"),
        title.label("title"),
        (literal(kind) if isinstance(kind, str) else kind).label("kind"),
        (literal(status) if isinstance(status, str) else status).label("status"),
        updated_at.label("updated_at"),
        (document if document is not None else literal(None, String(36))).label(
            "document_id"
        ),
        (version if version is not None else literal(None, String(36))).label(
            "version_id"
        ),
    )
