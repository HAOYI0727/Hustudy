"""M4 topic lifecycle, analysis snapshots and read-only source matrix."""

import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import User, ExamAnalysisReport, PastPaper
from ..schemas.exams import TopicEdit, TopicMerge, TopicSourceEdit, TopicResponse
from ..schemas.exams import BankSplit, BankMerge, BankMetadataEdit, BankMetadataBatch
from ..services import bank_edits, topic_tree
from ..services import exam_analysis as service
from ..services import question_bank as bank
from ..services.courses import owned_course
from ..repositories.materials import checked_chunk

router = APIRouter(prefix="/api/v1", tags=["exam-analysis"])


@router.post("/past-questions/{question_id}/split")
def split_question(
    question_id: str,
    payload: BankSplit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    q, paper = bank_edits.owned_question(db, user.id, question_id)
    return bank_edits.split(db, user.id, q, paper, payload)


@router.post("/courses/{course_id}/question-bank/merge")
def merge_questions(
    course_id: str,
    payload: BankMerge,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return bank_edits.merge(db, user.id, course_id, payload)


def topic_payload(row):
    return TopicResponse(
        id=row.id,
        name=row.name,
        aliases=json.loads(row.aliases_json),
        revision=row.revision,
        merged_into_id=row.merged_into_id,
        parent_id=topic_tree.parent_id(row),
    )


@router.patch("/topics/{topic_id}", response_model=TopicResponse)
def rename(
    topic_id: str,
    payload: TopicEdit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = service.topic(db, user.id, topic_id, lock=True)
    return topic_payload(service.rename_topic(db, user.id, row, payload))


@router.delete("/topics/{topic_id}")
def delete_topic(
    topic_id: str,
    revision: int = Query(ge=1),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = service.topic(db, user.id, topic_id, lock=True)
    return service.delete_topic(db, user.id, row, revision)


@router.post("/topics/{topic_id}/merge", response_model=TopicResponse)
def merge(
    topic_id: str,
    payload: TopicMerge,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = service.topic(db, user.id, topic_id, lock=True)
    return topic_payload(service.merge_topic(db, user.id, row, payload))


@router.put("/topics/{topic_id}/sources", response_model=TopicResponse)
def confirm_source(
    topic_id: str,
    payload: TopicSourceEdit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = service.topic(db, user.id, topic_id, lock=True)
    service.checked_revision(row, payload.revision)
    source = checked_chunk(
        db,
        str(payload.version_id),
        str(payload.chunk_id),
        payload.quote,
        user.id,
        row.course_id,
    )
    citation = {
        "version_id": str(payload.version_id),
        "chunk_id": source.id,
        "quote": payload.quote,
        "quote_hash": hashlib.sha256(payload.quote.encode()).hexdigest(),
        "locator": {"type": source.locator_type, "value": source.locator_value},
    }
    values = json.loads(row.sources_json).get("citations", [])
    if citation not in values:
        if len(values) >= 20:
            raise HTTPException(422, "每个标签最多确认20处资料依据")
        values.append(citation)
        row.sources_json = bank.encode(
            json.loads(row.sources_json) | {"citations": values}
        )
        row.revision += 1
    db.commit()
    return topic_payload(row)


@router.post("/courses/{course_id}/exam-analyses", status_code=201)
def create(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return service.create_report(db, user.id, course_id)


@router.get("/courses/{course_id}/exam-analyses")
def history(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_course(db, user.id, course_id)
    return [
        {"id": r.id, "status": r.status, "created_at": r.created_at}
        for r in db.scalars(
            select(ExamAnalysisReport)
            .where(
                ExamAnalysisReport.user_id == user.id,
                ExamAnalysisReport.course_id == course_id,
            )
            .order_by(ExamAnalysisReport.created_at.desc())
            .limit(50)
        )
    ]


@router.get("/exam-analyses/{report_id}")
def get(
    report_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return service.report_payload(db, user.id, report_id)


@router.get("/exam-analyses/{report_id}/gaps")
def gaps(
    report_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return service.gaps(db, user.id, report_id)


@router.post("/courses/{course_id}/question-bank/metadata-batch")
def metadata_batch(
    course_id: str,
    payload: BankMetadataBatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_identity import edit_batch

    return edit_batch(
        db,
        user.id,
        course_id,
        [item.model_dump(mode="json", exclude_unset=True) for item in payload.items],
    )


@router.patch("/past-papers/{paper_id}/metadata")
def metadata(
    paper_id: str,
    payload: BankMetadataEdit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_identity import edit_batch

    row = db.scalar(
        select(PastPaper).where(PastPaper.user_id == user.id, PastPaper.id == paper_id)
    )
    if not row:
        raise HTTPException(404, "题库不存在")
    if (
        payload.exam_identity is not None
        and "expected_revision" not in payload.model_fields_set
    ):
        raise HTTPException(422, "身份操作必须提供元数据修订号")
    data = payload.model_dump(mode="json", exclude_unset=True)
    data.setdefault("expected_revision", 1)
    edit_batch(db, user.id, row.course_id, [data | {"paper_id": paper_id}])
    meta = json.loads(row.bank_meta_json)
    return {
        "id": row.id,
        "title": row.title,
        "year": row.year,
        "metadata": {
            k: v
            for k, v in meta.items()
            if k
            not in {
                "ai_extract",
                "ai_topic_index",
                "image_import",
                "pdf_import",
                "vision_checkpoints",
                "pdf_render_complete",
            }
        },
    }


@router.get("/courses/{course_id}/question-bank/papers")
def bank_papers(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_course(db, user.id, course_id)
    from ..services.bank_deletion import question_rows, snapshot
    from ..services.question_display import has_major_groups

    return [
        {
            "id": p.id,
            "title": p.title,
            "year": p.year,
            "metadata": {
                k: v
                for k, v in json.loads(p.bank_meta_json).items()
                if k
                not in {
                    "ai_extract",
                    "ai_topic_index",
                    "image_import",
                    "pdf_import",
                    "vision_checkpoints",
                    "pdf_render_complete",
                }
            },
            "status": p.review_status,
            "question_count": len(question_rows(db, p.id)),
            "has_major_groups": has_major_groups(question_rows(db, p.id)),
            "question_snapshot": snapshot(question_rows(db, p.id)),
            "recognition": recognition_status(db, p),
        }
        for p in db.scalars(
            select(PastPaper)
            .where(
                PastPaper.user_id == user.id,
                PastPaper.course_id == course_id,
                func.coalesce(
                    func.json_extract(PastPaper.bank_meta_json, "$.deleted_by_user"), 0
                )
                != 1,
            )
            .order_by(PastPaper.created_at.desc())
            .limit(200)
        )
        if not json.loads(p.bank_meta_json).get("deleted_by_user")
    ]


def recognition_status(db, paper):
    from ..models import ProcessingJob

    meta = json.loads(paper.bank_meta_json)
    job = (
        db.get(ProcessingJob, meta.get("image_job_id"))
        if meta.get("image_job_id")
        else None
    )
    if not job:
        return None
    return {
        "status": job.status,
        "error": job.error,
        "completed_pages": len(meta.get("vision_checkpoints", [])),
        "total_pages": len(meta.get("image_import", {}).get("asset_ids", [])),
        "engine": meta.get("image_import", {}).get("engine", "local"),
    }
