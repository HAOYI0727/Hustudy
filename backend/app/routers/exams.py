from ..services.topic_tree import active_clause
import hashlib
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..dependencies import current_user
from ..models import (
    Course,
    ExamAttempt,
    ExamBlueprint,
    ExamPaper,
    Feedback,
    Mistake,
    PastPaper,
    PastQuestion,
    ReviewTask,
    Topic,
    User,
)
from ..schemas.exams import (
    AnswerRequest,
    AttemptResponse,
    BlueprintCreate,
    BlueprintResponse,
    FeedbackCreate,
    PaperResponse,
    PastPaperCreate,
    PastPaperResponse,
    PastQuestionResponse,
    ReviewTaskCreate,
    ReviewTaskResponse,
    ReviewReschedule,
    TopicCreate,
    TopicResponse,
)

from ..services.exam_retirement import check_attempt_course, check_mistake_course
from ..services.courses import owned_course
from ..services import question_bank as bank
from ..services import topic_tree
from ..services.mistake_progress import mastered_since

router = APIRouter(prefix="/api/v1", tags=["exams"])


def _course(course_id: str, user: User, db: Session, *, lock=False) -> Course:
    return owned_course(db, user.id, course_id, lock=lock)


def _topic_response(topic: Topic) -> TopicResponse:
    return TopicResponse(
        id=topic.id,
        name=topic.name,
        aliases=json.loads(topic.aliases_json),
        revision=topic.revision,
        merged_into_id=topic.merged_into_id,
        parent_id=topic_tree.parent_id(topic),
    )


