import hashlib
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import delete, select, update
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
)

from ..services.courses import owned_course

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
            select(Note).where(
                Note.id == target_id, Note.user_id == user.id, Note.deleted.is_(False)
            )
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
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> List[NoteResponse]:
    statement = select(Note).where(Note.user_id == user.id, Note.deleted.is_(False))
    if course_id:
        owned_course(db, user.id, course_id)
        statement = statement.where(Note.course_id == course_id)
    return [
        NoteResponse.model_validate(n, from_attributes=True)
        for n in db.scalars(statement.order_by(Note.updated_at.desc())).all()
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


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> NoteResponse:
    _check_course(payload.course_id, user, db)
    chunks = [
        checked_chunk(db, c.version_id, c.chunk_id, c.quote, user.id, payload.course_id)
        for c in payload.citations
    ]
    note = Note(
        user_id=user.id,
        course_id=payload.course_id,
        title=payload.title,
        content=payload.content,
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
    _check_course(payload.course_id, user, db)
    values = {
        key: value
        for key, value in payload.model_dump(exclude={"revision"}).items()
        if value is not None
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
        headers={"Content-Disposition": f'attachment; filename="note-{note.id}.md"'},
    )


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> None:
    note = _note(note_id, user, db)
    note.deleted = True
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
    return [
        CitationResponse.model_validate(c, from_attributes=True)
        for c in db.scalars(
            select(Citation).where(
                Citation.note_id == note_id, Citation.user_id == user.id
            )
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
    note = _note(note_id, user, db)
    chunk = checked_chunk(
        db, payload.version_id, payload.chunk_id, payload.quote, user.id, note.course_id
    )
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
    return CitationResponse.model_validate(citation, from_attributes=True)


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
