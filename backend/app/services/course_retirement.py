"""Shared transaction orchestrator: each business module owns its lifecycle adapter."""

from fastapi import HTTPException
from sqlalchemy import update
from ..models import Course
from ..models.base import utc_now
from ..schemas.course import CourseResponse, CourseDeletionPreview
from .courses import owned_course
from .material_retirement import course_material_counts, retire_course_materials
from .note_retirement import course_note_counts, retire_course_notes
from .ai_retirement import course_ai_counts, retire_course_ai
from .exam_retirement import course_exam_counts, retire_course_exams


def deletion_preview(db, user_id, course_id):
    # Explicit read transaction gives all module counts the same SQLite snapshot.
    connection = db.connection()
    if (
        connection.dialect.name == "sqlite"
        and not connection.connection.driver_connection.in_transaction
    ):
        connection.exec_driver_sql("BEGIN")
    course = owned_course(db, user_id, course_id)
    counts = {}
    for count in (
        course_material_counts,
        course_note_counts,
        course_ai_counts,
        course_exam_counts,
    ):
        counts.update(count(db, user_id, course_id))
    return CourseDeletionPreview(
        course=CourseResponse.model_validate(course, from_attributes=True),
        counts=counts,
    )


def retire_course(db, user_id, course_id, revision):
    owned_course(db, user_id, course_id)
    locked = db.execute(
        update(Course)
        .where(
            Course.id == course_id,
            Course.user_id == user_id,
            Course.deleted_at.is_(None),
            Course.revision == revision,
        )
        .values(updated_at=Course.updated_at)
        .execution_options(synchronize_session=False)
    )
    if locked.rowcount != 1:
        db.rollback()
        course = owned_course(db, user_id, course_id)
        raise HTTPException(
            409,
            {
                "message": "课程已改变，请重新核对删除范围",
                "server_course": CourseResponse.model_validate(
                    course, from_attributes=True
                ).model_dump(mode="json"),
            },
        )
    for retire in (
        retire_course_materials,
        retire_course_notes,
        retire_course_ai,
        retire_course_exams,
    ):
        retire(db, user_id, course_id)
    db.execute(
        update(Course)
        .where(Course.id == course_id, Course.user_id == user_id)
        .values(
            deleted_at=utc_now(), revision=Course.revision + 1, updated_at=utc_now()
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    db.expire_all()
