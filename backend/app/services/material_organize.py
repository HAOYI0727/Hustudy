"""Atomic, snapshot-checked material metadata changes; never rewrite sources."""

from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select
from ..models import Document
from ..models.base import utc_now
from ..repositories.materials import active_document
from ..schemas.material import DocumentMetadata
from .courses import owned_course


def metadata(row):
    return DocumentMetadata.model_validate(row).model_dump(mode="json")


def organize(db, user_id, course_id, payload):
    owned_course(db, user_id, course_id, lock=True)
    ids = [str(item.id) for item in payload.items]
    rows = db.scalars(
        select(Document).where(
            Document.id.in_(ids),
            Document.user_id == user_id,
            Document.course_id == course_id,
            Document.library_scope == "material",
            Document.deleted_at.is_(None),
        )
    ).all()
    if len(rows) != len(ids):
        raise HTTPException(404, "部分资料不存在或已不可访问，请重新选择")
    by_id = {row.id: row for row in rows}
    conflicts = [
        metadata(by_id[str(item.id)])
        for item in payload.items
        if by_id[str(item.id)].updated_at != item.expected_updated_at
    ]
    if conflicts:
        raise HTTPException(
            409,
            {
                "message": "所选资料已变化，本次整理未写入，请核对后重新读取所选资料",
                "conflicts": conflicts,
            },
        )
    changes = []
    for item in payload.items:
        row = by_id[str(item.id)]
        tags = {
            "keep": lambda: row.tags,
            "add": lambda: list(dict.fromkeys(row.tags + payload.tags)),
            "remove": lambda: [tag for tag in row.tags if tag not in payload.tags],
            "replace": lambda: payload.tags,
            "clear": lambda: [],
        }[payload.tags_mode]()
        if len(tags) > 12:
            raise HTTPException(
                422,
                {
                    "message": f"资料「{row.name}」整理后超过12个标签，本次未修改任何资料",
                    "document_id": row.id,
                },
            )
        category = payload.category if payload.category is not None else row.category
        changes.append((row, category, tags))
    changed = 0
    now = utc_now()
    for row, category, tags in changes:
        if row.category != category or row.tags != tags:
            row.category, row.tags = category, list(tags)
            row.updated_at = max(now, row.updated_at + timedelta(microseconds=1))
            changed += 1
    db.commit()
    return {"items": [by_id[id] for id in ids], "changed": changed}


def update_one(db, user_id, document_id, payload):
    document = active_document(db, document_id, user_id)
    owned_course(db, user_id, document.course_id, lock=True)
    document = active_document(db, document_id, user_id)
    if (
        payload.expected_updated_at is not None
        and document.updated_at != payload.expected_updated_at
    ):
        raise HTTPException(
            409,
            {
                "message": "资料已在其他窗口修改，本地输入已保留，请先核对服务端整理",
                "server_document": metadata(document),
            },
        )
    values = payload.model_dump(exclude_unset=True, exclude={"expected_updated_at"})
    if any(getattr(document, key) != value for key, value in values.items()):
        stamp = max(utc_now(), document.updated_at + timedelta(microseconds=1))
        for key, value in values.items():
            setattr(document, key, value)
        document.updated_at = stamp
    db.commit()
    return document
