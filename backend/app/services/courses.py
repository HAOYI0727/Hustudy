"""Shared course ownership, directory filters and atomic metadata updates."""

from fastapi import HTTPException
from sqlalchemy import select, update, func, exists, or_
from ..models import Course
from ..models.base import utc_now
from ..schemas.course import CourseResponse


def owned_course(db, user_id, course_id, *, lock=False):
    if lock:
        changed = db.execute(
            update(Course)
            .where(
                Course.id == course_id,
                Course.user_id == user_id,
                Course.deleted_at.is_(None),
            )
            .values(updated_at=Course.updated_at)
            .execution_options(synchronize_session=False)
        )
        if changed.rowcount != 1:
            raise HTTPException(404, "课程不存在")
        db.expire_all()
    row = db.scalar(
        select(Course).where(
            Course.id == course_id,
            Course.user_id == user_id,
            Course.deleted_at.is_(None),
        )
    )
    if row is None:
        raise HTTPException(404, "课程不存在")
    return row


def course_directory(db, user_id, q, category, tag, sort):
    filters = [Course.user_id == user_id, Course.deleted_at.is_(None)]
    labels = func.json_each(Course.tags).table_valued("value")
    if q.strip():
        needle = q.strip().lower()
        filters.append(
            or_(
                *(
                    func.instr(func.lower(field), needle) > 0
                    for field in (Course.name, Course.description, Course.category)
                ),
                exists(
                    select(1)
                    .select_from(labels)
                    .where(func.instr(func.lower(labels.c.value), needle) > 0)
                ),
            )
        )
    if category is not None:
        filters.append(Course.category == category)
    if tag is not None:
        filters.append(
            exists(select(1).select_from(labels).where(labels.c.value == tag))
        )
    order = {
        "newest": Course.created_at.desc(),
        "updated": Course.updated_at.desc(),
        "name": Course.name.asc(),
    }[sort]
    return db.scalars(select(Course).where(*filters).order_by(order, Course.id)).all()


def organize_course(db, user_id, course_id, payload):
    owned_course(db, user_id, course_id)
    changed = db.execute(
        update(Course)
        .where(
            Course.id == course_id,
            Course.user_id == user_id,
            Course.deleted_at.is_(None),
            Course.revision == payload.revision,
        )
        .values(
            **payload.model_dump(exclude_unset=True, exclude={"revision"}),
            revision=Course.revision + 1,
            updated_at=utc_now(),
        )
        .execution_options(synchronize_session=False)
    )
    if changed.rowcount != 1:
        db.rollback()
        row = owned_course(db, user_id, course_id)
        raise HTTPException(
            409,
            {
                "message": "课程已在其他窗口修改，本地输入已保留",
                "server_course": CourseResponse.model_validate(
                    row, from_attributes=True
                ).model_dump(mode="json"),
            },
        )
    db.commit()
    db.expire_all()
    return owned_course(db, user_id, course_id)
