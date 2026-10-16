"""M4 course lifecycle interface; remove dependent reviews before their source."""

from sqlalchemy import delete, select, func
from ..models import (
    Topic,
    PastPaper,
    ExamBlueprint,
    ExamPaper,
    ExamAttempt,
    Mistake,
    ReviewTask,
)
from fastapi import HTTPException
from .courses import owned_course


def check_attempt_course(db, user_id, attempt_id, *, lock=False):
    course_id = db.scalar(
        select(ExamPaper.course_id)
        .join(ExamAttempt, ExamAttempt.paper_id == ExamPaper.id)
        .where(
            ExamAttempt.id == attempt_id,
            ExamAttempt.user_id == user_id,
            ExamPaper.user_id == user_id,
        )
    )
    if course_id is None:
        raise HTTPException(404, "作答记录不存在")
    return owned_course(db, user_id, course_id, lock=lock)


def check_mistake_course(db, user_id, mistake_id, *, lock=False):
    attempt_id = db.scalar(
        select(Mistake.attempt_id).where(
            Mistake.id == mistake_id, Mistake.user_id == user_id
        )
    )
    if attempt_id is None:
        raise HTTPException(404, "错题不存在")
    return check_attempt_course(db, user_id, attempt_id, lock=lock)


def attempts_in_course(user_id, course_id):
    return (
        select(ExamAttempt.id)
        .join(ExamPaper, ExamAttempt.paper_id == ExamPaper.id)
        .where(
            ExamAttempt.user_id == user_id,
            ExamPaper.user_id == user_id,
            ExamPaper.course_id == course_id,
        )
    )


def mistakes_in_course(user_id, course_id):
    return select(Mistake.id).where(
        Mistake.user_id == user_id,
        Mistake.attempt_id.in_(attempts_in_course(user_id, course_id)),
    )


def course_exam_counts(db, user_id, course_id):
    counts = {
        key: db.scalar(
            select(func.count())
            .select_from(model)
            .where(model.user_id == user_id, model.course_id == course_id)
        )
        for key, model in (("past_papers", PastPaper), ("exam_papers", ExamPaper))
    }
    counts["attempts"] = db.scalar(
        select(func.count())
        .select_from(ExamAttempt)
        .where(ExamAttempt.id.in_(attempts_in_course(user_id, course_id)))
    )
    counts["review_tasks"] = db.scalar(
        select(func.count())
        .select_from(ReviewTask)
        .where(
            ReviewTask.user_id == user_id,
            ReviewTask.mistake_id.in_(mistakes_in_course(user_id, course_id)),
        )
    )
    return counts


def retire_course_exams(db, user_id, course_id):
    db.execute(
        delete(ReviewTask)
        .where(
            ReviewTask.user_id == user_id,
            ReviewTask.mistake_id.in_(mistakes_in_course(user_id, course_id)),
        )
        .execution_options(synchronize_session=False)
    )
    # Deleting these roots cascades questions, attempts and mistakes under existing FKs.
    for model in (ExamPaper, ExamBlueprint, PastPaper, Topic):
        db.execute(
            delete(model)
            .where(model.user_id == user_id, model.course_id == course_id)
            .execution_options(synchronize_session=False)
        )
