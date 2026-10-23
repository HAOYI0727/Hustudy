"""User bank management and sampling, shared by M4 and the AI-study practice tab."""

import json
from ..services.topic_tree import active_clause
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..schemas.remote_ai import ConsentRequest
from ..models import (
    PastPaper,
    PastQuestion,
    ExamAttempt,
    ExamPaper,
    ExamBlueprint,
    Topic,
    User,
)
from ..schemas.exams import (
    BankImport,
    BankBatch,
    BankSave,
    BankImageImport,
    BankQuestionEdit,
    BankDraw,
    SelfGrade,
    PaperResponse,
)
from ..services import (
    question_bank as bank,
    bank_topic_ai,
    bank_pdf,
    bank_deletion,
    bank_library,
)
from ..services.courses import owned_course
from ..services.exam_retirement import check_attempt_course

router = APIRouter(prefix="/api/v1", tags=["question-bank"])


@router.post("/courses/{course_id}/question-bank/files", status_code=202)
def bank_upload(
    course_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.documents import save_upload
    from ..schemas.material import JobResponse

    owned_course(db, user.id, course_id)
    bank.no_active_attempt(db, user.id, course_id)
    try:
        _, _, job, _ = save_upload(
            file, course_id, user.id, db, library_scope="question_bank"
        )
        return JobResponse.model_validate(job, from_attributes=True)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    finally:
        file.file.close()


@router.get("/courses/{course_id}/question-bank/files")
def bank_files(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    from .documents import _document_response

    return [
        _document_response(d, db).model_dump() | {"library_scope": d.library_scope}
        for d in bank_library.rows(db, user.id, course_id)
    ]


@router.post("/courses/{course_id}/question-bank/files/{document_id}/move")
def move_bank_file(
    course_id: str,
    document_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return bank_library.move(db, user.id, course_id, document_id)


@router.post("/courses/{course_id}/question-bank/restore")
def restore_questions(
    course_id: str,
    payload: bank_deletion.Restore,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return bank_deletion.restore(db, user.id, course_id, payload)


@router.post("/past-papers/{paper_id}/delete")
def remove_bank_paper(
    paper_id: str,
    payload: bank_deletion.RemovePaper,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return bank_deletion.remove_paper(db, user.id, paper_id, payload)


@router.get("/courses/{course_id}/question-bank/pdf/{version_id}")
def pdf_inspect(
    course_id: str,
    version_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return bank_pdf.inspect(db, user.id, course_id, version_id)


@router.post("/courses/{course_id}/question-bank/pdf/{version_id}/ocr", status_code=202)
def pdf_ocr(
    course_id: str,
    version_id: str,
    payload: bank_pdf.Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return bank_pdf.enqueue(db, user.id, course_id, version_id, payload)


@router.post("/past-papers/{paper_id}/topic-ai-preview", status_code=201)
def topic_ai_preview(
    paper_id: str,
    payload: bank_topic_ai.PreviewRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return bank_topic_ai.preview(db, user.id, paper_id, payload.question_ids)


@router.get("/past-papers/{paper_id}/topic-ai-preview")
def topic_ai_detail(
    paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return bank_topic_ai.response(db, bank_topic_ai.owned_paper(db, user.id, paper_id))


@router.post("/past-papers/{paper_id}/topic-ai-confirm", status_code=202)
def topic_ai_confirm(
    paper_id: str,
    payload: bank_topic_ai.ConfirmRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return bank_topic_ai.confirm(db, user.id, paper_id, payload.preview_id)


@router.get("/question-bank/ai-capabilities")
def ai_capabilities(user: User = Depends(current_user)):
    from ..services.bank_ai import capabilities

    return capabilities()


@router.post("/courses/{course_id}/question-bank/ai-preview", status_code=201)
def ai_preview(
    course_id: str,
    payload: BankImport,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_ai import preview

    if not payload.version_id or payload.content:
        raise HTTPException(422, "AI识别请选择已经解析的资料版本")
    return preview(db, user.id, course_id, payload)


@router.post("/past-papers/{paper_id}/ai-confirm", status_code=202)
def ai_confirm(
    paper_id: str,
    payload: ConsentRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_ai import confirm

    return confirm(db, user.id, paper_id)


@router.get("/courses/{course_id}/question-bank/ai-jobs")
def ai_jobs(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    from ..services.bank_ai import response

    owned_course(db, user.id, course_id)
    bank.no_active_attempt(db, user.id, course_id)
    rows = db.scalars(
        select(PastPaper)
        .where(PastPaper.user_id == user.id, PastPaper.course_id == course_id)
        .order_by(PastPaper.created_at.desc())
    ).all()
    return [
        response(db, p, include_sources=False)
        for p in rows
        if "ai_extract" in json.loads(p.bank_meta_json)
        and not json.loads(p.bank_meta_json).get("deleted_by_user")
    ][:40]


@router.get("/past-papers/{paper_id}/ai-preview")
def ai_preview_detail(
    paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    from ..services.bank_ai import response

    paper = db.scalar(
        select(PastPaper).where(PastPaper.id == paper_id, PastPaper.user_id == user.id)
    )
    if not paper or "ai_extract" not in json.loads(paper.bank_meta_json):
        raise HTTPException(404, "预览不存在")
    owned_course(db, user.id, paper.course_id)
    bank.no_active_attempt(db, user.id, paper.course_id)
    return response(db, paper)


@router.post("/courses/{course_id}/question-bank/archives", status_code=201)
def archive_upload(
    course_id: str,
    file: UploadFile = File(...),
    selected_paths: str | None = Form(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_archives import import_archive, MAX_ZIP

    owned_course(db, user.id, course_id)
    try:
        try:
            chosen = json.loads(selected_paths) if selected_paths is not None else None
        except ValueError:
            raise HTTPException(422, "ZIP选择列表格式错误") from None
        if chosen is not None and (
            not isinstance(chosen, list) or any(not isinstance(n, str) for n in chosen)
        ):
            raise HTTPException(422, "ZIP选择列表格式错误")
        return import_archive(
            db, user.id, course_id, file.file.read(MAX_ZIP + 1), chosen
        )
    finally:
        file.file.close()


@router.get("/question-bank/illustrations/{asset_id}")
def illustration_pixels(
    asset_id: str,
    course_id: str,
    box: str = "0,0,1,1",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    import io
    from pathlib import Path
    from PIL import Image, ImageOps
    from fastapi.responses import Response
    from ..core.storage import get_storage
    from ..repositories.assets import active_asset
    from ..services.bank_images import check_images

    owned_course(db, user.id, course_id)
    try:
        region = [float(v) for v in box.split(",")]
    except ValueError:
        raise HTTPException(422, "裁剪区域格式不正确") from None
    check_images(db, user.id, course_id, [{"asset_id": asset_id, "box": region}])
    asset = active_asset(db, asset_id, user.id)
    path = get_storage().checked(Path(asset.storage_path))
    if not path.is_file():
        raise HTTPException(404, "原图片文件已不可用")
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    w, h = image.size
    x, y, width, height = region
    bounds = (
        int(x * w),
        int(y * h),
        min(w, max(int(x * w) + 1, int((x + width) * w))),
        min(h, max(int(y * h) + 1, int((y + height) * h))),
    )
    output = io.BytesIO()
    image.crop(bounds).save(output, format="PNG")
    return Response(
        output.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"}
    )


@router.delete("/past-questions/{question_id}")
def remove_question(
    question_id: str,
    revision: int = Query(ge=1),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return batch_questions_for_owner(
        db, user.id, [question_id], {question_id: revision}, "delete", []
    )


def batch_questions_for_owner(
    db, user_id, ids, revisions, action, topic_ids, course_id=None
):
    from ..services.bank_edits import owned_question, sync_review_status

    ids = [str(i) for i in ids]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "不能重复选择题目")
    rows = []
    for qid in ids:
        q, paper = owned_question(db, user_id, qid)
        if course_id and paper.course_id != course_id:
            raise HTTPException(404, "题目不属于当前课程")
        if revisions.get(q.id) != q.revision:
            raise HTTPException(409, "题目已经变化，请刷新后重新选择")
        if action in {"tag", "tag_add"}:
            bank.topic_rows(db, user_id, paper.course_id, topic_ids)
        rows.append((q, paper))
    if action == "confirm":
        from ..services.bank_images import check_images

        errors = {}
        for q, paper in rows:
            data = json.loads(q.bank_data_json)
            warnings = bank.validate_question(q, data)
            if warnings:
                errors[q.id] = warnings
            bank.topic_rows(db, user_id, paper.course_id, data.get("topic_ids", []))
            check_images(db, user_id, paper.course_id, data.get("illustrations", []))
            bank.require_source_valid(db, user_id, paper.course_id, [data])
        if errors:
            raise HTTPException(
                422,
                {
                    "message": "所选题目仍有待校正项，未核验任何题目",
                    "questions": errors,
                },
            )
    tags = {}
    overflow = []
    if action in {"tag", "tag_add"}:
        for q, paper in rows:
            data = json.loads(q.bank_data_json)
            existing = data.get("topic_ids", [q.topic_id] if q.topic_id else [])
            values = (existing if action == "tag_add" else []) + [
                str(t) for t in topic_ids
            ]
            tags[q.id] = list(dict.fromkeys(values))
            if len(tags[q.id]) > 5:
                overflow.append(
                    {
                        "question_id": q.id,
                        "paper_id": paper.id,
                        "paper_title": paper.title,
                        "number": q.number,
                        "tag_count": len(tags[q.id]),
                        "limit": 5,
                    }
                )
        if overflow:
            raise HTTPException(
                422,
                {
                    "message": "部分题目超过每题5个标签的上限，整批未修改；请减少标签或改用统一替换",
                    "limit": 5,
                    "over_limit_questions": overflow,
                },
            )
    # Validate the whole selection before writing any row.
    for q, paper in rows:
        data = json.loads(q.bank_data_json)
        if action == "confirm":
            q.status = "CONFIRMED"
        elif action == "delete":
            q.status = "SUPERSEDED"
            data["removed_by_user"] = True
        else:
            if data.get("topic_ids", []) != tags[q.id]:
                q.status = "DRAFT"
            data["topic_ids"] = tags[q.id]
            data["topic_index"] = data.get("topic_index", {}) | {
                "selection_reviewed": True
            }
            q.topic_id = data["topic_ids"][0] if data["topic_ids"] else None
        q.bank_data_json = bank.encode(data)
        q.revision += 1
    sync_review_status(db, [p for _, p in rows])
    db.commit()
    return {"changed": len(rows), "revisions": {q.id: q.revision for q, _ in rows}}


@router.post("/courses/{course_id}/question-bank/batch")
def batch_questions(
    course_id: str,
    payload: BankBatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned_course(db, user.id, course_id, lock=True)
    bank.no_active_attempt(db, user.id, course_id)
    return batch_questions_for_owner(
        db,
        user.id,
        payload.question_ids,
        payload.revisions,
        payload.action,
        payload.topic_ids,
        course_id,
    )


@router.post("/courses/{course_id}/question-bank/images", status_code=202)
def image_import(
    course_id: str,
    payload: BankImageImport,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_ocr import enqueue

    return enqueue(db, user.id, course_id, payload)


@router.get("/courses/{course_id}/question-bank/image-jobs")
def image_jobs(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    from ..services.bank_ocr import list_jobs

    owned_course(db, user.id, course_id)
    bank.no_active_attempt(db, user.id, course_id)
    return list_jobs(db, user.id, course_id)


@router.post("/courses/{course_id}/question-bank/import", status_code=201)
def import_questions(
    course_id: str,
    payload: BankImport,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    paper = bank.import_bank(db, user.id, course_id, payload)
    from .exams import _paper_response

    return _paper_response(paper, db)


@router.get("/courses/{course_id}/question-bank")
def list_questions(
    course_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    paper_id: str | None = None,
    topic_id: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned_course(db, user.id, course_id)
    bank.no_active_attempt(db, user.id, course_id)
    rows = db.scalars(
        select(PastQuestion)
        .join(PastPaper)
        .where(
            PastQuestion.user_id == user.id,
            PastPaper.user_id == user.id,
            PastPaper.course_id == course_id,
            PastQuestion.status != "SUPERSEDED",
            *([PastPaper.id == paper_id] if paper_id else []),
        )
        .order_by(
            PastPaper.created_at.desc(),
            PastPaper.id,
            PastQuestion.created_at,
            PastQuestion.id,
        )
    ).all()
    if topic_id:
        bank.topic_rows(db, user.id, course_id, [topic_id])
        from ..services.topic_tree import expand

        selected = expand(db, user.id, course_id, [topic_id])
        rows = [
            q
            for q in rows
            if selected.intersection(
                json.loads(q.bank_data_json).get("topic_ids", [q.topic_id])
            )
        ]
    from ..services.question_display import order_rows

    rows = order_rows(rows)
    items = []
    for q in rows[offset : offset + limit]:
        item = bank.question_payload(q) | {"paper_id": q.paper_id}
        if item["bank_data"].get("topic_index", {}).get("version") not in {
            "bank-topic-ai-v2",
            "bank-topic-ai-v3",
        }:
            item["bank_data"]["topic_index"] = {
                "version": bank_topic_ai.VERSION,
                "existing": [],
                "candidates": [],
            }
        items.append(item)
    return {
        "total": len(rows),
        "offset": offset,
        "limit": limit,
        "items": items,
    }


@router.get("/courses/{course_id}/question-directory")
def question_directory(
    course_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.question_directory import page

    return page(db, user.id, course_id, offset, limit)


@router.get("/past-questions/{question_id}")
def question_detail(
    question_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.question_directory import detail

    return detail(db, user.id, question_id)


@router.patch("/past-questions/{question_id}")
def edit_question(
    question_id: str,
    payload: BankQuestionEdit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_edits import save_question

    return save_question(db, user.id, question_id, payload)


@router.post("/courses/{course_id}/question-bank/save")
def save_selected_questions(
    course_id: str,
    payload: BankSave,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_edits import save_question

    owned_course(db, user.id, course_id, lock=True)
    ids = [str(item.question_id) for item in payload.items]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "不能重复选择题目")
    try:
        results = [
            save_question(
                db,
                user.id,
                str(item.question_id),
                item,
                commit=False,
                course_id=course_id,
            )
            for item in payload.items
        ]
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "changed": len(results),
        "revisions": {q["id"]: q["revision"] for q in results},
        "needs_review": any(q["status"] != "CONFIRMED" for q in results),
    }


@router.post(
    "/courses/{course_id}/question-bank/draw",
    response_model=PaperResponse,
    status_code=201,
)
def draw_questions(
    course_id: str,
    payload: BankDraw,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    paper = bank.draw(db, user.id, course_id, payload)
    from .exams import _paper_payload

    return _paper_payload(paper)


@router.get("/courses/{course_id}/exam-papers")
def list_exams(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_course(db, user.id, course_id)
    attempts = db.scalars(
        select(ExamAttempt)
        .join(ExamPaper)
        .where(
            ExamAttempt.user_id == user.id,
            ExamPaper.user_id == user.id,
            ExamPaper.course_id == course_id,
        )
        .order_by(ExamAttempt.created_at.desc())
    ).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "status": p.status,
            "mode": p.mode,
            "attempts": [
                {"id": a.id, "status": a.status} for a in attempts if a.paper_id == p.id
            ],
        }
        for p in db.scalars(
            select(ExamPaper)
            .where(ExamPaper.user_id == user.id, ExamPaper.course_id == course_id)
            .order_by(ExamPaper.created_at.desc())
            .limit(100)
        )
    ]


@router.get("/courses/{course_id}/question-bank/statistics")
def statistics(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_course(db, user.id, course_id)
    pool = bank.eligible_questions(db, user.id, course_id)
    papers = db.scalars(
        select(PastPaper).where(
            PastPaper.user_id == user.id, PastPaper.course_id == course_id
        )
    ).all()
    confirmed = [p for p in papers if p.review_status == "CONFIRMED"]
    topics = db.scalars(
        select(Topic).where(
            active_clause(),
            Topic.user_id == user.id,
            Topic.course_id == course_id,
            Topic.merged_into_id.is_(None),
        )
    ).all()
    return {
        "confirmed_papers": len(confirmed),
        "unknown_years": sum(p.year is None for p in confirmed),
        "eligible_questions": len(pool),
        "by_type": {
            kind: sum(q.question_type == kind for q, _ in pool) for kind in bank.KINDS
        },
        "unknown_points": sum(q.points is None for q, _ in pool),
        "known_points": sum(q.points or 0 for q, _ in pool),
        "by_topic": [
            {
                "id": t.id,
                "name": t.name,
                "count": sum(t.id in data["topic_ids"] for _, data in pool),
            }
            for t in topics
        ],
    }


@router.get("/attempts/{attempt_id}")
def restore_attempt(
    attempt_id: str,
    course_id: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    course = check_attempt_course(db, user.id, attempt_id)
    if course_id is not None and course_id != course.id:
        raise HTTPException(404, "作答不属于当前课程")
    attempt = db.get(ExamAttempt, attempt_id)
    from .exams import _attempt_response

    paper = db.get(ExamPaper, attempt.paper_id)
    snapshot = bank.attempt_snapshot(
        attempt, paper, db.get(ExamBlueprint, paper.blueprint_id)
    )
    return _attempt_response(attempt).model_dump() | {
        "deadline_at": bank.deadline(attempt, snapshot).isoformat(),
        "questions": [bank.public_question(q) for q in snapshot["questions"]],
    }


@router.post("/attempts/{attempt_id}/self-grades/{question_id}")
def self_grade(
    attempt_id: str,
    question_id: str,
    payload: SelfGrade,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    check_attempt_course(db, user.id, attempt_id, lock=True)
    attempt = db.get(ExamAttempt, attempt_id)
    if attempt.status == "IN_PROGRESS":
        raise HTTPException(409, "交卷后才能自行批改")
    paper = db.get(ExamPaper, attempt.paper_id)
    questions = bank.submitted_questions(
        attempt, paper, db.get(ExamBlueprint, paper.blueprint_id)
    )
    q = next((q for q in questions if q["id"] == question_id), None)
    if not q:
        raise HTTPException(404, "题目不属于本次作答")
    grades = json.loads(attempt.grading_json)
    g = grades[question_id]
    automatic = g.get("automatic")
    if automatic is None:
        automatic = bank.grade(q, json.loads(attempt.answers_json).get(question_id))[
            "automatic"
        ]
    if automatic:
        raise HTTPException(422, "自动批改题不能通过自评覆盖")
    if "self_correct" in g:
        if g.get("self_correct") != payload.correct:
            raise HTTPException(409, "该题已自行批改，不能用重复请求覆盖")
    else:
        g.update(
            status="self_correct" if payload.correct else "self_incorrect",
            self_correct=payload.correct,
            reviewed_at=bank.utc_now().isoformat(),
        )
        if not payload.correct:
            bank.mark_mistake(
                db,
                user.id,
                attempt.id,
                q,
                json.loads(attempt.answers_json).get(question_id),
            )
    attempt.grading_json = bank.encode(grades)
    attempt.status = (
        "SUBMITTED"
        if any(v["status"] == "pending_self_review" for v in grades.values())
        else "SCORED"
    )
    db.commit()
    from .exams import _attempt_response

    return _attempt_response(attempt)


@router.post("/courses/{course_id}/question-bank/archives/inspect")
def inspect_archive(
    course_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_archives import members, MAX_ZIP

    owned_course(db, user.id, course_id)
    try:
        return {
            "entries": [
                {"path": n, "kind": k, "size": len(b)}
                for n, k, b in members(file.file.read(MAX_ZIP + 1))
            ]
        }
    finally:
        file.file.close()


@router.post("/past-papers/{paper_id}/vision-resume", status_code=202)
def vision_resume(
    paper_id: str,
    payload: ConsentRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_vision import resume

    return resume(db, user.id, paper_id)


@router.post("/past-papers/{paper_id}/recognition-cancel")
def recognition_cancel(
    paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    from ..models import ProcessingJob

    paper = bank_topic_ai.owned_paper(db, user.id, paper_id, lock=True)
    for job in db.scalars(
        select(ProcessingJob).where(
            ProcessingJob.user_id == user.id,
            ProcessingJob.resource_id == paper.id,
            ProcessingJob.type.in_(["BANK_OCR", "BANK_EXTRACT"]),
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
    ):
        job.status, job.error, job.lease_token, job.lease_until = (
            "CANCELLED",
            "用户从上传列表删除，已取消识别",
            None,
            None,
        )
    db.commit()
    return {"cancelled": True}


@router.get("/past-questions/{question_id}/markdown")
def question_markdown(
    question_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    from fastapi.responses import Response

    q = db.scalar(
        select(PastQuestion).where(
            PastQuestion.id == question_id,
            PastQuestion.user_id == user.id,
            PastQuestion.status != "SUPERSEDED",
        )
    )
    if not q:
        raise HTTPException(404, "题目不存在")
    paper = db.get(PastPaper, q.paper_id)
    owned_course(db, user.id, paper.course_id)
    bank.no_active_attempt(db, user.id, paper.course_id)
    bank.require_source_valid(
        db, user.id, paper.course_id, [json.loads(q.bank_data_json)]
    )
    data = json.loads(q.bank_data_json)
    source = q.stem + "".join(
        f"\n\n### {chr(65 + i)}\n\n{o}" for i, o in enumerate(data.get("options", []))
    )
    return Response(
        source + "\n",
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="question-{q.id}.md"'},
    )
