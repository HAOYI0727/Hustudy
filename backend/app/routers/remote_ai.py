from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import User
from ..schemas.remote_ai import PreviewRequest, ConsentRequest, RemoteQueryResponse
from ..services import remote_ai

router = APIRouter(prefix="/api/v1", tags=["ai"])


@router.get("/ai/provider")
def provider(user: User = Depends(current_user)):
    return remote_ai.provider_status()


@router.post(
    "/courses/{course_id}/remote-queries/preview",
    response_model=RemoteQueryResponse,
    status_code=201,
)
def preview(
    course_id: str,
    payload: PreviewRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return remote_ai.preview(db, user.id, course_id, payload)


@router.post(
    "/remote-queries/{query_id}/confirm",
    response_model=RemoteQueryResponse,
    status_code=202,
)
def confirm(
    query_id: str,
    payload: ConsentRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return remote_ai.confirm(db, user.id, query_id)


@router.get("/remote-queries/{query_id}", response_model=RemoteQueryResponse)
def get_query(
    query_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return remote_ai.response(db, remote_ai.owned_query(db, user.id, query_id))


@router.post("/remote-queries/{query_id}/cancel", response_model=RemoteQueryResponse)
def cancel(
    query_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return remote_ai.cancel(db, user.id, query_id)
