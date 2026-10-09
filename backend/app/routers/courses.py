from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import Course, User
from ..schemas.course import CourseCreate, CourseResponse, CourseUpdate
router = APIRouter(prefix="/api/v1/courses", tags=["courses"])
def _response(course: Course) -> CourseResponse: return CourseResponse.model_validate(course, from_attributes=True)
@router.get("", response_model=list[CourseResponse])
def list_courses(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[CourseResponse]:
    return [_response(row) for row in db.scalars(select(Course).where(Course.user_id == user.id).order_by(Course.created_at.desc())).all()]
@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> CourseResponse:
    course = Course(user_id=user.id, name=payload.name, description=payload.description); db.add(course); db.commit(); db.refresh(course); return _response(course)
def _owned(course_id: str, user: User, db: Session) -> Course:
    course = db.scalar(select(Course).where(Course.id == course_id, Course.user_id == user.id))
    if not course: raise HTTPException(status_code=404, detail="课程不存在")
    return course
@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(course_id: str, payload: CourseUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> CourseResponse:
    course = _owned(course_id, user, db); course.name = payload.name; course.description = payload.description; db.commit(); db.refresh(course); return _response(course)
@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    db.delete(_owned(course_id, user, db)); db.commit()
