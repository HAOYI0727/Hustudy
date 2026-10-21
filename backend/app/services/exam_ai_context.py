"""M4-owned read-only bridge for M2. No commits, generation or status changes."""

from .topic_tree import active_clause
from fastapi import HTTPException
from sqlalchemy import select
from ..models import Topic, PastPaper, PastQuestion
from .courses import owned_course


def candidate_context(db, user_id, course_id, topic_ids=None, reference_ids=None):
    owned_course(db, user_id, course_id)
    topics = select(Topic).where(
        active_clause(), Topic.user_id == user_id, Topic.course_id == course_id
    )
    questions = (
        select(PastQuestion, PastPaper)
        .join(PastPaper)
        .where(
            PastQuestion.user_id == user_id,
            PastPaper.user_id == user_id,
            PastPaper.course_id == course_id,
            PastPaper.review_status == "CONFIRMED",
            PastQuestion.status == "CONFIRMED",
        )
    )
    if topic_ids is not None:
        topics = topics.where(Topic.id.in_(topic_ids))
    if reference_ids is not None:
        questions = questions.where(PastQuestion.id.in_(reference_ids))
    topic_rows = db.scalars(topics.order_by(Topic.id).limit(200)).all()
    question_rows = db.execute(questions.order_by(PastQuestion.id).limit(100)).all()
    if topic_ids is not None and len(topic_rows) != len(set(topic_ids)):
        raise HTTPException(404, "目标Topic不存在或不属于当前课程")
    if reference_ids is not None and len(question_rows) != len(set(reference_ids)):
        raise HTTPException(404, "参考原题不存在、未确认或不属于当前课程")
    references = []
    budget = 6000
    for question, paper in question_rows:
        # List endpoints return bounded summaries; snapshot selection never truncates silently.
        if reference_ids is not None and (
            len(question.stem) > 2000 or len(question.stem) > budget
        ):
            raise HTTPException(
                422, "参考原题超出6000字符预算，请减少原题或先在M4校正拆题"
            )
        references.append(
            {
                "id": question.id,
                "paper_id": paper.id,
                "title": paper.title,
                "year": paper.year,
                "stem": question.stem
                if reference_ids is not None
                else question.stem[:200],
                "topic_id": question.topic_id,
            }
        )
        budget -= len(question.stem)
    return {
        "topics": [{"id": t.id, "name": t.name} for t in topic_rows],
        "references": references,
    }


def validate_candidate_context(db, user_id, course_id, snapshot):
    current = candidate_context(
        db,
        user_id,
        course_id,
        [t["id"] for t in snapshot["topics"]],
        [q["id"] for q in snapshot["references"]],
    )
    if current != snapshot:
        raise HTTPException(409, "目标Topic或参考原题已变化，请重新预览确认")


def to_exam_enums(question_type, mode):
    """Explicit legacy naming bridge; final blueprint/state checks remain M4's job."""
    return (
        "true_false" if question_type == "boolean" else question_type,
        {
            "historical": "history_blueprint",
            "variant": "topic_variant",
            "weakness": "weakness_practice",
        }[mode],
    )
