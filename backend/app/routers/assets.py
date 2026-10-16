"""M1 image endpoints; existing URLs remain compatible with NoteGraph."""

from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import Asset, Document, DocumentVersion, User
from ..repositories.assets import active_asset, owned_asset, source_available
from ..schemas.notes import AssetResponse, AssetMetadataResponse
from ..schemas.assets import AssetUpdate, AssetPageResponse
from ..services.assets import preview_source, save_asset
from ..services.asset_organization import asset_page, organize_asset
from ..repositories.assets import available_assets

from ..services.courses import owned_course

router = APIRouter(prefix="/api/v1", tags=["materials"])


def course_check(db, course_id, user_id, *, lock=False):
    owned_course(db, user_id, course_id, lock=lock)


@router.post(
    "/courses/{course_id}/assets", response_model=AssetResponse, status_code=201
)
def upload_asset(
    course_id: str,
    file: UploadFile = File(...),
    alt: str = Query(default="", max_length=500),
    source_version_id: str | None = None,
    source_page: int | None = Query(default=None, ge=1),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    course_check(db, course_id, user.id, lock=True)
    source = preview_source(db, user.id, course_id, source_version_id, source_page)
    return AssetResponse.model_validate(
        save_asset(db, user.id, course_id, file, alt, source), from_attributes=True
    )


@router.get("/assets/{asset_id}")
def get_asset(
    asset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    asset = active_asset(db, asset_id, user.id)
    if not Path(asset.storage_path).is_file():
        raise HTTPException(404, "图片不可用")
    return FileResponse(
        asset.storage_path,
        media_type=asset.mime_type,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/assets/{asset_id}/metadata", response_model=AssetMetadataResponse)
def metadata(
    asset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    asset = owned_asset(db, asset_id, user.id)
    version = (
        db.scalar(
            select(DocumentVersion).where(
                DocumentVersion.id == asset.source_version_id,
                DocumentVersion.user_id == user.id,
            )
        )
        if asset.source_version_id
        else None
    )
    document = (
        db.scalar(
            select(Document).where(
                Document.id == version.document_id, Document.user_id == user.id
            )
        )
        if version
        else None
    )
    return AssetMetadataResponse.model_validate(asset, from_attributes=True).model_copy(
        update={
            "source_document_id": document.id if document else None,
            "source_document_name": document.name if document else None,
            "source_version_no": version.version_no if version else None,
            "source_availability": "active"
            if source_available(db, asset, user.id)
            else "unavailable",
        }
    )


@router.get("/courses/{course_id}/assets", response_model=list[AssetResponse])
def list_assets(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    course_check(db, course_id, user.id)
    rows = db.scalars(
        select(Asset)
        .where(available_assets(user.id, course_id))
        .order_by(Asset.created_at.desc())
    ).all()
    return [AssetResponse.model_validate(row, from_attributes=True) for row in rows]


@router.get("/courses/{course_id}/assets/page", response_model=AssetPageResponse)
def browse_assets(
    course_id: str,
    q: str = Query(default="", max_length=200),
    tag: str | None = Query(default=None, min_length=1, max_length=32),
    origin: Literal["all", "captured", "external"] = "all",
    sort: Literal["newest", "oldest", "updated", "name"] = "newest",
    offset: int = Query(default=0, ge=0, le=100000),
    limit: int = Query(default=12, ge=1, le=48),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    course_check(db, course_id, user.id)
    return asset_page(db, user.id, course_id, q, tag, origin, sort, offset, limit)


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: str,
    payload: AssetUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return organize_asset(db, user.id, asset_id, payload)


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(
    asset_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    asset = owned_asset(db, asset_id, user.id)
    if asset.deleted:
        raise HTTPException(404, "图片不存在")
    asset.deleted = True
    db.commit()
