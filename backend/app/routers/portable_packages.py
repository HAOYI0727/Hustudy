from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from ..core.database import get_db
from ..core.storage import InsufficientStorage
from ..dependencies import current_user
from ..models import User
from ..schemas.portable_packages import (
    PackageExport,
    PackageImportRequest,
    PackageSelection,
)
from ..services import portable_packages as service

router = APIRouter(prefix="/api/v1", tags=["portable-packages"])


def call(action, *args):
    try:
        return action(*args)
    except InsufficientStorage:
        raise
    except (ValueError, OSError) as error:
        # Never expose server paths from filesystem exception strings.
        message = (
            str(error)
            if isinstance(error, ValueError)
            else "包文件读写失败，请重试；现有内容保留"
        )
        raise HTTPException(422, message) from error
    except OperationalError as error:
        raise HTTPException(
            409, "当前有其他写入，请核对导入状态后使用原请求重试"
        ) from error


@router.get("/courses/{course_id}/packages/catalog")
def catalog(
    course_id: UUID,
    kind: Literal["course", "folder"] = "course",
    folder_id: UUID | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return call(service.source_catalog, db, user.id, course_id, kind, folder_id)


@router.post("/packages/export")
def export(
    payload: PackageExport,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    path, name = call(service.export_package, db, user.id, payload)
    return FileResponse(
        path,
        filename=name,
        media_type="application/zip",
        headers={"Cache-Control": "no-store"},
        background=BackgroundTask(service.cleanup_file, path),
    )


@router.post("/packages/preview")
def preview(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return call(service.create_preview, db, user.id, file)


@router.delete("/packages/previews/{preview_id}", status_code=204)
def remove_preview(
    preview_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    call(service.remove_preview, db, user.id, preview_id)


@router.get("/packages/previews")
def previews(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return call(service.list_previews, db, user.id)


@router.post("/packages/selection-preview")
def selection_preview(
    payload: PackageSelection,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return call(service.selection_preview, db, user.id, payload)


@router.post("/packages/import")
def import_package(
    payload: PackageImportRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return call(service.import_package, db, user.id, payload)


@router.get("/packages/imports/{request_id}")
def status(
    request_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return call(service.import_status, db, user.id, request_id)