@router.get("/courses/{course_id}/topics", response_model=List[TopicResponse])
def list_topics(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> List[TopicResponse]:
    _course(course_id, user, db)
    return [
        _topic_response(x)
        for x in db.scalars(
            select(Topic)
            .where(
                Topic.course_id == course_id,
                active_clause(),
                Topic.user_id == user.id,
                Topic.merged_into_id.is_(None),
            )
            .order_by(Topic.name)
        ).all()
    ]


@router.post(
    "/courses/{course_id}/topics", response_model=TopicResponse, status_code=201
)
def create_topic(
    course_id: str,
    payload: TopicCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> TopicResponse:
    _course(course_id, user, db, lock=True)
    topic = Topic(
        user_id=user.id,
        course_id=course_id,
        name=payload.name,
        aliases_json=json.dumps(payload.aliases, ensure_ascii=False),
    )
    db.add(topic)
    db.flush()
    topic_tree.check_parent(
        db,
        user.id,
        course_id,
        topic.id,
        str(payload.parent_id) if payload.parent_id else None,
    )
    topic_tree.write_parent(
        topic, str(payload.parent_id) if payload.parent_id else None
    )
    db.commit()
    db.refresh(topic)
    return _topic_response(topic)


@router.post(
    "/courses/{course_id}/past-papers",
    response_model=PastPaperResponse,
    status_code=201,
)
def create_paper(
    course_id: str,
    payload: PastPaperCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PastPaperResponse:
    _course(course_id, user, db, lock=True)
    bank.no_active_attempt(db, user.id, course_id)
    digest = hashlib.sha256(payload.content.encode()).hexdigest()
    existing = db.scalar(
        select(PastPaper).where(
            PastPaper.course_id == course_id,
            PastPaper.user_id == user.id,
            PastPaper.content_hash == digest,
        )
    )
    if existing:
        return _paper_response(existing, db)
    paper = PastPaper(
        user_id=user.id,
        course_id=course_id,
        title=payload.title,
        year=payload.year,
        content=payload.content,
        content_hash=digest,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return _paper_response(paper, db)


def _paper_response(paper: PastPaper, db: Session) -> PastPaperResponse:
    questions = db.scalars(
        select(PastQuestion)
        .where(PastQuestion.paper_id == paper.id)
        .order_by(PastQuestion.number)
    ).all()
    return PastPaperResponse(
        id=paper.id,
        title=paper.title,
        year=paper.year,
        review_status=paper.review_status,
        questions=[PastQuestionResponse(**bank.question_payload(q)) for q in questions],
    )


@router.get("/courses/{course_id}/past-papers", response_model=List[PastPaperResponse])
def list_papers(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> List[PastPaperResponse]:
    _course(course_id, user, db)
    bank.no_active_attempt(db, user.id, course_id)
    return [
        _paper_response(p, db)
        for p in db.scalars(
            select(PastPaper)
            .where(PastPaper.course_id == course_id, PastPaper.user_id == user.id)
            .order_by(PastPaper.year.desc())
        ).all()
    ]


@router.post("/past-papers/{paper_id}/extract", response_model=PastPaperResponse)
def extract_paper(
    paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> PastPaperResponse:
    paper = db.scalar(
        select(PastPaper).where(PastPaper.id == paper_id, PastPaper.user_id == user.id)
    )
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    _course(paper.course_id, user, db, lock=True)
    bank.no_active_attempt(db, user.id, paper.course_id)
    if db.scalar(
        select(PastQuestion.id).where(PastQuestion.paper_id == paper.id).limit(1)
    ):
        return _paper_response(paper, db)
    if not paper.content.strip():
        raise HTTPException(status_code=422, detail="试卷没有可拆分文本")
    for old in db.scalars(
        select(PastQuestion).where(PastQuestion.paper_id == paper.id)
    ).all():
        db.delete(old)
    lines = [line.strip() for line in paper.content.splitlines() if line.strip()]
    stems = []
    for line in lines:
        match = re.match(r"(?:第\s*)?([0-9]+)[.、)）]\s*(.+)", line)
        if match:
            stems.append((match.group(1), match.group(2)))
    if not stems:
        stems = [(str(i + 1), line) for i, line in enumerate(lines[:50])]
    for number, stem in stems:
        db.add(
            PastQuestion(
                user_id=user.id,
                paper_id=paper.id,
                number=number,
                stem=stem,
                question_type="short_answer",
                answer_source="unknown",
            )
        )
    db.commit()
    return _paper_response(paper, db)


@router.post("/past-papers/{paper_id}/confirm", response_model=PastPaperResponse)
def confirm_paper(
    paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> PastPaperResponse:
    paper = db.scalar(
        select(PastPaper).where(PastPaper.id == paper_id, PastPaper.user_id == user.id)
    )
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    _course(paper.course_id, user, db, lock=True)
    questions = db.scalars(
        select(PastQuestion).where(
            PastQuestion.paper_id == paper.id, PastQuestion.status != "SUPERSEDED"
        )
    ).all()
    if not questions:
        raise HTTPException(status_code=422, detail="请先拆分题目")
    bank.no_active_attempt(db, user.id, paper.course_id)
    errors = {
        q.id: bank.validate_question(q, json.loads(q.bank_data_json))
        for q in questions
        if q.bank_data_json != "{}"
    }
    errors = {qid: value for qid, value in errors.items() if value}
    if errors:
        raise HTTPException(422, {"message": "题库仍有待校正题目", "questions": errors})
    from ..services.bank_images import check_images

    for q in questions:
        check_images(
            db,
            user.id,
            paper.course_id,
            json.loads(q.bank_data_json).get("illustrations", []),
        )
        q.status = "CONFIRMED"
    paper.review_status = "CONFIRMED"
    db.commit()
    return _paper_response(paper, db)


@router.post("/exam-blueprints", response_model=BlueprintResponse, status_code=201)
def create_blueprint(
    payload: BlueprintCreate,
    course_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> BlueprintResponse:
    _course(course_id, user, db, lock=True)
    total = sum(item.count * item.points for item in payload.question_types)
    count = sum(item.count for item in payload.question_types)
    if count <= 0 or total != payload.total_points:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "蓝图数量或总分不一致",
                "computed_points": total,
                "computed_count": count,
            },
        )
    if count > 100 or (
        payload.topics and sum(chapter.count for chapter in payload.topics) != count
    ):
        raise HTTPException(422, "章节配额必须与总题数一致，且最多 100 题")
    if len({item.type for item in payload.question_types}) != len(
        payload.question_types
    ):
        raise HTTPException(422, "题型配额不能重复")
    config = payload.model_dump()
    blueprint = ExamBlueprint(
        user_id=user.id,
        course_id=course_id,
        name=payload.name,
        config_json=json.dumps(config, ensure_ascii=False),
    )
    db.add(blueprint)
    db.commit()
    db.refresh(blueprint)
    return BlueprintResponse(
        id=blueprint.id, name=blueprint.name, config=config, status=blueprint.status
    )


def _paper_payload(paper: ExamPaper, include_answers: bool = False) -> PaperResponse:
    questions = json.loads(paper.questions_json)
    if not include_answers:
        questions = [bank.public_question(q) for q in questions]
    return PaperResponse(
        id=paper.id,
        title=paper.title,
        mode=paper.mode,
        status=paper.status,
        questions=questions,
    )


@router.post(
    "/exam-blueprints/{blueprint_id}/generate",
    response_model=PaperResponse,
    status_code=201,
)
def generate_paper(
    blueprint_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> PaperResponse:
    blueprint = db.scalar(
        select(ExamBlueprint).where(
            ExamBlueprint.id == blueprint_id, ExamBlueprint.user_id == user.id
        )
    )
    if not blueprint:
        raise HTTPException(status_code=404, detail="蓝图不存在")
    _course(blueprint.course_id, user, db, lock=True)
    return _paper_payload(bank.generate_blueprint(db, user.id, blueprint))


@router.get("/exam-papers/{paper_id}", response_model=PaperResponse)
def get_paper(
    paper_id: str,
    include_answers: bool = False,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> PaperResponse:
    paper = db.scalar(
        select(ExamPaper).where(ExamPaper.id == paper_id, ExamPaper.user_id == user.id)
    )
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    _course(paper.course_id, user, db)
    if include_answers:
        bank.no_active_attempt(db, user.id, paper.course_id)
        active = db.scalar(
            select(ExamAttempt.id).where(
                ExamAttempt.paper_id == paper.id,
                ExamAttempt.user_id == user.id,
                ExamAttempt.status == "IN_PROGRESS",
            )
        )
        if active:
            raise HTTPException(409, "作答中不能读取答案；提交后查看结果")
    return _paper_payload(paper, include_answers=include_answers)


@router.post("/exam-papers/{paper_id}/review", response_model=PaperResponse)
def review_paper(
    paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> PaperResponse:
    paper = db.scalar(
        select(ExamPaper).where(ExamPaper.id == paper_id, ExamPaper.user_id == user.id)
    )
    if not paper:
        raise HTTPException(status_code=404, detail="试卷不存在")
    _course(paper.course_id, user, db, lock=True)
    bank.no_active_attempt(db, user.id, paper.course_id)
    if paper.status not in {"DRAFT", "REVIEWED", "READY"}:
        raise HTTPException(409, "当前试卷不能审阅")
    bank.require_source_valid(
        db, user.id, paper.course_id, json.loads(paper.questions_json)
    )
    if paper.status == "READY":
        return _paper_payload(paper)
    paper.status = "REVIEWED"
    db.flush()
    paper.status = "READY"
    paper.title = paper.title.replace("（草稿）", "")
    db.commit()
    return _paper_payload(paper)


def _attempt_response(attempt: ExamAttempt) -> AttemptResponse:
    return AttemptResponse(
        id=attempt.id,
        paper_id=attempt.paper_id,
        status=attempt.status,
        answers=json.loads(attempt.answers_json),
        score=attempt.score,
        grading=json.loads(attempt.grading_json),
    )


@router.post(
    "/exam-papers/{paper_id}/attempts", response_model=AttemptResponse, status_code=201
)
def start_attempt(
    paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> AttemptResponse:
    paper = db.scalar(
        select(ExamPaper).where(
            ExamPaper.id == paper_id,
            ExamPaper.user_id == user.id,
            ExamPaper.status == "READY",
        )
    )
    if not paper:
        raise HTTPException(status_code=404, detail="可作答试卷不存在")
    _course(paper.course_id, user, db, lock=True)
    blueprint = db.get(ExamBlueprint, paper.blueprint_id)
    return _attempt_response(bank.new_attempt(db, user.id, paper, blueprint))


@router.put(
    "/attempts/{attempt_id}/answers/{question_id}", response_model=AttemptResponse
)
def save_answer(
    attempt_id: str,
    question_id: str,
    payload: AnswerRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> AttemptResponse:
    check_attempt_course(db, user.id, attempt_id, lock=True)
    attempt = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.id == attempt_id, ExamAttempt.user_id == user.id
        )
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="答题记录不存在")
    if attempt.status != "IN_PROGRESS":
        raise HTTPException(status_code=409, detail="作答已提交，不能继续修改")
    locked = db.execute(
        update(ExamAttempt)
        .where(ExamAttempt.id == attempt.id, ExamAttempt.status == "IN_PROGRESS")
        .values(status=ExamAttempt.status)
    )
    if locked.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "作答已提交，不能继续修改")
    db.refresh(attempt)
    paper = db.get(ExamPaper, attempt.paper_id)
    blueprint = db.get(ExamBlueprint, paper.blueprint_id)
    snapshot = bank.attempt_snapshot(attempt, paper, blueprint)
    if bank.is_expired(attempt, snapshot):
        raise HTTPException(409, "作答时限已到，请提交已保存答案")
    question = next((q for q in snapshot["questions"] if q["id"] == question_id), None)
    if not question:
        raise HTTPException(404, "题目不属于此试卷")
    if question["type"] == "single_choice" and payload.answer not in [
        chr(65 + i) for i in range(len(question.get("options", [])))
    ]:
        raise HTTPException(422, "选择题答案必须为合法选项")
    if question["type"] == "true_false" and not isinstance(payload.answer, bool):
        raise HTTPException(422, "判断题答案必须为布尔值")
    if question["type"] in {"short_answer", "solution"} and (
        not isinstance(payload.answer, str) or len(payload.answer) > 20000
    ):
        raise HTTPException(422, "简答题答案需为不超过 20000 字符的文本")
    if question["type"] == "fill_blank":
        expected = question["blank_count"]
        actual = (
            [payload.answer]
            if isinstance(payload.answer, str) and expected == 1
            else payload.answer
        )
        if (
            not isinstance(actual, list)
            or len(actual) != expected
            or any(not isinstance(v, str) or len(v) > 20000 for v in actual)
        ):
            raise HTTPException(422, "填空答案应与空位数量一致，每空不超过20000字符")
    if question["type"] == "fill_blank" and question.get("unique_answer"):
        grades = json.loads(attempt.grading_json)
        grades[question_id] = bank.grade(question, payload.answer)
        attempt.grading_json = bank.encode(grades)
    answers = json.loads(attempt.answers_json)
    answers[question_id] = payload.answer
    attempt.answers_json = json.dumps(answers, ensure_ascii=False)
    db.commit()
    db.refresh(attempt)
    return _attempt_response(attempt)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResponse)
def submit_attempt(
    attempt_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> AttemptResponse:
    check_attempt_course(db, user.id, attempt_id, lock=True)
    attempt = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.id == attempt_id, ExamAttempt.user_id == user.id
        )
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="答题记录不存在")
    if attempt.status != "IN_PROGRESS":
        return _attempt_response(attempt)
    locked = db.execute(
        update(ExamAttempt)
        .where(ExamAttempt.id == attempt.id, ExamAttempt.status == "IN_PROGRESS")
        .values(status="SUBMITTED")
    )
    if locked.rowcount != 1:
        db.rollback()
        db.refresh(attempt)
        return _attempt_response(attempt)
    db.refresh(attempt)
    paper = db.get(ExamPaper, attempt.paper_id)
    blueprint = db.get(ExamBlueprint, paper.blueprint_id)
    questions = bank.submitted_questions(attempt, paper, blueprint)
    bank.finish_grading(db, attempt, questions)
    db.commit()
    db.refresh(attempt)
    return _attempt_response(attempt)


@router.get("/attempts/{attempt_id}/result", response_model=PaperResponse)
def attempt_result(
    attempt_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    check_attempt_course(db, user.id, attempt_id)
    attempt = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.id == attempt_id, ExamAttempt.user_id == user.id
        )
    )
    if not attempt:
        raise HTTPException(404, "作答记录不存在")
    if attempt.status == "IN_PROGRESS":
        raise HTTPException(409, "提交后才能查看答案")
    paper = db.get(ExamPaper, attempt.paper_id)
    blueprint = db.get(ExamBlueprint, paper.blueprint_id)
    questions = bank.submitted_questions(attempt, paper, blueprint)
    return PaperResponse(
        id=paper.id,
        title=paper.title,
        mode=paper.mode,
        status=paper.status,
        questions=questions,
    )


@router.get("/mistakes")
def list_mistakes(
    topic_id: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    topics = {
        t.id: t
        for t in db.scalars(
            select(Topic).where(active_clause(), Topic.user_id == user.id)
        ).all()
    }

    def resolve(tid):
        seen = set()
        while tid in topics and topics[tid].merged_into_id and tid not in seen:
            seen.add(tid)
            tid = topics[tid].merged_into_id
        return topics.get(tid)

    selected = {topic_id} if topic_id else set()
    if topic_id in topics:
        selected = topic_tree.expand(db, user.id, topics[topic_id].course_id, selected)
    result = []
    for m in db.scalars(
        select(Mistake)
        .join(ExamAttempt, Mistake.attempt_id == ExamAttempt.id)
        .join(ExamPaper, ExamAttempt.paper_id == ExamPaper.id)
        .join(Course, ExamPaper.course_id == Course.id)
        .where(Mistake.user_id == user.id, Course.user_id == user.id, Course.deleted_at.is_(None))
        .order_by(Mistake.created_at.desc())
    ).all():
        detail = json.loads(m.detail_json)
        if detail.get("removed_from_bank"):
            continue
        mastered_at = mastered_since(detail)
        detail.pop("redoes", None)
        detail.pop("relapses", None)
        q = detail.get("question", {})
        labels = {}
        for tid in q.get("topic_ids", []) or (
            [q["topic_id"]] if q.get("topic_id") else []
        ):
            t = resolve(tid)
            if t:
                labels[t.id] = {
                    "id": t.id,
                    "name": t.name,
                    "aliases": json.loads(t.aliases_json),
                    "revision": t.revision,
                    "parent_id": topic_tree.parent_id(t),
                }
        ancestors = list(labels.values())
        for label in ancestors:
            current = topics.get(label["id"])
            seen = set()
            while current and topic_tree.parent_id(current) and current.id not in seen:
                seen.add(current.id)
                current = resolve(topic_tree.parent_id(current))
                if current:
                    labels[current.id] = {
                        "id": current.id,
                        "name": current.name,
                        "aliases": json.loads(current.aliases_json),
                        "revision": current.revision,
                        "parent_id": topic_tree.parent_id(current),
                    }
        if topic_id and not selected.intersection(labels):
            continue
        result.append(
            {
                "id": m.id,
                "question_id": m.question_id,
                **detail,
                "topics": list(labels.values()),
                "mastered": mastered_at is not None,
                "mastered_at": mastered_at.isoformat() if mastered_at else None,
            }
        )
    return sorted(result, key=lambda item: item["mastered"])


@router.post("/review-tasks", response_model=ReviewTaskResponse, status_code=201)
def create_review_task(
    payload: ReviewTaskCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ReviewTaskResponse:
    if payload.mistake_id:
        check_mistake_course(db, user.id, payload.mistake_id, lock=True)
    if payload.mistake_id and not db.scalar(
        select(Mistake).where(
            Mistake.id == payload.mistake_id, Mistake.user_id == user.id
        )
    ):
        raise HTTPException(status_code=404, detail="错题不存在")
    if payload.mistake_id and db.scalar(
        select(ReviewTask).where(
            ReviewTask.mistake_id == payload.mistake_id,
            ReviewTask.user_id == user.id,
            ReviewTask.status == "PENDING",
        )
    ):
        existing = db.scalar(
            select(ReviewTask).where(
                ReviewTask.mistake_id == payload.mistake_id,
                ReviewTask.user_id == user.id,
                ReviewTask.status == "PENDING",
            )
        )
        return ReviewTaskResponse.model_validate(existing, from_attributes=True)
    task = ReviewTask(
        user_id=user.id,
        mistake_id=payload.mistake_id,
        title=payload.title,
        due_date=(
            payload.due_date or datetime.now(ZoneInfo(user.timezone)).date()
        ).isoformat(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return ReviewTaskResponse.model_validate(task, from_attributes=True)


@router.get("/review-tasks/today", response_model=List[ReviewTaskResponse])
def today_tasks(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> List[ReviewTaskResponse]:
    return [
        ReviewTaskResponse.model_validate(x, from_attributes=True)
        for x in db.scalars(
            select(ReviewTask)
            .where(
                ReviewTask.user_id == user.id,
                ReviewTask.due_date
                <= datetime.now(ZoneInfo(user.timezone)).date().isoformat(),
                ReviewTask.status == "PENDING",
            )
            .order_by(ReviewTask.due_date)
        ).all()
    ]


@router.post("/review-tasks/{task_id}/complete", response_model=ReviewTaskResponse)
def complete_task(
    task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> ReviewTaskResponse:
    task = db.scalar(
        select(ReviewTask).where(
            ReviewTask.id == task_id, ReviewTask.user_id == user.id
        )
    )
    if not task:
        raise HTTPException(status_code=404, detail="复习任务不存在")
    if task.mistake_id:
        check_mistake_course(db, user.id, task.mistake_id, lock=True)
    task.status = "COMPLETED"
    db.commit()
    db.refresh(task)
    return ReviewTaskResponse.model_validate(task, from_attributes=True)


@router.patch("/review-tasks/{task_id}", response_model=ReviewTaskResponse)
def reschedule_review(
    task_id: str,
    payload: ReviewReschedule,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    task = db.scalar(
        select(ReviewTask).where(
            ReviewTask.id == task_id, ReviewTask.user_id == user.id
        )
    )
    if not task:
        raise HTTPException(404, "复习任务不存在")
    if task.mistake_id:
        check_mistake_course(db, user.id, task.mistake_id, lock=True)
    changed = db.execute(
        update(ReviewTask)
        .where(
            ReviewTask.id == task.id,
            ReviewTask.user_id == user.id,
            ReviewTask.due_date == payload.expected_due_date.isoformat(),
        )
        .values(due_date=payload.due_date.isoformat(), status="PENDING")
    )
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "复习日期已变化，请刷新后重新安排")
    db.commit()
    db.refresh(task)
    return ReviewTaskResponse.model_validate(task, from_attributes=True)


@router.post("/feedback", status_code=201)
def feedback(
    payload: FeedbackCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    row = Feedback(
        user_id=user.id,
        kind=payload.kind,
        content=payload.content,
        rating=payload.rating,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "status": "received"}
