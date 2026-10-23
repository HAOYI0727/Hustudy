"""M3 metadata bridge: shared evidence and exact tags are distinct relations."""

from sqlalchemy import select, or_, and_
from ..models import Note, Citation
from .note_filters import tag_matches


def related_notes(db, user_id, course_id, sources, terms):
    common = (
        Note.user_id == user_id,
        Note.course_id == course_id,
        Note.deleted.is_(False),
    )
    evidence = [
        and_(Citation.version_id == s["version_id"], Citation.chunk_id == s["chunk_id"])
        for s in sources
        if s["availability"] == "active"
    ]
    columns = (Note.id, Note.title, Note.updated_at)
    shared = []
    if evidence:
        ids = select(Citation.note_id).where(
            Citation.user_id == user_id,
            Citation.availability == "active",
            or_(*evidence),
        )
        shared = db.execute(
            select(*columns)
            .where(*common, Note.id.in_(ids))
            .order_by(Note.updated_at.desc(), Note.id)
            .limit(6)
        ).all()
    tagged = db.execute(
        select(*columns)
        .where(
            *common,
            Note.id.not_in([n.id for n in shared]),
            or_(*(tag_matches(term) for term in terms)),
        )
        .order_by(Note.updated_at.desc(), Note.id)
        .limit(6)
    ).all()
    return [dict(n._mapping, relation="shared_source") for n in shared] + [
        dict(n._mapping, relation="same_tag_candidate") for n in tagged
    ]
