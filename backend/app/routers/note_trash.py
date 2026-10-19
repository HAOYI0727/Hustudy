"""Owned, revision-checked trash operations. Reads never purge data."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, load_only
from ..core.database import get_db, begin_read_snapshot
from ..dependencies import current_user
from ..models import Note, Course, User, NoteTrashPolicy
from ..models.base import utc_now
from ..schemas.note_trash import (
    TrashBatch,
    TrashPage,
    EmptyTrash,
    TrashPolicyUpdate,
    TrashPolicyResponse,
)
from ..services import note_trash as service
from ..services.note_folders import lock_owner
from ..services.courses import owned_course

router = APIRouter(prefix="/api/v1/notes/trash", tags=["note-trash"])


@router.get("/policy", response_model=TrashPolicyResponse)
def get_policy(user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = service.policy(db, user.id)
    return {
        "retention_days": row.retention_days if row else 30,
        "revision": row.revision if row else 0,
    }


@router.put("/policy", response_model=TrashPolicyResponse)
def set_policy(
    payload: TrashPolicyUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    lock_owner(db, user.id)
    row = service.policy(db, user.id)
    if payload.revision != (row.revision if row else 0):
        raise HTTPException(409, "回收站设置已变化，请刷新后重试")
    if row is None:
        row = NoteTrashPolicy(
            user_id=user.id, retention_days=payload.retention_days, revision=1
        )
        db.add(row)
    else:
        row.retention_days = payload.retention_days
        row.revision += 1
    for note in db.scalars(
        select(Note)
        .options(load_only(Note.deleted_at, Note.purge_after, Note.revision))
        .where(Note.user_id == user.id, Note.deleted.is_(True))
    ):
        note.purge_after = (
            note.deleted_at + timedelta(days=payload.retention_days)
            if payload.retention_days is not None
            else None
        )
        note.revision += 1
    db.commit()
    return get_policy(user, db)


@router.get("", response_model=TrashPage)
def list_trash(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    # Snapshot and page must describe the same SQLite read transaction.
    begin_read_snapshot(db)
    total, digest = service.snapshot(db, user.id)
    rows = db.execute(
        select(Note, Course)
        .options(
            load_only(
                Note.id,
                Note.title,
                Note.course_id,
                Note.folder_id,
                Note.tags,
                Note.revision,
                Note.deleted_at,
                Note.purge_after,
            )
        )
        .outerjoin(Course, Course.id == Note.course_id)
        .where(Note.user_id == user.id, Note.deleted.is_(True))
        .order_by(Note.deleted_at.desc(), Note.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                **{
                    key: getattr(note, key)
                    for key in (
                        "id",
                        "title",
                        "course_id",
                        "folder_id",
                        "tags",
                        "revision",
                        "deleted_at",
                        "purge_after",
                    )
                },
                "course_name": course.name
                if course and course.user_id == user.id
                else "未关联课程",
                "restore_requires_course": not course or course.deleted_at is not None,
            }
            for note, course in rows
        ],
        "total": total,
        "snapshot": digest,
    }


@router.post("/batch")
def batch(
    payload: TrashBatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    lock_owner(db, user.id)
    revisions = {str(n.id): n.revision for n in payload.notes}
    rows = db.scalars(
        select(Note).where(Note.user_id == user.id, Note.id.in_(revisions))
    ).all()
    if len(rows) != len(revisions):
        raise HTTPException(404, "部分笔记不存在或不可访问，未修改任何笔记")
    for row in rows:
        if row.revision != revisions[row.id] or row.deleted != (
            payload.action != "trash"
        ):
            raise HTTPException(
                409, "笔记状态或版本已变化，未修改任何笔记；请刷新后重选"
            )
    now, days = utc_now(), service.retention(db, user.id)
    if payload.action == "purge":
        service.purge(db, user.id, list(revisions))
    elif payload.action == "trash":
        for row in rows:
            service.mark_trashed(row, days, now)
    else:
        for row in rows:
            course = db.get(Course, row.course_id) if row.course_id else None
            if not course or course.user_id != user.id or course.deleted_at is not None:
                if payload.fallback_course_id is None:
                    raise HTTPException(422, "原课程不可用，请选择恢复到的课程")
                target = owned_course(db, user.id, str(payload.fallback_course_id))
                row.course_id, row.folder_id = target.id, None
        for row in rows:
            row.deleted, row.deleted_at, row.purge_after = False, None, None
            row.revision += 1
    db.commit()
    return {"affected": len(rows)}


@router.post("/empty")
def empty(
    payload: EmptyTrash,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    lock_owner(db, user.id)
    _, digest = service.snapshot(db, user.id)
    if digest != payload.snapshot:
        raise HTTPException(409, "回收站内容已变化，未清空；请刷新并重新确认")
    count = service.purge(db, user.id)
    db.commit()
    return {"affected": count}
