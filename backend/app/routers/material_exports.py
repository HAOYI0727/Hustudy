from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import User, MaterialExport
from ..schemas.material_exports import MaterialExportCreate, MaterialExportResponse
from ..services import material_exports as service

router = APIRouter(prefix="/api/v1", tags=["materials"])


@router.post(
    "/courses/{course_id}/material-exports",
    response_model=MaterialExportResponse,
    status_code=202,
)
def create_export(
    course_id: str,
    payload: MaterialExportCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return service.create_export(
        db,
        course_id,
        user.id,
        str(payload.request_id),
        None
        if payload.document_ids is None
        else [str(item) for item in payload.document_ids],
    )


@router.get(
    "/courses/{course_id}/material-exports", response_model=list[MaterialExportResponse]
)
def list_exports(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    service.owned_course(db, course_id, user.id)
    return [
        service.response(db, row)
        for row in db.scalars(
            select(MaterialExport)
            .where(
                MaterialExport.course_id == course_id, MaterialExport.user_id == user.id
            )
            .order_by(MaterialExport.created_at.desc(), MaterialExport.id)
            .limit(20)
        ).all()
    ]


@router.get("/material-exports/{export_id}", response_model=MaterialExportResponse)
def get_export(
    export_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return service.response(db, service.owned_export(db, export_id, user.id))


@router.post(
    "/material-exports/{export_id}/retry",
    response_model=MaterialExportResponse,
    status_code=202,
)
def retry_export(
    export_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return service.retry_export(db, export_id, user.id)


@router.get("/material-exports/{export_id}/download")
def download_export(
    export_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    row = service.owned_export(db, export_id, user.id)
    path = service.download_path(db, row)
    return FileResponse(
        path,
        media_type="application/zip",
        filename=f"hustudy-materials-{row.id}.zip",
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/material-exports/{export_id}", status_code=204)
def remove_export(
    export_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    service.remove_export(db, export_id, user.id)
