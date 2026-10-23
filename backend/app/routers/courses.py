from typing import Literal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import Course, User
from ..schemas.course import (
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    CourseDeletionPreview,
)
from ..schemas.workspace import WorkspaceSection, LearningRecordPage, RecordKind
from ..schemas.learning_hub import LearningDirectory, LearningDetail
from ..services.courses import course_directory, organize_course, owned_course
from ..services.course_retirement import deletion_preview, retire_course

router = APIRouter(prefix="/api/v1/courses", tags=["courses"])


@router.get("/{course_id}/learning-records", response_model=LearningRecordPage)
def learning_records(
    course_id: str, kind: RecordKind = "all", q: str = Query(default="", max_length=200),
    offset: int = Query(default=0, ge=0, le=1000000),
    limit: int = Query(default=12, ge=1, le=50),
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    from ..services.workspace import records
    return records(db, user, course_id, kind, q, offset, limit)


@router.get("/{course_id}/learning-topics", response_model=LearningDirectory)
def learning_topics(
    course_id: str, q: str = Query(default="", max_length=200),
    state: Literal["all", "needs_review", "without_questions"] = "all",
    offset: int = Query(default=0, ge=0), limit: int = Query(default=12, ge=1, le=50),
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    from ..services.learning_hub import directory
    return directory(db, user, course_id, q, state, offset, limit)


@router.get("/{course_id}/learning-topics/{topic_id}", response_model=LearningDetail)
def learning_topic(course_id: str, topic_id: str,
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.learning_hub import detail
    return detail(db, user, course_id, topic_id)


@router.get("/{course_id}/workspace/{domain}", response_model=WorkspaceSection)
def course_workspace(
    course_id: str, domain: Literal["materials", "notes", "study", "practice"],
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    from ..services.workspace import section
    return WorkspaceSection.model_validate(section(db, user, course_id, domain))


def _response(course: Course) -> CourseResponse:
    return CourseResponse.model_validate(course, from_attributes=True)


@router.get("", response_model=list[CourseResponse])
def list_courses(
    q: str = Query(default="", max_length=200),
    category: str | None = Query(default=None, min_length=1, max_length=64),
    tag: str | None = Query(default=None, min_length=1, max_length=32),
    sort: Literal["newest", "updated", "name"] = "newest",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[CourseResponse]:
    return [
        _response(row) for row in course_directory(db, user.id, q, category, tag, sort)
    ]


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CourseResponse:
    course = Course(user_id=user.id, **payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return _response(course)


def _owned(course_id: str, user: User, db: Session) -> Course:
    return owned_course(db, user.id, course_id)


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: str,
    payload: CourseUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CourseResponse:
    return _response(organize_course(db, user.id, course_id, payload))


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: str,
    revision: int = Query(ge=1),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    retire_course(db, user.id, course_id, revision)


@router.get("/{course_id}/deletion-preview", response_model=CourseDeletionPreview)
def preview_course_deletion(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return deletion_preview(db, user.id, course_id)
