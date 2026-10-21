"""Separate catalogue and storage scope, sharing immutable M1 versions."""

import json
from fastapi import HTTPException
from sqlalchemy import select, or_
from ..models import Document, DocumentVersion, PastPaper
from ..repositories.materials import active_document
from .courses import owned_course
from . import question_bank as bank


def rows(db, user_id, course_id):
    owned_course(db, user_id, course_id)
    bank.no_active_attempt(db, user_id, course_id)
    refs = []
    for meta in db.scalars(
        select(PastPaper.bank_meta_json).where(
            PastPaper.user_id == user_id, PastPaper.course_id == course_id
        )
    ):
        value = json.loads(meta).get("version_id")
        if value:
            refs.append(value)
    legacy = select(DocumentVersion.document_id).where(
        DocumentVersion.id.in_(refs), DocumentVersion.user_id == user_id
    )
    return db.scalars(
        select(Document)
        .where(
            Document.user_id == user_id,
            Document.course_id == course_id,
            Document.deleted_at.is_(None),
            or_(Document.library_scope == "question_bank", Document.id.in_(legacy)),
        )
        .order_by(Document.created_at.desc())
        .limit(2000)
    ).all()


def move(db, user_id, course_id, document_id):
    owned_course(db, user_id, course_id, lock=True)
    bank.no_active_attempt(db, user_id, course_id)
    document = active_document(db, document_id, user_id)
    if document.course_id != course_id or document.id not in {
        r.id for r in rows(db, user_id, course_id)
    }:
        raise HTTPException(404, "该文件不是当前题库的来源")
    document.library_scope = "question_bank"
    db.commit()
    return {"moved": True}
