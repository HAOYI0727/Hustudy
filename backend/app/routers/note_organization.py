"""M3 folder organization, atomic bulk edits and idempotent Markdown import."""

import json
from pathlib import PurePosixPath
from uuid import uuid4, UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import Note, NoteFolder, User
from ..schemas.notes import NoteCreate, NoteResponse
from ..schemas.note_organization import (
    FolderCreate,
    FolderUpdate,
    FolderResponse,
    NoteBatch,
)
from ..services.note_folders import (
    lock_owner,
    owned_folder,
    check_placement,
    tree_rows,
    validate_tree,
)
from ..services.courses import owned_course

router = APIRouter(prefix="/api/v1", tags=["note-organization"])


@router.get("/note-folders", response_model=list[FolderResponse])
def folders(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_course(db, user.id, course_id)
    return [
        FolderResponse.model_validate(row, from_attributes=True)
        for row in db.scalars(
            select(NoteFolder)
            .where(NoteFolder.user_id == user.id, NoteFolder.course_id == course_id)
            .order_by(NoteFolder.name, NoteFolder.id)
        )
    ]


@router.post("/note-folders", response_model=FolderResponse, status_code=201)
def create_folder(
    payload: FolderCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    lock_owner(db, user.id)
    owned_course(db, user.id, payload.course_id)
    if payload.parent_id:
        owned_folder(db, user.id, payload.parent_id, payload.course_id)
    row = NoteFolder(id=str(uuid4()), user_id=user.id, **payload.model_dump())
    _validate_tree(
        db,
        user.id,
        row.course_id,
        {k: getattr(row, k) for k in ("id", "name", "parent_id", "course_id")},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return FolderResponse.model_validate(row, from_attributes=True)


def _validate_tree(db, user_id, course_id, changed):
    rows = [
        row for row in tree_rows(db, user_id, course_id) if row["id"] != changed["id"]
    ]
    try:
        validate_tree(rows + [changed])
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.patch("/note-folders/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: str,
    payload: FolderUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    lock_owner(db, user.id)
    row = owned_folder(db, user.id, folder_id)
    if row.revision != payload.revision:
        raise HTTPException(409, "文件夹已在其他位置修改，请刷新后重试")
    changed = {k: getattr(row, k) for k in ("id", "name", "parent_id", "course_id")}
    changed.update(payload.model_dump(exclude_unset=True, exclude={"revision"}))
    if changed["parent_id"]:
        owned_folder(db, user.id, changed["parent_id"], row.course_id)
    _validate_tree(db, user.id, row.course_id, changed)
    row.name, row.parent_id = changed["name"], changed["parent_id"]
    row.revision += 1
    db.commit()
    db.refresh(row)
    return FolderResponse.model_validate(row, from_attributes=True)


@router.delete("/note-folders/{folder_id}", status_code=204)
def remove_folder(
    folder_id: str,
    revision: int = Query(ge=1),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    lock_owner(db, user.id)
    row = owned_folder(db, user.id, folder_id)
    if row.revision != revision:
        raise HTTPException(409, "文件夹版本冲突，请刷新后重试")
    if db.scalar(
        select(NoteFolder.id).where(NoteFolder.parent_id == row.id).limit(1)
    ) or db.scalar(
        select(Note.id)
        .where(Note.folder_id == row.id, Note.deleted.is_(False))
        .limit(1)
    ):
        raise HTTPException(409, "请先移出笔记和子文件夹，再删除空文件夹")
    db.execute(
        delete(NoteFolder).where(NoteFolder.id == row.id, NoteFolder.user_id == user.id)
    )
    db.commit()


@router.post("/notes/batch", response_model=list[NoteResponse])
def batch_notes(
    payload: NoteBatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    lock_owner(db, user.id)
    items = {n.id: n.revision for n in payload.notes}
    rows = db.scalars(
        select(Note).where(
            Note.id.in_(items), Note.user_id == user.id, Note.deleted.is_(False)
        )
    ).all()
    if len(rows) != len(items):
        raise HTTPException(404, "部分笔记不存在或不可访问，未修改任何笔记")
    changes = []
    for row in rows:
        if row.course_id:
            owned_course(db, user.id, row.course_id)
        if row.revision != items[row.id]:
            raise HTTPException(
                409, "部分笔记已有新版本，未修改任何笔记；请刷新列表后重选"
            )
        if "folder_id" in payload.model_fields_set:
            check_placement(db, user.id, payload.folder_id, row.course_id)
        tags = list(
            dict.fromkeys(
                [t for t in row.tags if t not in payload.remove_tags] + payload.add_tags
            )
        )
        if len(tags) > 12:
            raise HTTPException(422, "部分笔记将超过12个标签，未修改任何笔记")
        changes.append((row, tags))
    for row, tags in changes:
        row.tags = tags
        if "folder_id" in payload.model_fields_set:
            row.folder_id = payload.folder_id
        row.revision += 1
    db.commit()
    return [NoteResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("/notes/import-markdown", response_model=NoteResponse, status_code=201)
async def import_markdown(
    file: UploadFile = File(...),
    course_id: str = Form(...),
    request_id: UUID = Form(...),
    tags: str = Form("[]"),
    folder_id: str | None = Form(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from .notes import create_note

    name = PurePosixPath((file.filename or "").replace("\\", "/")).name
    if PurePosixPath(name).suffix.lower() not in {".md", ".markdown"}:
        raise HTTPException(422, "请选择.md或.markdown文件")
    content = await file.read(2 * 1024 * 1024 + 1)
    await file.close()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "每份Markdown文件最多2MiB")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(422, "文件不是UTF-8编码，请转为UTF-8后重试") from error
    if "\x00" in decoded:
        raise HTTPException(422, "文件包含无效的二进制内容")
    try:
        title = PurePosixPath(name).stem.strip()
        if any(ord(c) < 32 or ord(c) == 127 for c in title):
            raise ValueError()
        payload = NoteCreate(
            request_id=request_id,
            course_id=course_id,
            folder_id=folder_id or None,
            title=title,
            content=decoded,
            tags=json.loads(tags),
        )
    except (ValidationError, ValueError, TypeError) as error:
        raise HTTPException(
            422, "文件名或统一标签不合法：标题1–240字，最多12个标签、每个1–32字"
        ) from error
    return create_note(payload, user, db)
