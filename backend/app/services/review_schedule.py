"""M4 read adapter for an accessible, paginated review calendar."""

from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, or_, case, and_
from ..core.database import begin_read_snapshot
from ..models import Course, ExamPaper, ExamAttempt, Mistake, ReviewTask
from .courses import owned_course


def page(db, user, state, offset, limit, *, course_id=None, q="", period="all"):
    begin_read_snapshot(db)
    if course_id is not None:
        owned_course(db, user.id, course_id)
    today = datetime.now(ZoneInfo(user.timezone)).date().isoformat()
    detail = case(
        (func.json_valid(Mistake.detail_json), Mistake.detail_json), else_="{}"
    )
    accessible = (
        select(Mistake.id)
        .join(ExamAttempt, ExamAttempt.id == Mistake.attempt_id)
        .join(ExamPaper, ExamPaper.id == ExamAttempt.paper_id)
        .join(Course, Course.id == ExamPaper.course_id)
        .where(
            Mistake.user_id == user.id,
            ExamAttempt.user_id == user.id,
            ExamPaper.user_id == user.id,
            Course.user_id == user.id,
            Course.deleted_at.is_(None),
            func.coalesce(func.json_extract(detail, "$.removed_from_bank"), 0) != 1,
        )
    )
    if course_id is not None:
        accessible = accessible.where(Course.id == course_id)
    query = select(ReviewTask).where(
        ReviewTask.user_id == user.id,
        (
            ReviewTask.mistake_id.in_(accessible)
            if course_id is not None
            else or_(
                ReviewTask.mistake_id.is_(None), ReviewTask.mistake_id.in_(accessible)
            )
        ),
    )
    if q.strip():
        query = query.where(
            func.instr(func.lower(ReviewTask.title), q.strip().lower()) > 0
        )
    base = query.subquery()
    pending = base.c.status == "PENDING"
    conditions = {
        "pending": pending,
        "due": and_(pending, base.c.due_date <= today),
        "overdue": and_(pending, base.c.due_date < today),
        "today": and_(pending, base.c.due_date == today),
        "upcoming": and_(pending, base.c.due_date > today),
        "completed": base.c.status == "COMPLETED",
    }
    # One bounded aggregate for the complete filtered set, never per-row queries.
    counts = dict(
        db.execute(
            select(
                *[
                    func.coalesce(func.sum(case((condition, 1), else_=0)), 0).label(
                        name
                    )
                    for name, condition in conditions.items()
                ]
            )
        )
        .mappings()
        .one()
    )
    if state == "pending":
        query = query.where(ReviewTask.status == "PENDING")
    elif state == "completed":
        query = query.where(ReviewTask.status == "COMPLETED")
    dates = {
        "due": ReviewTask.due_date <= today,
        "overdue": ReviewTask.due_date < today,
        "today": ReviewTask.due_date == today,
        "upcoming": ReviewTask.due_date > today,
    }
    if period != "all":
        query = query.where(dates[period])
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(ReviewTask.due_date, ReviewTask.id).offset(offset).limit(limit)
    ).all()
    return dict(
        items=rows,
        total=total,
        offset=offset,
        limit=limit,
        course_id=course_id,
        counts=counts,
        today=today,
        timezone=user.timezone,
    )
