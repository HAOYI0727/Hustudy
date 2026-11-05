"""User bank management and sampling, shared by M4 and the AI-study practice tab."""

import json
from pydantic import BaseModel, ConfigDict, Field
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
    ProcessingJob,
    ExamAttempt,
    ExamPaper,
    ExamBlueprint,
    Topic,
    User,
)
from ..schemas.exams import (
    BankImport,
    BankBatch,
    BankValuesBatch,
    BankSave,
    BankImageImport,
    BankQuestionEdit,
    BankDraw,
    BankManualPractice,
    BankWholePaperPractice,
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


@router.post("/past-papers/{paper_id}/answer-imports", status_code=201)
def answer_preview(paper_id: str, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.bank_answer_import import preview
    try:
        return preview(db, user.id, paper_id, file)
    finally:
        file.file.close()


@router.get("/past-papers/{paper_id}/answer-imports")
def answer_import_history(paper_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..models import BankAnswerImport
    from ..services.bank_answer_import import target
    target(db, user.id, paper_id)
    rows = db.scalars(select(BankAnswerImport).where(
        BankAnswerImport.paper_id == paper_id, BankAnswerImport.user_id == user.id,
        BankAnswerImport.status != "DELETED",
    ).order_by(BankAnswerImport.created_at.desc()).limit(20))
    return [{"id": row.id, "status": row.status, "filename": json.loads(row.scope_json)["filename"]} for row in rows]


@router.get("/answer-imports/{identity}")
def answer_detail(identity: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.bank_answer_import import owned, response
    return response(db, owned(db, user.id, identity))


@router.delete("/answer-imports/{identity}", status_code=204)
def delete_answer_import(identity: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.bank_answer_import import owned
    row = owned(db, user.id, identity)
    if row.job_id:
        job = db.get(ProcessingJob, row.job_id)
        if job and job.user_id == user.id:
            job.status = "CANCELLED"
            job.lease_token = None
            job.lease_until = None
    row.status = "DELETED"
    db.commit()


@router.post("/answer-imports/{identity}/confirm")
def answer_confirm(identity: str, payload: ConsentRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.bank_answer_import import confirm
    if not payload.confirm_remote_send:
        raise HTTPException(422, "请确认发送")
    return confirm(db, user.id, identity)


class AnswerApply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_ids: list[str] = Field(min_length=1, max_length=100)
    overwrite: bool = False


class AnswerCrop(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result_index: int = Field(ge=0)
    asset_id: str
    source_asset_id: str | None = None
    box: list[float] = Field(min_length=4, max_length=4)
    expected_answer: str = Field(max_length=20000)


class AnswerImageDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result_index: int = Field(ge=0)
    asset_id: str
    expected_answer: str = Field(max_length=20000)


class AnswerImagesAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result_index: int = Field(ge=0)
    expected_answer: str = Field(max_length=20000)
    images: dict[str, str] = Field(min_length=1, max_length=8)


@router.post("/answer-imports/{identity}/add-images")
def add_answer_images(identity: str, payload: AnswerImagesAdd, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.bank_answer_import import add_result_images
    return add_result_images(db, user.id, identity, payload)


@router.post("/answer-imports/{identity}/remove-image")
def remove_answer_image(identity: str, payload: AnswerImageDelete, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.bank_answer_import import remove_result_image
    return remove_result_image(db, user.id, identity, payload)


@router.post("/answer-imports/{identity}/crop")
def crop_answer_result(identity: str, payload: AnswerCrop, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.bank_answer_import import crop_result
    return crop_result(db, user.id, identity, payload)


@router.post("/answer-imports/{identity}/apply")
def answer_apply(identity: str, payload: AnswerApply, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.bank_answer_import import apply
    return apply(db, user.id, identity, payload.question_ids, payload.overwrite)


@router.get("/past-questions/{question_id}/image-group")
def image_group(question_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.bank_edits import owned_question
    from ..services.question_display import display_group

    question, paper = owned_question(db, user.id, question_id)
    group = display_group(question.number, paper.id)
    rows = db.scalars(select(PastQuestion).where(
        PastQuestion.paper_id == paper.id, PastQuestion.user_id == user.id,
        PastQuestion.status != "SUPERSEDED",
    )).all()
    metadata=json.loads(paper.bank_meta_json)
    page_ids=list(metadata.get("image_import",{}).get("asset_ids",[]))
    for row in rows:
        for source in json.loads(row.bank_data_json).get("source_images",[]):
            if source["asset_id"] not in page_ids:
                page_ids.append(source["asset_id"])
    sources=[{"asset_id":asset_id,"box":[0,0,1,1],"alt":f"原文件第{index+1}页"} for index,asset_id in enumerate(page_ids)]
    return [
        {"id": q.id, "revision": q.revision, "images": json.loads(q.bank_data_json).get("illustrations", []),
         "preferred_asset_id": next((i["asset_id"] for i in json.loads(q.bank_data_json).get("source_images",[])),None),
         "sources": sources}
        for q in rows if (group and (display_group(q.number, paper.id) or {}).get("key") == group["key"])
        or (not group and q.id == question.id)
    ]


class GroupImages(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revisions: dict[str, int] = Field(min_length=1, max_length=500)
    images: list[dict] = Field(max_length=8)


@router.put("/past-questions/{question_id}/image-group")
def save_group_images(question_id: str, payload: GroupImages, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..services.bank_edits import owned_question, sync_review_status
    from ..services.bank_images import check_images

    question, paper = owned_question(db, user.id, question_id)
    group = image_group(question_id, user, db)
    if payload.revisions != {q["id"]: q["revision"] for q in group}:
        raise HTTPException(409, "大题内容已变化，请保留插图并刷新后重试")
    images = check_images(db, user.id, paper.course_id, payload.images)
    for item in group:
        row = db.get(PastQuestion, item["id"])
        data = json.loads(row.bank_data_json)
        data["illustrations"], data["images_reviewed"] = images, False
        row.bank_data_json = bank.encode(data)
        row.revision += 1
        row.status = "DRAFT"
    sync_review_status(db, [paper])
    db.commit()
    return {"changed": len(group), "revisions": {item["id"]: item["revision"] + 1 for item in group}}


@router.post("/courses/{course_id}/question-bank/files", status_code=202)
def bank_upload(
    course_id: str,
    file: UploadFile = File(...),
    mode: str = Form(default="local", pattern="^(local|ai)$"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.documents import save_upload
    from ..schemas.material import JobResponse

    owned_course(db, user.id, course_id)
    bank.no_active_attempt(db, user.id, course_id)
    try:
        if mode == "local":
            from ..services.bank_strict_markdown import validate_file

            validate_file(file.filename or "", file.file.read(2 * 1024 * 1024 + 1))
            file.file.seek(0)
        _, _, job, _ = save_upload(
            file, course_id, user.id, db, library_scope="question_bank",
            defer_parse=mode == "ai" and (file.filename or "").lower().endswith(".pdf"),
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


class AutoClassifyRequest(bank_topic_ai.ConsentRequest):
    revision: int = Field(ge=1, strict=True)


@router.post(
    "/courses/{course_id}/past-questions/{question_id}/auto-classify", status_code=202
)
def auto_classify_question(
    course_id: str,
    question_id: str,
    payload: AutoClassifyRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_edits import owned_question
    from ..services import topic_tree

    q, paper = owned_question(db, user.id, question_id)
    if paper.course_id != course_id:
        raise HTTPException(404, "题目不属于当前课程")
    if q.revision != payload.revision:
        raise HTTPException(409, "题目已变化，请刷新后重新归类")
    ids = json.loads(q.bank_data_json).get(
        "topic_ids", [q.topic_id] if q.topic_id else []
    )
    if set(ids).intersection(t.id for t in topic_tree.rows(db, user.id, course_id)):
        raise HTTPException(409, "题目已归类，请刷新列表")
    scope = bank_topic_ai.preview(db, user.id, paper.id, [q.id], auto_apply=True)
    return bank_topic_ai.confirm(db, user.id, paper.id, scope["preview_id"])


class AutoClassifyBatchRequest(bank_topic_ai.ConsentRequest):
    revisions: dict[str, int] = Field(min_length=1, max_length=5000)


@router.post(
    "/courses/{course_id}/past-papers/{paper_id}/auto-classify", status_code=202
)
def auto_classify_batch(
    course_id: str,
    paper_id: str,
    payload: AutoClassifyBatchRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_edits import owned_question
    from ..services import topic_tree

    paper = bank_topic_ai.owned_paper(db, user.id, paper_id, lock=True)
    if paper.course_id != course_id:
        raise HTTPException(404, "题库不属于当前课程")
    known = {t.id for t in topic_tree.rows(db, user.id, course_id)}
    for qid, revision in payload.revisions.items():
        q, owner = owned_question(db, user.id, qid)
        if owner.id != paper.id:
            raise HTTPException(404, "题目不属于当前题库")
        if q.revision != revision:
            raise HTTPException(409, "题目已变化，请刷新后重新归类")
        ids = json.loads(q.bank_data_json).get(
            "topic_ids", [q.topic_id] if q.topic_id else []
        )
        if known.intersection(ids):
            raise HTTPException(409, "所选题目已有归类，请刷新后重选")
    scope = bank_topic_ai.preview(
        db, user.id, paper.id, list(payload.revisions), auto_apply=True
    )
    return bank_topic_ai.confirm(db, user.id, paper.id, scope["preview_id"])


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

    return capabilities(user.id)


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
    mode: str = Form(default="local", pattern="^(local|ai)$"),
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
            db,
            user.id,
            course_id,
            file.file.read(MAX_ZIP + 1),
            chosen,
            local=mode == "local",
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
        if action == "review_topics":
            existing = json.loads(q.bank_data_json).get("topic_ids", [])
            if not 1 <= len(existing) <= 5:
                raise HTTPException(
                    422, f"题号{q.number}需要先设置1至5个知识标签；整批未修改"
                )
            bank.topic_rows(db, user_id, paper.course_id, existing)
        rows.append((q, paper))
    if action == "confirm":
        from ..services.bank_images import check_images

        errors = {}
        for q, paper in rows:
            data = json.loads(q.bank_data_json)
            warnings = bank.validate_question(q, data | {"images_reviewed": True})
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
            data["images_reviewed"] = True
            data["topic_index"] = data.get("topic_index", {}) | {
                "selection_reviewed": True
            }
            q.status = "CONFIRMED"
        elif action == "review_topics":
            if data.get("topic_index", {}).get("selection_reviewed") is True:
                continue
            data["topic_index"] = data.get("topic_index", {}) | {
                "selection_reviewed": True
            }
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


@router.post("/courses/{course_id}/question-bank/batch-values")
def batch_question_values(
    course_id: str,
    payload: BankValuesBatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_edits import batch_values

    return batch_values(db, user.id, course_id, payload)


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


@router.get("/courses/{course_id}/question-bank/practice-questions")
def practice_candidates(
    course_id: str,
    query: str = Query(default="", max_length=500),
    topic_id: str | None = None,
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned_course(db, user.id, course_id)
    from ..services.topic_tree import expand

    requested = set()
    if topic_id:
        bank.topic_rows(db, user.id, course_id, [topic_id])
        requested = expand(db, user.id, course_id, [topic_id])
    matches = [
        q for q, data in bank.eligible_questions(db, user.id, course_id)
        if query.strip().casefold() in q.stem.casefold()
        and (not requested or requested.intersection(data["topic_ids"]))
    ]
    return {
        "total": len(matches),
        "items": [
            {"id": q.id, "stem": q.stem, "number": q.number, "points": q.points}
            for q in matches[offset:offset + 20]
        ],
    }


@router.post("/courses/{course_id}/question-bank/manual-practice", response_model=PaperResponse, status_code=201)
def manual_practice(
    course_id: str,
    payload: BankManualPractice,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from .exams import _paper_payload

    return _paper_payload(bank.draw(db, user.id, course_id, payload))


@router.get("/courses/{course_id}/question-bank/practice-papers")
def practice_papers(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    from ..services.bank_paper_practice import papers

    return papers(db, user.id, course_id)


@router.post(
    "/courses/{course_id}/question-bank/papers/{paper_id}/practice",
    response_model=PaperResponse,
    status_code=201,
)
def practice_whole_paper(
    course_id: str,
    paper_id: str,
    payload: BankWholePaperPractice,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_paper_practice import create
    from .exams import _paper_payload

    return _paper_payload(create(db, user.id, course_id, paper_id, payload))


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


@router.delete("/attempts/{attempt_id}")
def delete_attempt(
    attempt_id: str,
    confirm_delete: bool = False,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.attempt_deletion import remove

    return remove(db, user.id, attempt_id, confirm_delete)


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
    known = bank.points_known(q)
    if known:
        if (
            payload.score is None
            or payload.correct is not None
            or payload.score > q["points"]
        ):
            raise HTTPException(422, "请输入0至本题满分的整数得分，不使用对错自评")
        if "self_correct" in g:
            if g.get("score") != payload.score:
                raise HTTPException(409, "该题已评分，不能覆盖原评分")
        else:
            g.update(
                status="self_scored",
                score=payload.score,
                max_score=q["points"],
                self_correct=payload.score == q["points"],
                reviewed_at=bank.utc_now().isoformat(),
            )
            if payload.score < q["points"]:
                bank.mark_mistake(
                    db,
                    user.id,
                    attempt.id,
                    q,
                    json.loads(attempt.answers_json).get(question_id),
                )
    else:
        if payload.correct is None or payload.score is not None:
            raise HTTPException(422, "本题未设分值，请使用对错自评")
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
    attempt.score = sum(
        grades[item["id"]].get("score", 0)
        for item in questions
        if bank.points_known(item)
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
