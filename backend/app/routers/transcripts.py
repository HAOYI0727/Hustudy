from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import ManualTranscript, User
from ..repositories.materials import active_version
from ..schemas.transcripts import (
    TranscriptCreate,
    TranscriptUpdate,
    TranscriptRevision,
    TranscriptResponse,
)
from ..services import transcripts as service

router = APIRouter(prefix="/api/v1", tags=["materials"])


def response(row):
    return TranscriptResponse.model_validate(row, from_attributes=True)


@router.get(
    "/versions/{version_id}/transcripts", response_model=list[TranscriptResponse]
)
def list_transcripts(
    version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    active_version(db, version_id, user.id)
    return [
        response(row)
        for row in db.scalars(
            select(ManualTranscript)
            .where(
                ManualTranscript.version_id == version_id,
                ManualTranscript.user_id == user.id,
            )
            .order_by(ManualTranscript.page, ManualTranscript.created_at.desc())
        ).all()
    ]


@router.post(
    "/versions/{version_id}/transcripts",
    response_model=TranscriptResponse,
    status_code=201,
)
def create(
    version_id: str,
    payload: TranscriptCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return response(service.create_draft(db, user.id, version_id, payload))


@router.patch("/transcripts/{transcript_id}", response_model=TranscriptResponse)
def edit(
    transcript_id: str,
    payload: TranscriptUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return response(service.update_draft(db, user.id, transcript_id, payload))


@router.post("/transcripts/{transcript_id}/confirm", response_model=TranscriptResponse)
def confirm(
    transcript_id: str,
    payload: TranscriptRevision,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return response(service.confirm_draft(db, user.id, transcript_id, payload.revision))


@router.post("/transcripts/{transcript_id}/withdraw", response_model=TranscriptResponse)
def withdraw(
    transcript_id: str,
    payload: TranscriptRevision,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return response(service.withdraw(db, user.id, transcript_id, payload.revision))
