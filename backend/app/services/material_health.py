"""Current material readiness, independent of historical task failures."""

from sqlalchemy import select, func, case, and_, or_
from ..core.database import begin_read_snapshot
from ..models import (
    Document,
    DocumentVersion,
    DocumentChunk,
    ManualTranscript,
    ProcessingJob,
)
from ..models.base import utc_now
from ..repositories.source_links import STRIP_CHARS
from .courses import owned_course

ISSUES = ("text", "parse", "index", "preview", "processing")


def current_rows(user_id, course_id):
    latest = (
        select(DocumentVersion.id)
        .where(
            DocumentVersion.document_id == Document.id,
            DocumentVersion.user_id == user_id,
        )
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
        .correlate(Document)
        .scalar_subquery()
    )
    text = (
        select(DocumentChunk.id)
        .outerjoin(ManualTranscript, ManualTranscript.chunk_id == DocumentChunk.id)
        .where(
            DocumentChunk.version_id == DocumentVersion.id,
            DocumentChunk.user_id == user_id,
            func.length(func.trim(DocumentChunk.text, STRIP_CHARS)) > 0,
            or_(
                and_(
                    DocumentChunk.source_kind == "extracted",
                    DocumentVersion.parse_status == "SUCCEEDED",
                ),
                and_(
                    DocumentChunk.source_kind == "manual_transcript",
                    ManualTranscript.user_id == user_id,
                    ManualTranscript.version_id == DocumentVersion.id,
                    ManualTranscript.status == "CONFIRMED",
                ),
            ),
        )
        .correlate(DocumentVersion)
        .exists()
    )
    rows = (
        select(
            Document.id.label("document_id"),
            Document.name,
            Document.updated_at,
            DocumentVersion.id.label("version_id"),
            DocumentVersion.version_no,
            DocumentVersion.parse_status,
            DocumentVersion.index_status,
            DocumentVersion.preview_status,
            func.coalesce(
                func.nullif(DocumentVersion.original_filename, ""),
                Document.original_filename,
            ).label("original_filename"),
            text.label("has_text"),
        )
        .join(DocumentVersion, DocumentVersion.id == latest)
        .where(
            Document.user_id == user_id,
            Document.course_id == course_id,
            Document.deleted_at.is_(None),
            Document.library_scope == "material",
        )
        .subquery()
    )
    active_parse = rows.c.parse_status.in_(["QUEUED", "RUNNING"])
    checks = {
        "text": and_(~rows.c.has_text, ~active_parse),
        "parse": rows.c.parse_status.in_(["FAILED", "CANCELLED"]),
        "index": rows.c.index_status.in_(["FAILED", "CANCELLED"]),
        "preview": and_(
            rows.c.preview_status.in_(["FAILED", "CANCELLED"]),
            or_(
                *(
                    func.lower(rows.c.original_filename).endswith(ext)
                    for ext in (".pdf", ".pptx", ".docx")
                )
            ),
        ),
        "processing": or_(
            *(
                rows.c[field].in_(["QUEUED", "RUNNING"])
                for field in ("parse_status", "index_status", "preview_status")
            )
        ),
    }
    return select(
        *rows.c,
        *(value.label(key) for key, value in checks.items()),
        or_(*(checks[key] for key in ISSUES if key != "processing")).label("attention"),
    ).subquery()


def counts(db, rows):
    return dict(
        db.execute(
            select(
                func.count().label("materials"),
                *(
                    func.coalesce(func.sum(case((rows.c[key], 1), else_=0)), 0).label(
                        key
                    )
                    for key in ("attention", *ISSUES)
                ),
                func.coalesce(func.sum(case((rows.c.has_text, 1), else_=0)), 0).label(
                    "readable"
                ),
            ).select_from(rows)
        )
        .mappings()
        .one()
    )


def current_counts(db, user_id, course_id):
    return counts(db, current_rows(user_id, course_id))


def page(db, user_id, course_id, issue, q, offset, limit):
    begin_read_snapshot(db)
    owned_course(db, user_id, course_id)
    rows = current_rows(user_id, course_id)
    matched = select(rows)
    if q.strip():
        matched = matched.where(
            func.instr(func.lower(rows.c.name), q.strip().lower()) > 0
        )
    rows = matched.subquery()
    overview = counts(db, rows)
    selected = select(rows)
    if issue != "all":
        selected = selected.where(rows.c[issue])
    result = (
        db.execute(
            selected.order_by(rows.c.updated_at.desc(), rows.c.document_id)
            .offset(offset)
            .limit(limit)
        )
        .mappings()
        .all()
    )
    ids = [row["version_id"] for row in result]
    jobs = {}
    if ids:
        ranked = (
            select(
                ProcessingJob.resource_id,
                ProcessingJob.id,
                ProcessingJob.type,
                ProcessingJob.status,
                ProcessingJob.attempt_count,
                ProcessingJob.max_attempts,
                case(
                    (
                        ProcessingJob.status == "CANCELLED",
                        "任务已取消，恢复后沿用原次数预算。",
                    ),
                    (
                        ProcessingJob.status == "FAILED",
                        case(
                            (
                                ProcessingJob.type == "PARSE",
                                "解析未完成，请核对原件；扫描PDF可确认人工文字。",
                            ),
                            (
                                ProcessingJob.type == "INDEX",
                                "索引未完成，请核对有效正文与处理记录。",
                            ),
                            else_="兼容预览未完成，可核对转换环境或使用文本/原格式。",
                        ),
                    ),
                    else_=None,
                ).label("error"),
                func.row_number()
                .over(
                    partition_by=(ProcessingJob.resource_id, ProcessingJob.type),
                    order_by=(ProcessingJob.created_at.desc(), ProcessingJob.id.desc()),
                )
                .label("rank"),
            )
            .where(
                ProcessingJob.user_id == user_id,
                ProcessingJob.resource_id.in_(ids),
                ProcessingJob.type.in_(["PARSE", "INDEX", "PREVIEW"]),
            )
            .subquery()
        )
        for row in db.execute(
            select(ranked).where(ranked.c.rank == 1).order_by(ranked.c.type)
        ).mappings():
            jobs.setdefault(row["resource_id"], []).append(row)
    return dict(
        course_id=course_id,
        counts=overview,
        total=overview["materials" if issue == "all" else issue],
        items=[
            dict(
                **{
                    key: row[key]
                    for key in (
                        "document_id",
                        "name",
                        "updated_at",
                        "version_id",
                        "version_no",
                        "parse_status",
                        "index_status",
                        "preview_status",
                        "has_text",
                    )
                },
                issues=[key for key in ISSUES if row[key]],
                jobs=jobs.get(row["version_id"], []),
            )
            for row in result
        ],
        offset=offset,
        limit=limit,
        checked_at=utc_now(),
    )
