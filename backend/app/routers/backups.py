from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.storage import InsufficientStorage
from ..dependencies import current_user
from ..models import User, AccountArchive, ProcessingJob
from ..services import account_backups as service

router = APIRouter(prefix="/api/v1", tags=["backups"])


@router.delete("/backups/{archive_id}", status_code=204)
def remove(
    archive_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    service.remove(db, user.id, archive_id)


@router.post("/backups", status_code=202)
def create(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return service.response(db, service.create(db, user.id, "export"))


@router.get("/backups")
def listing(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(AccountArchive)
        .where(AccountArchive.user_id == user.id)
        .order_by(AccountArchive.created_at.desc(),AccountArchive.id)
        .limit(50)
    ).all()
    return [service.response(db, row) for row in rows]


@router.post("/backups/restore", status_code=202)
def restore(
    file: UploadFile = File(...),
    confirm: str = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if confirm != "RESTORE_EMPTY_ACCOUNT":
        raise HTTPException(422, "请明确确认只向空账户恢复")
    return service.response(db, service.create(db, user.id, "restore", file))


@router.get("/backups/{archive_id}")
def detail(
    archive_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return service.response(db, service.owned(db, user.id, archive_id))


@router.get("/backups/{archive_id}/download")
def download(
    archive_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    row = service.owned(db, user.id, archive_id)
    job = db.get(ProcessingJob, row.job_id)
    if row.purpose != "export" or job.status != "SUCCEEDED" or not row.artifact_path:
        raise HTTPException(409, "完整备份尚不可下载")
    try:
        service.active_sources(db, user.id, row.sources)
        path = service.storage().checked(Path(row.artifact_path))
        if not path.is_file() or service.hash_file(path) != row.sha256:
            raise ValueError("备份文件缺失或hash不符，请重新生成")
    except (ValueError, InsufficientStorage) as error:
        raise HTTPException(409, str(error)) from error
    return FileResponse(
        path,
        media_type="application/zip",
        filename="hustudy-account-" + row.id + ".zip",
        headers={"Cache-Control": "no-store"},
    )
