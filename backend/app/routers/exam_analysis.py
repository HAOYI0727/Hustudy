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
from ..schemas.exams import BankSplit, BankMerge, BankMetadataEdit
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


@router.patch("/past-papers/{paper_id}/metadata")
def metadata(
    paper_id: str,
    payload: BankMetadataEdit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    payload = payload.model_dump(mode="json", exclude_unset=True)
    expected_revision = payload.pop("expected_revision", 1)
    # Unknown years and manual duplicate groups remain explicit.
    row = db.scalar(
        select(PastPaper).where(PastPaper.user_id == user.id, PastPaper.id == paper_id)
    )
    if not row:
        raise HTTPException(404, "题库不存在")
    owned_course(db, user.id, row.course_id, lock=True)
    bank.no_active_attempt(db, user.id, row.course_id)
    if set(payload) - {"year", "variant", "provenance", "duplicate_of"}:
        raise HTTPException(422, "只允许年份、卷别与来源说明")
    year = payload.get("year", row.year)
    if year is not None and (type(year) is not int or not 1900 <= year <= 2200):
        raise HTTPException(422, "年份必须未知或1900–2200之间的整数")
    meta = json.loads(row.bank_meta_json)
    if meta.get("revision", 1) != expected_revision:
        raise HTTPException(409, "题库元数据已变化，请刷新后重试")
    if "duplicate_of" in payload:
        target_id = payload["duplicate_of"]
        if target_id:
            target = db.scalar(
                select(PastPaper).where(
                    PastPaper.id == target_id,
                    PastPaper.user_id == user.id,
                    PastPaper.course_id == row.course_id,
                )
            )
            if not target:
                raise HTTPException(404, "代表试卷不存在或不属于本课程")
            if target.id == row.id or json.loads(target.bank_meta_json).get(
                "duplicate_of"
            ):
                raise HTTPException(422, "重复材料须指向另一独立代表卷")
        meta["duplicate_of"] = target_id
    meta["revision"] = expected_revision + 1
    for key, limit in [("variant", 80), ("provenance", 500)]:
        if key in payload:
            if not isinstance(payload[key], str) or len(payload[key]) > limit:
                raise HTTPException(422, "卷别或来源说明不合法")
            meta[key] = payload[key]
    row.year = year
    row.bank_meta_json = bank.encode(meta)
    db.commit()
    return {
        "id": row.id,
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
            "question_snapshot": snapshot(question_rows(db, p.id)),
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
