import hashlib
import re
from urllib.parse import quote
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import delete, select, update, func
from sqlalchemy.orm import Session

from ..repositories.materials import checked_chunk
from ..core.database import get_db
from ..dependencies import current_user
from ..models import (
    Asset,
    AssetReference,
    Citation,
    Note,
    NoteLink,
    User,
)
from ..schemas.notes import (
    CitationCreate,
    CitationResponse,
    NoteCreate,
    NoteSearchPage,
    NoteResponse,
    NoteUpdate,
    NoteOptionPage,
    NoteCatalog,
    NoteMetadata,
)

from ..services.courses import owned_course
from ..services.note_export_names import safe_name
from ..services.note_filters import tag_matches, text_matches
from ..services.note_citations import citation_response, lock_note
from ..services.note_folders import check_placement, lock_owner
from ..services.note_trash import retention
from ..models.base import utc_now
from datetime import timedelta

router = APIRouter(prefix="/api/v1", tags=["notes"])
LINK_RE = re.compile(r"\[\[note:([0-9a-fA-F-]{36})(?:\|([^\]]+))?\]\]")
ASSET_RE = re.compile(r"!\[\[asset:([0-9a-fA-F-]{36})(?:\|[^\]]*)?\]\]")


def _note(note_id: str, user: User, db: Session) -> Note:
    note = db.scalar(
        select(Note).where(
            Note.id == note_id, Note.user_id == user.id, Note.deleted.is_(False)
        )
    )
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return note


def _check_course(course_id: str | None, user: User, db: Session) -> None:
    if course_id:
        owned_course(db, user.id, course_id, lock=True)


def _sync_links(note: Note, user: User, db: Session) -> None:
    db.execute(
        delete(NoteLink).where(
            NoteLink.source_note_id == note.id, NoteLink.user_id == user.id
        )
    )
    for target_id, label in LINK_RE.findall(note.content):
        if target_id == note.id:
            continue
        target = db.scalar(
            select(Note).where(Note.id == target_id, Note.user_id == user.id)
        )
        if target:
            db.add(
                NoteLink(
                    user_id=user.id,
                    source_note_id=note.id,
                    target_note_id=target.id,
                    label=label or target.title,
                )
            )

    db.execute(
        delete(AssetReference).where(
            AssetReference.note_id == note.id, AssetReference.user_id == user.id
        )
    )
    for asset_id in set(ASSET_RE.findall(note.content)):
        asset = db.scalar(
            select(Asset).where(
                Asset.id == asset_id, Asset.user_id == user.id, Asset.deleted.is_(False)
            )
        )
        if asset:
            db.add(AssetReference(user_id=user.id, note_id=note.id, asset_id=asset_id))


