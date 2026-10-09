import hashlib
import re
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.database import get_db
from ..dependencies import current_user
from ..models import Asset, Citation, Course, DocumentChunk, DocumentVersion, Note, NoteLink, User
from ..schemas.notes import AssetResponse, CitationCreate, CitationResponse, NoteCreate, NoteResponse, NoteUpdate

router = APIRouter(prefix="/api/v1", tags=["notes"])
LINK_RE = re.compile(r"\[\[note:([0-9a-fA-F-]{36})(?:\|([^\]]+))?\]\]")
ALLOWED_IMAGES = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _note(note_id: str, user: User, db: Session) -> Note:
    note = db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user.id, Note.deleted.is_(False)))
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return note


def _check_course(course_id: str | None, user: User, db: Session) -> None:
    if course_id and not db.scalar(select(Course).where(Course.id == course_id, Course.user_id == user.id)):
        raise HTTPException(status_code=404, detail="课程不存在")


def _sync_links(note: Note, user: User, db: Session) -> None:
    db.execute(delete(NoteLink).where(NoteLink.source_note_id == note.id, NoteLink.user_id == user.id))
    for target_id, label in LINK_RE.findall(note.content):
        if target_id == note.id:
            continue
        target = db.scalar(select(Note).where(Note.id == target_id, Note.user_id == user.id, Note.deleted.is_(False)))
        if target:
            db.add(NoteLink(user_id=user.id, source_note_id=note.id, target_note_id=target.id, label=label or target.title))


@router.get("/notes", response_model=List[NoteResponse])
def list_notes(course_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[NoteResponse]:
    statement = select(Note).where(Note.user_id == user.id, Note.deleted.is_(False))
    if course_id:
        statement = statement.where(Note.course_id == course_id)
    return [NoteResponse.model_validate(n, from_attributes=True) for n in db.scalars(statement.order_by(Note.updated_at.desc())).all()]


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> NoteResponse:
    _check_course(payload.course_id, user, db)
    note = Note(user_id=user.id, course_id=payload.course_id, title=payload.title, content=payload.content)
    db.add(note); db.flush(); _sync_links(note, user, db); db.commit(); db.refresh(note)
    return NoteResponse.model_validate(note, from_attributes=True)


@router.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> NoteResponse:
    return NoteResponse.model_validate(_note(note_id, user, db), from_attributes=True)


@router.patch("/notes/{note_id}", response_model=NoteResponse)
def update_note(note_id: str, payload: NoteUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> NoteResponse:
    note = _note(note_id, user, db)
    if payload.revision != note.revision:
        raise HTTPException(status_code=409, detail={"message": "笔记版本冲突", "server_revision": note.revision, "server_content": note.content})
    _check_course(payload.course_id, user, db)
    if payload.title is not None: note.title = payload.title
    if payload.content is not None: note.content = payload.content
    if payload.course_id is not None: note.course_id = payload.course_id
    note.revision += 1
    _sync_links(note, user, db); db.commit(); db.refresh(note)
    return NoteResponse.model_validate(note, from_attributes=True)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    note = _note(note_id, user, db); note.deleted = True; db.commit()


@router.get("/notes/{note_id}/backlinks", response_model=List[NoteResponse])
def backlinks(note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[NoteResponse]:
    _note(note_id, user, db)
    ids = db.scalars(select(NoteLink.source_note_id).where(NoteLink.target_note_id == note_id, NoteLink.user_id == user.id)).all()
    if not ids: return []
    return [NoteResponse.model_validate(n, from_attributes=True) for n in db.scalars(select(Note).where(Note.id.in_(ids), Note.user_id == user.id, Note.deleted.is_(False))).all()]


@router.get("/notes/{note_id}/citations", response_model=List[CitationResponse])
def note_citations(note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[CitationResponse]:
    _note(note_id, user, db)
    return [CitationResponse.model_validate(c, from_attributes=True) for c in db.scalars(select(Citation).where(Citation.note_id == note_id, Citation.user_id == user.id)).all()]


@router.post("/notes/{note_id}/citations", response_model=CitationResponse, status_code=status.HTTP_201_CREATED)
def add_citation(note_id: str, payload: CitationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> CitationResponse:
    note = _note(note_id, user, db)
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.id == payload.version_id, DocumentVersion.user_id == user.id))
    chunk = db.scalar(select(DocumentChunk).where(DocumentChunk.id == payload.chunk_id, DocumentChunk.version_id == payload.version_id, DocumentChunk.user_id == user.id))
    if not version or not chunk or payload.quote not in chunk.text:
        raise HTTPException(status_code=422, detail="引用版本、切片或摘录不匹配")
    citation = Citation(user_id=user.id, note_id=note.id, version_id=version.id, chunk_id=chunk.id, locator_type=chunk.locator_type, locator_value=chunk.locator_value, quote=payload.quote, quote_hash=hashlib.sha256(payload.quote.encode()).hexdigest())
    db.add(citation); db.commit(); db.refresh(citation)
    return CitationResponse.model_validate(citation, from_attributes=True)


@router.post("/courses/{course_id}/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def upload_asset(course_id: str, file: UploadFile = File(...), alt: str = "", user: User = Depends(current_user), db: Session = Depends(get_db)) -> AssetResponse:
    _check_course(course_id, user, db)
    if file.content_type not in ALLOWED_IMAGES:
        raise HTTPException(status_code=422, detail="图片仅支持 PNG、JPEG、WebP")
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=422, detail="图片大小不能超过 10 MiB")
    folder = Path(get_settings().storage_root) / user.id / course_id / "assets"; folder.mkdir(parents=True, exist_ok=True)
    stored = folder / f"{uuid4().hex}{Path(file.filename or 'asset').suffix.lower()}"; stored.write_bytes(data)
    asset = Asset(user_id=user.id, course_id=course_id, original_filename=Path(file.filename or "asset").name, mime_type=file.content_type, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), storage_path=str(stored), alt=alt)
    db.add(asset); db.commit(); db.refresh(asset)
    return AssetResponse.model_validate(asset, from_attributes=True)


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> FileResponse:
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id, Asset.deleted.is_(False)))
    if not asset or not Path(asset.storage_path).exists(): raise HTTPException(status_code=404, detail="图片不可用")
    return FileResponse(asset.storage_path, media_type=asset.mime_type)
