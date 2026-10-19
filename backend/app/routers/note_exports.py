from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import User, NoteExport
from ..schemas.note_exports import NoteExportCreate, NoteExportResponse
from ..services import note_exports as service

router = APIRouter(prefix="/api/v1/note-exports", tags=["notes"])


@router.post("", response_model=NoteExportResponse, status_code=202)
def create_export(
    payload: NoteExportCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return service.create_export(
        db,
        user.id,
        str(payload.request_id),
        [str(key) for key in payload.note_ids]
        if payload.note_ids is not None
        else None,
        payload.include_images,
    )


@router.get("", response_model=list[NoteExportResponse])
def list_exports(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(NoteExport)
        .where(NoteExport.user_id == user.id)
        .order_by(NoteExport.created_at.desc(), NoteExport.id)
        .limit(20)
    ).all()
    return [service.response(db, row) for row in rows]


@router.get("/{export_id}", response_model=NoteExportResponse)
def get_export(
    export_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return service.response(db, service.owned_export(db, export_id, user.id))


@router.post("/{export_id}/retry", response_model=NoteExportResponse, status_code=202)
def retry_export(
    export_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return service.retry_export(db, export_id, user.id)


@router.delete("/{export_id}", status_code=204)
def remove_export(
    export_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    service.remove_export(db, export_id, user.id)


@router.get("/{export_id}/download")
def download_export(
    export_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    row = service.owned_export(db, export_id, user.id)
    path = service.download_path(db, row)
    return FileResponse(
        path,
        media_type="application/zip",
        filename=service.filename(db, row),
        headers={"Cache-Control": "no-store"},
    )
