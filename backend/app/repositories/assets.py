"""M1 ownership and source validity boundary for all image consumers."""

from fastapi import HTTPException
from sqlalchemy import select, and_, or_, exists
from ..models import Asset, Course, Document, DocumentVersion
from .materials import active_version


def available_assets(user_id, course_id=None):
    """SQL authorization scope shared by listing, facets, counts and writes."""
    source = exists(
        select(DocumentVersion.id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(
            DocumentVersion.id == Asset.source_version_id,
            DocumentVersion.user_id == user_id,
            Document.user_id == user_id,
            Document.course_id == Asset.course_id,
            Document.deleted_at.is_(None),
        )
    )
    conditions = [
        Asset.user_id == user_id,
        Asset.deleted.is_(False),
        or_(
            Asset.course_id.is_(None),
            exists(
                select(Course.id).where(
                    Course.id == Asset.course_id,
                    Course.user_id == user_id,
                    Course.deleted_at.is_(None),
                )
            ),
        ),
        or_(Asset.source_locator_type.is_(None), source),
    ]
    if course_id is not None:
        conditions.append(Asset.course_id == course_id)
    return and_(*conditions)


def owned_asset(db, asset_id, user_id):
    row = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id))
    if row is None:
        raise HTTPException(404, "图片不存在")
    return row


def source_available(db, asset, user_id):
    if asset.deleted:
        return False
    if asset.course_id and not db.scalar(
        select(Course.id).where(
            Course.id == asset.course_id,
            Course.user_id == user_id,
            Course.deleted_at.is_(None),
        )
    ):
        return False
    if asset.source_locator_type is None:
        return True
    if not asset.source_version_id:
        return False
    try:
        active_version(db, asset.source_version_id, user_id, asset.course_id)
        return True
    except HTTPException:
        return False


def active_asset(db, asset_id, user_id):
    row = owned_asset(db, asset_id, user_id)
    if not source_available(db, row, user_id):
        raise HTTPException(404, "图片或来源资料已不可用")
    return row
