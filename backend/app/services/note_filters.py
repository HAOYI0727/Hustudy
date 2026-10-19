"""Shared predicates for the M3 list and paginated discovery adapter."""

from sqlalchemy import func, or_, select

from ..models import Note


def tag_matches(value: str, *, exact: bool = True):
    tags = func.json_each(Note.tags).table_valued("key", "value")
    predicate = (
        tags.c.value == value
        if exact
        else tags.c.value.icontains(value, autoescape=True)
    )
    return select(1).select_from(tags).where(predicate).correlate(Note).exists()


def text_matches(query: str):
    return or_(
        Note.title.icontains(query, autoescape=True),
        Note.content.icontains(query, autoescape=True),
        tag_matches(query, exact=False),
    )