@router.get("/notes", response_model=List[NoteResponse])
def list_notes(
    course_id: str | None = None,
    q: str = Query(default="", max_length=200),
    tag: str | None = Query(default=None, min_length=1, max_length=32),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> List[NoteResponse]:
    statement = select(Note).where(Note.user_id == user.id, Note.deleted.is_(False))
    if course_id:
        owned_course(db, user.id, course_id)
        statement = statement.where(Note.course_id == course_id)
    if q.strip():
        statement = statement.where(text_matches(q.strip()))
    if tag is not None:
        statement = statement.where(tag_matches(tag.strip()))
    return [
        NoteResponse.model_validate(n, from_attributes=True)
        for n in db.scalars(statement.order_by(Note.updated_at.desc(), Note.id)).all()
    ]


@router.get("/courses/{course_id}/note-search", response_model=NoteSearchPage)
def find_notes(
    course_id: str,
    q: str = Query(max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=12, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.note_search import search_notes

    return search_notes(db, user.id, course_id, q, offset, limit)


@router.get("/notes/catalog", response_model=NoteCatalog)
def note_catalog(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.note_catalog import catalog

    return catalog(db, user.id, offset, limit)


@router.get("/courses/{course_id}/note-matches")
def note_matches(
    course_id: str,
    q: str = Query(default="", max_length=200),
    tag: str = Query(default="", max_length=32),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.note_catalog import matches

    return matches(db, user.id, course_id, q, tag)


@router.get("/notes/{note_id}/backlink-options", response_model=list[NoteMetadata])
def backlink_options(
    note_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.note_catalog import backlinks

    return backlinks(db, user.id, note_id)


@router.get("/courses/{course_id}/note-options", response_model=NoteOptionPage)
def citation_targets(
    course_id: str,
    q: str = Query(default="", max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.note_search import note_options

    return note_options(db, user.id, course_id, q, offset, limit)


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    lock_owner(db, user.id)
    _check_course(payload.course_id, user, db)
    check_placement(db, user.id, payload.folder_id, payload.course_id)
    if payload.request_id:
        db.execute(update(User).where(User.id == user.id).values(id=User.id))
        previous = db.get(Note, str(payload.request_id))
        if previous:
            if previous.user_id != user.id or previous.deleted:
                raise HTTPException(404, "笔记请求标识不可用")
            saved_sources = db.scalars(
                select(Citation).where(
                    Citation.note_id == previous.id, Citation.user_id == user.id
                )
            ).all()
            same_sources = sorted(
                (c.version_id, c.chunk_id, c.quote) for c in saved_sources
            ) == sorted((c.version_id, c.chunk_id, c.quote) for c in payload.citations)
            if (
                previous.revision != 1
                or previous.course_id != payload.course_id
                or previous.title != payload.title
                or previous.content != payload.content
                or previous.tags != payload.tags
                or previous.folder_id != payload.folder_id
                or not same_sources
            ):
                raise HTTPException(
                    409,
                    {
                        "message": "此前创建的笔记已变化，请核对服务端版本",
                        "server_id": previous.id,
                        "server_revision": previous.revision,
                        "server_title": previous.title,
                        "server_content": previous.content,
                        "server_tags": previous.tags,
                        "server_folder_id": previous.folder_id,
                    },
                )
            db.commit()
            return NoteResponse.model_validate(previous, from_attributes=True)
    chunks = [
        checked_chunk(db, c.version_id, c.chunk_id, c.quote, user.id, payload.course_id)
        for c in payload.citations
    ]
    note = Note(
        **({"id": str(payload.request_id)} if payload.request_id else {}),
        user_id=user.id,
        course_id=payload.course_id,
        title=payload.title,
        content=payload.content,
        tags=payload.tags,
        folder_id=payload.folder_id,
    )
    db.add(note)
    db.flush()
    _sync_links(note, user, db)
    for source, chunk in zip(payload.citations, chunks):
        db.add(
            Citation(
                user_id=user.id,
                note_id=note.id,
                version_id=source.version_id,
                chunk_id=chunk.id,
                locator_type=chunk.locator_type,
                locator_value=chunk.locator_value,
                quote=source.quote,
                source_kind=chunk.source_kind,
                quote_hash=hashlib.sha256(source.quote.encode()).hexdigest(),
            )
        )
    db.commit()
    db.refresh(note)
    return NoteResponse.model_validate(note, from_attributes=True)


@router.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> NoteResponse:
    return NoteResponse.model_validate(_note(note_id, user, db), from_attributes=True)


@router.patch("/notes/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: str,
    payload: NoteUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    lock_owner(db, user.id)
    current = _note(note_id, user, db)
    _check_course(payload.course_id, user, db)
    check_placement(
        db,
        user.id,
        payload.folder_id
        if "folder_id" in payload.model_fields_set
        else current.folder_id,
        payload.course_id or current.course_id,
    )
    values = {
        key: value
        for key, value in payload.model_dump(exclude={"revision"}).items()
        if value is not None or (key == "folder_id" and key in payload.model_fields_set)
    }
    values["revision"] = payload.revision + 1
    result = db.execute(
        update(Note)
        .where(
            Note.id == note_id,
            Note.user_id == user.id,
            Note.deleted.is_(False),
            Note.revision == payload.revision,
        )
        .values(**values)
    )
    if result.rowcount != 1:
        db.rollback()
        note = _note(note_id, user, db)
        raise HTTPException(
            status_code=409,
            detail={
                "message": "笔记版本冲突",
                "server_revision": note.revision,
                "server_title": note.title,
                "server_content": note.content,
                "server_tags": note.tags,
                "server_folder_id": note.folder_id,
            },
        )
    note = _note(note_id, user, db)
    _sync_links(note, user, db)
    db.commit()
    db.refresh(note)
    return NoteResponse.model_validate(note, from_attributes=True)


@router.get("/notes/{note_id}/export")
def export_note(
    note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Response:
    note = _note(note_id, user, db)
    return Response(
        content=f"# {note.title}\n\n{note.content}\n",
        media_type="text/markdown",
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(safe_name(note.title, "未命名笔记") + ".md", safe="")
        },
    )


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str,
    revision: int | None = Query(default=None, ge=1),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    lock_owner(db, user.id)
    now, days = utc_now(), retention(db, user.id)
    result = db.execute(
        update(Note)
        .where(
            Note.id == note_id,
            Note.user_id == user.id,
            Note.deleted.is_(False),
            Note.revision == revision if revision is not None else True,
        )
        .values(
            deleted=True,
            revision=Note.revision + 1,
            deleted_at=now,
            purge_after=now + timedelta(days=days) if days is not None else None,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        note = _note(note_id, user, db)
        raise HTTPException(
            409,
            {
                "message": "笔记已有新版本，请核对后再删除",
                "server_revision": note.revision,
                "server_title": note.title,
                "server_content": note.content,
                "server_tags": note.tags,
                "server_folder_id": note.folder_id,
            },
        )
    db.commit()


@router.get("/notes/{note_id}/backlinks", response_model=List[NoteResponse])
def backlinks(
    note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> List[NoteResponse]:
    _note(note_id, user, db)
    ids = db.scalars(
        select(NoteLink.source_note_id).where(
            NoteLink.target_note_id == note_id, NoteLink.user_id == user.id
        )
    ).all()
    if not ids:
        return []
    return [
        NoteResponse.model_validate(n, from_attributes=True)
        for n in db.scalars(
            select(Note).where(
                Note.id.in_(ids), Note.user_id == user.id, Note.deleted.is_(False)
            )
        ).all()
    ]


@router.get("/notes/{note_id}/citations", response_model=List[CitationResponse])
def note_citations(
    note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> List[CitationResponse]:
    _note(note_id, user, db)
    cache = {}
    return [
        citation_response(db, user.id, c, cache)
        for c in db.scalars(
            select(Citation)
            .where(Citation.note_id == note_id, Citation.user_id == user.id)
            .order_by(Citation.created_at, Citation.id)
        ).all()
    ]


@router.post(
    "/notes/{note_id}/citations",
    response_model=CitationResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_citation(
    note_id: str,
    payload: CitationCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CitationResponse:
    note = lock_note(db, user.id, note_id)
    chunk = checked_chunk(
        db, payload.version_id, payload.chunk_id, payload.quote, user.id, note.course_id
    )
    existing = db.scalar(
        select(Citation)
        .where(
            Citation.note_id == note.id,
            Citation.user_id == user.id,
            Citation.version_id == payload.version_id,
            Citation.chunk_id == chunk.id,
            Citation.quote == payload.quote,
        )
        .order_by(Citation.created_at, Citation.id)
    )
    if existing:
        result = citation_response(db, user.id, existing)
        db.commit()
        return result
    count = db.scalar(
        select(func.count())
        .select_from(Citation)
        .where(
            Citation.note_id == note.id,
            Citation.user_id == user.id,
        )
    )
    if count >= 50:
        raise HTTPException(422, "每篇笔记最多50条资料引用，请先移除不需要的引用")
    citation = Citation(
        user_id=user.id,
        note_id=note.id,
        version_id=payload.version_id,
        chunk_id=chunk.id,
        locator_type=chunk.locator_type,
        locator_value=chunk.locator_value,
        quote=payload.quote,
        source_kind=chunk.source_kind,
        quote_hash=hashlib.sha256(payload.quote.encode()).hexdigest(),
    )
    db.add(citation)
    db.commit()
    db.refresh(citation)
    return citation_response(db, user.id, citation)


@router.delete("/notes/{note_id}/citations/{citation_id}", status_code=204)
def remove_citation(
    note_id: str,
    citation_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    lock_note(db, user.id, note_id)
    changed = db.execute(
        delete(Citation).where(
            Citation.id == citation_id,
            Citation.note_id == note_id,
            Citation.user_id == user.id,
        )
    )
    if changed.rowcount != 1:
        raise HTTPException(404, "引用不存在或不属于这篇笔记")
    db.commit()


@router.get("/assets/{asset_id}/references", response_model=List[NoteResponse])
def asset_references(
    asset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    asset = db.scalar(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    if not asset:
        raise HTTPException(404, "图片不存在")
    rows = db.scalars(
        select(Note)
        .join(AssetReference, AssetReference.note_id == Note.id)
        .where(
            AssetReference.asset_id == asset_id,
            AssetReference.user_id == user.id,
            Note.user_id == user.id,
            Note.deleted.is_(False),
        )
    ).all()
    return [NoteResponse.model_validate(row, from_attributes=True) for row in rows]
