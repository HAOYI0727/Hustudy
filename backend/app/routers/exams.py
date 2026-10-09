import hashlib
import json
import re
from datetime import date
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..dependencies import current_user
from ..models import (Course, ExamAttempt, ExamBlueprint, ExamPaper, Feedback, Mistake, PastPaper, PastQuestion,
                      ReviewTask, Topic, User)
from ..schemas.exams import (AnswerRequest, AttemptResponse, BlueprintCreate, BlueprintResponse, FeedbackCreate,
                             PaperResponse, PastPaperCreate, PastPaperResponse, PastQuestionResponse, ReviewTaskCreate,
                             ReviewTaskResponse, TopicCreate, TopicResponse)

router = APIRouter(prefix="/api/v1", tags=["exams"])


def _course(course_id: str, user: User, db: Session) -> Course:
    course = db.scalar(select(Course).where(Course.id == course_id, Course.user_id == user.id))
    if not course: raise HTTPException(status_code=404, detail="课程不存在")
    return course


def _topic_response(topic: Topic) -> TopicResponse:
    return TopicResponse(id=topic.id, name=topic.name, aliases=json.loads(topic.aliases_json))


@router.get("/courses/{course_id}/topics", response_model=List[TopicResponse])
def list_topics(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[TopicResponse]:
    _course(course_id, user, db)
    return [_topic_response(x) for x in db.scalars(select(Topic).where(Topic.course_id == course_id, Topic.user_id == user.id).order_by(Topic.name)).all()]


@router.post("/courses/{course_id}/topics", response_model=TopicResponse, status_code=201)
def create_topic(course_id: str, payload: TopicCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> TopicResponse:
    _course(course_id, user, db)
    topic = Topic(user_id=user.id, course_id=course_id, name=payload.name, aliases_json=json.dumps(payload.aliases, ensure_ascii=False))
    db.add(topic); db.commit(); db.refresh(topic); return _topic_response(topic)


@router.post("/courses/{course_id}/past-papers", response_model=PastPaperResponse, status_code=201)
def create_paper(course_id: str, payload: PastPaperCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> PastPaperResponse:
    _course(course_id, user, db)
    digest = hashlib.sha256(payload.content.encode()).hexdigest()
    existing = db.scalar(select(PastPaper).where(PastPaper.course_id == course_id, PastPaper.user_id == user.id, PastPaper.content_hash == digest))
    if existing: return _paper_response(existing, db)
    paper = PastPaper(user_id=user.id, course_id=course_id, title=payload.title, year=payload.year, content=payload.content, content_hash=digest)
    db.add(paper); db.commit(); db.refresh(paper); return _paper_response(paper, db)


def _paper_response(paper: PastPaper, db: Session) -> PastPaperResponse:
    questions = db.scalars(select(PastQuestion).where(PastQuestion.paper_id == paper.id).order_by(PastQuestion.number)).all()
    return PastPaperResponse(id=paper.id, title=paper.title, year=paper.year, review_status=paper.review_status, questions=[PastQuestionResponse.model_validate(q, from_attributes=True) for q in questions])


@router.get("/courses/{course_id}/past-papers", response_model=List[PastPaperResponse])
def list_papers(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[PastPaperResponse]:
    _course(course_id, user, db)
    return [_paper_response(p, db) for p in db.scalars(select(PastPaper).where(PastPaper.course_id == course_id, PastPaper.user_id == user.id).order_by(PastPaper.year.desc())).all()]


@router.post("/past-papers/{paper_id}/extract", response_model=PastPaperResponse)
def extract_paper(paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> PastPaperResponse:
    paper = db.scalar(select(PastPaper).where(PastPaper.id == paper_id, PastPaper.user_id == user.id))
    if not paper: raise HTTPException(status_code=404, detail="试卷不存在")
    if not paper.content.strip(): raise HTTPException(status_code=422, detail="试卷没有可拆分文本")
    for old in db.scalars(select(PastQuestion).where(PastQuestion.paper_id == paper.id)).all(): db.delete(old)
    lines = [line.strip() for line in paper.content.splitlines() if line.strip()]
    stems = []
    for line in lines:
        match = re.match(r"(?:第\s*)?([0-9]+)[.、)）]\s*(.+)", line)
        if match: stems.append((match.group(1), match.group(2)))
    if not stems: stems = [(str(i + 1), line) for i, line in enumerate(lines[:50])]
    for number, stem in stems:
        db.add(PastQuestion(user_id=user.id, paper_id=paper.id, number=number, stem=stem, question_type="short_answer", answer_source="unknown"))
    db.commit(); return _paper_response(paper, db)


@router.post("/past-papers/{paper_id}/confirm", response_model=PastPaperResponse)
def confirm_paper(paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> PastPaperResponse:
    paper = db.scalar(select(PastPaper).where(PastPaper.id == paper_id, PastPaper.user_id == user.id))
    if not paper: raise HTTPException(status_code=404, detail="试卷不存在")
    questions = db.scalars(select(PastQuestion).where(PastQuestion.paper_id == paper.id)).all()
    if not questions: raise HTTPException(status_code=422, detail="请先拆分题目")
    for q in questions: q.status = "CONFIRMED"
    paper.review_status = "CONFIRMED"; db.commit(); return _paper_response(paper, db)


@router.post("/exam-blueprints", response_model=BlueprintResponse, status_code=201)
def create_blueprint(payload: BlueprintCreate, course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> BlueprintResponse:
    _course(course_id, user, db)
    total = sum(int(item.get("count", 0)) * int(item.get("points", 0)) for item in payload.question_types)
    count = sum(int(item.get("count", 0)) for item in payload.question_types)
    if count <= 0 or total != payload.total_points:
        raise HTTPException(status_code=422, detail={"message": "蓝图数量或总分不一致", "computed_points": total, "computed_count": count})
    config = payload.model_dump(); blueprint = ExamBlueprint(user_id=user.id, course_id=course_id, name=payload.name, config_json=json.dumps(config, ensure_ascii=False))
    db.add(blueprint); db.commit(); db.refresh(blueprint); return BlueprintResponse(id=blueprint.id, name=blueprint.name, config=config, status=blueprint.status)


def _paper_payload(paper: ExamPaper, include_answers: bool = False) -> PaperResponse:
    questions = json.loads(paper.questions_json)
    if not include_answers:
        questions = [{k: v for k, v in question.items() if k not in {"answer", "rubric", "explanation"}} for question in questions]
    return PaperResponse(id=paper.id, title=paper.title, mode=paper.mode, status=paper.status, questions=questions)


@router.post("/exam-blueprints/{blueprint_id}/generate", response_model=PaperResponse, status_code=201)
def generate_paper(blueprint_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> PaperResponse:
    blueprint = db.scalar(select(ExamBlueprint).where(ExamBlueprint.id == blueprint_id, ExamBlueprint.user_id == user.id))
    if not blueprint: raise HTTPException(status_code=404, detail="蓝图不存在")
    config = json.loads(blueprint.config_json); topic_names = [x.get("name", "未指定章节") for x in config.get("topics", [])] or ["综合"]
    questions = []; index = 0
    for item in config["question_types"]:
        kind, count, points = item.get("type", "short_answer"), int(item["count"]), int(item["points"])
        for _ in range(count):
            index += 1; qid = str(uuid4()); topic = topic_names[(index - 1) % len(topic_names)]
            if kind in {"single_choice", "choice"}:
                question = {"id": qid, "type": "single_choice", "stem": f"【演示题】请结合“{topic}”选择最符合课件的表述。", "options": ["定义与条件均符合", "只符合名称", "与资料无关", "无法判断"], "answer": "A", "explanation": "演示模型题目，需由用户结合课件审阅。"}
            elif kind == "true_false":
                question = {"id": qid, "type": "true_false", "stem": f"【演示题】“{topic}”中的概念需要结合资料中的条件判断。", "answer": True, "explanation": "演示模型题目，需由用户审阅。"}
            else:
                question = {"id": qid, "type": "short_answer", "stem": f"请用自己的话解释“{topic}”，并给出一个应用场景。", "rubric": ["概念准确", "解释条件", "应用示例"], "answer": "参考要点需由用户结合课程资料审阅。", "explanation": "主观题仅提供 rubric 和演示参考。"}
            question.update({"points": points, "topic": topic, "difficulty_label": item.get("difficulty", "基础"), "material_citation_ids": [], "generation_status": "AI_DRAFT"})
            questions.append(question)
    paper = ExamPaper(user_id=user.id, course_id=blueprint.course_id, blueprint_id=blueprint.id, title=blueprint.name + "（草稿）", mode=config.get("mode", "history_blueprint"), questions_json=json.dumps(questions, ensure_ascii=False))
    db.add(paper); db.commit(); db.refresh(paper); return _paper_payload(paper, include_answers=True)


@router.get("/exam-papers/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: str, include_answers: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)) -> PaperResponse:
    paper = db.scalar(select(ExamPaper).where(ExamPaper.id == paper_id, ExamPaper.user_id == user.id))
    if not paper: raise HTTPException(status_code=404, detail="试卷不存在")
    return _paper_payload(paper, include_answers=include_answers)


@router.post("/exam-papers/{paper_id}/review", response_model=PaperResponse)
def review_paper(paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> PaperResponse:
    paper = db.scalar(select(ExamPaper).where(ExamPaper.id == paper_id, ExamPaper.user_id == user.id))
    if not paper: raise HTTPException(status_code=404, detail="试卷不存在")
    paper.status = "READY"; paper.title = paper.title.replace("（草稿）", ""); db.commit(); return _paper_payload(paper, include_answers=True)


def _attempt_response(attempt: ExamAttempt) -> AttemptResponse:
    return AttemptResponse(id=attempt.id, paper_id=attempt.paper_id, status=attempt.status, answers=json.loads(attempt.answers_json), score=attempt.score)


@router.post("/exam-papers/{paper_id}/attempts", response_model=AttemptResponse, status_code=201)
def start_attempt(paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> AttemptResponse:
    paper = db.scalar(select(ExamPaper).where(ExamPaper.id == paper_id, ExamPaper.user_id == user.id, ExamPaper.status == "READY"))
    if not paper: raise HTTPException(status_code=422, detail="试卷尚未审阅确认")
    existing = db.scalar(select(ExamAttempt).where(ExamAttempt.paper_id == paper_id, ExamAttempt.user_id == user.id, ExamAttempt.status == "IN_PROGRESS"))
    if existing: return _attempt_response(existing)
    attempt = ExamAttempt(user_id=user.id, paper_id=paper_id, answers_json="{}")
    db.add(attempt); db.commit(); db.refresh(attempt); return _attempt_response(attempt)


@router.put("/attempts/{attempt_id}/answers/{question_id}", response_model=AttemptResponse)
def save_answer(attempt_id: str, question_id: str, payload: AnswerRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> AttemptResponse:
    attempt = db.scalar(select(ExamAttempt).where(ExamAttempt.id == attempt_id, ExamAttempt.user_id == user.id))
    if not attempt: raise HTTPException(status_code=404, detail="答题记录不存在")
    if attempt.status != "IN_PROGRESS": raise HTTPException(status_code=409, detail="作答已提交，不能继续修改")
    answers = json.loads(attempt.answers_json); answers[question_id] = payload.answer; attempt.answers_json = json.dumps(answers, ensure_ascii=False); db.commit(); db.refresh(attempt); return _attempt_response(attempt)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResponse)
def submit_attempt(attempt_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> AttemptResponse:
    attempt = db.scalar(select(ExamAttempt).where(ExamAttempt.id == attempt_id, ExamAttempt.user_id == user.id))
    if not attempt: raise HTTPException(status_code=404, detail="答题记录不存在")
    if attempt.status != "IN_PROGRESS": return _attempt_response(attempt)
    paper = db.get(ExamPaper, attempt.paper_id); questions = json.loads(paper.questions_json); answers = json.loads(attempt.answers_json); score = 0
    for question in questions:
        if question["id"] not in answers: continue
        correct = question.get("answer"); given = answers[question["id"]]
        ok = (str(given).strip().upper() == str(correct).strip().upper())
        if ok: score += int(question.get("points", 0))
        elif question["type"] in {"single_choice", "true_false"}:
            db.add(Mistake(user_id=user.id, attempt_id=attempt.id, question_id=question["id"], detail_json=json.dumps({"question": question, "given": given}, ensure_ascii=False)))
    attempt.score = score; attempt.status = "SCORED"; db.commit(); db.refresh(attempt); return _attempt_response(attempt)


@router.get("/mistakes")
def list_mistakes(user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return [{"id": m.id, "question_id": m.question_id, **json.loads(m.detail_json)} for m in db.scalars(select(Mistake).where(Mistake.user_id == user.id).order_by(Mistake.created_at.desc())).all()]


@router.post("/review-tasks", response_model=ReviewTaskResponse, status_code=201)
def create_review_task(payload: ReviewTaskCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ReviewTaskResponse:
    if payload.mistake_id and not db.scalar(select(Mistake).where(Mistake.id == payload.mistake_id, Mistake.user_id == user.id)):
        raise HTTPException(status_code=404, detail="错题不存在")
    if payload.mistake_id and db.scalar(select(ReviewTask).where(ReviewTask.mistake_id == payload.mistake_id, ReviewTask.user_id == user.id, ReviewTask.status == "PENDING")):
        raise HTTPException(status_code=409, detail="该错题已有待复习任务")
    task = ReviewTask(user_id=user.id, mistake_id=payload.mistake_id, title=payload.title, due_date=payload.due_date.isoformat()); db.add(task); db.commit(); db.refresh(task)
    return ReviewTaskResponse.model_validate(task, from_attributes=True)


@router.get("/review-tasks/today", response_model=List[ReviewTaskResponse])
def today_tasks(user: User = Depends(current_user), db: Session = Depends(get_db)) -> List[ReviewTaskResponse]:
    return [ReviewTaskResponse.model_validate(x, from_attributes=True) for x in db.scalars(select(ReviewTask).where(ReviewTask.user_id == user.id, ReviewTask.due_date <= date.today().isoformat(), ReviewTask.status == "PENDING").order_by(ReviewTask.due_date)).all()]


@router.post("/review-tasks/{task_id}/complete", response_model=ReviewTaskResponse)
def complete_task(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ReviewTaskResponse:
    task = db.scalar(select(ReviewTask).where(ReviewTask.id == task_id, ReviewTask.user_id == user.id))
    if not task: raise HTTPException(status_code=404, detail="复习任务不存在")
    task.status = "COMPLETED"; db.commit(); db.refresh(task); return ReviewTaskResponse.model_validate(task, from_attributes=True)


@router.post("/feedback", status_code=201)
def feedback(payload: FeedbackCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Dict[str, str]:
    row = Feedback(user_id=user.id, kind=payload.kind, content=payload.content, rating=payload.rating); db.add(row); db.commit(); return {"id": row.id, "status": "received"}
