from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..dependencies import current_user
from ..models import User
from ..schemas.note_graph import NoteGraph
from ..services.note_graph import note_graph

router = APIRouter(prefix="/api/v1", tags=["notes"])


@router.get("/courses/{course_id}/note-graph", response_model=NoteGraph)
def course_note_graph(
    course_id: str,
    q: str = Query(default="", max_length=200),
    link_state: Literal["all", "linked", "isolated"] = "all",
    focus_note_id: UUID | None = None,
    limit: int = Query(default=120, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return note_graph(
        db,
        user.id,
        course_id,
        q,
        link_state,
        str(focus_note_id) if focus_note_id else None,
        limit,
    )
