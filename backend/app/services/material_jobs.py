"""Authorized material job controls, serialized against lease completion/deletion."""

from fastapi import HTTPException
from sqlalchemy import select, update
from ..models import (
    DocumentVersion,
    ProcessingJob,
    DocumentChunk,
    ManualTranscript,
    Asset,
)
from ..repositories.materials import active_version
from ..schemas.material import JobResponse

FIELDS = {"PARSE": "parse_status", "INDEX": "index_status", "PREVIEW": "preview_status"}


def lock_version(db, version_id, user_id):
    active_version(db, version_id, user_id)
    db.execute(
        update(DocumentVersion)
        .where(DocumentVersion.id == version_id, DocumentVersion.user_id == user_id)
        .values(updated_at=DocumentVersion.updated_at)
        .execution_options(synchronize_session=False)
    )
    db.expire_all()
    return active_version(db, version_id, user_id)


def owned_job(db, job_id, user_id):
    job = db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.id == job_id, ProcessingJob.user_id == user_id
        )
    )
    if not job:
        raise HTTPException(404, "任务不存在")
    if job.type not in FIELDS:
        raise HTTPException(409, "此操作仅支持资料解析、索引和预览任务")
    version = lock_version(db, job.resource_id, user_id)
    return db.get(ProcessingJob, job_id), version


def dependent_status(db, version, value):
    for kind in ("INDEX", "PREVIEW"):
        exists = db.scalar(
            select(ProcessingJob.id)
            .where(ProcessingJob.resource_id == version.id, ProcessingJob.type == kind)
            .limit(1)
        )
        if not exists and getattr(version, FIELDS[kind]) in {"PENDING", "CANCELLED"}:
            setattr(version, FIELDS[kind], value)


def has_index_input(db, version, user_id):
    manual = db.scalar(
        select(ManualTranscript.id)
        .where(
            ManualTranscript.version_id == version.id,
            ManualTranscript.user_id == user_id,
            ManualTranscript.status == "CONFIRMED",
        )
        .limit(1)
    )
    extracted = version.parse_status == "SUCCEEDED" and db.scalar(
        select(DocumentChunk.id)
        .where(
            DocumentChunk.version_id == version.id,
            DocumentChunk.user_id == user_id,
            DocumentChunk.source_kind == "extracted",
        )
        .limit(1)
    )
    return bool(manual or extracted)


def cancel_job(db, user_id, job_id):
    job, version = owned_job(db, job_id, user_id)
    if job.status == "CANCELLED":
        db.commit()
        return JobResponse.model_validate(job, from_attributes=True)
    if job.status not in {"QUEUED", "RUNNING"}:
        raise HTTPException(409, "只能取消排队或处理中的任务")
    job.status = "CANCELLED"
    job.lease_token = None
    job.lease_until = None
    job.error = "用户已取消；后台处理可能稍后结束，结果不会写入"
    setattr(version, FIELDS[job.type], "CANCELLED")
    if job.type == "PARSE":
        dependent_status(db, version, "CANCELLED")
    db.commit()
    return JobResponse.model_validate(job, from_attributes=True)


def retry_job(db, user_id, job_id):
    job, version = owned_job(db, job_id, user_id)
    if job.status in {"QUEUED", "RUNNING"}:
        db.commit()
        return JobResponse.model_validate(job, from_attributes=True)
    if (
        job.status not in {"FAILED", "CANCELLED"}
        or job.attempt_count >= job.max_attempts
    ):
        raise HTTPException(409, "仅失败或取消任务可恢复，且不能超过尝试上限")
    if db.scalar(
        select(ProcessingJob.id).where(
            ProcessingJob.resource_id == version.id,
            ProcessingJob.type == job.type,
            ProcessingJob.id != job.id,
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
    ):
        raise HTTPException(409, "此版本已有同类型任务正在处理")
    if job.type == "INDEX" and not has_index_input(db, version, user_id):
        raise HTTPException(409, "没有可索引的有效正文，请先完成解析或确认人工文字")
    job.status = "QUEUED"
    job.error = None
    job.progress = 0
    job.lease_token = None
    job.lease_until = None
    setattr(version, FIELDS[job.type], "QUEUED")
    if job.type == "PARSE":
        dependent_status(db, version, "PENDING")
    db.commit()
    return JobResponse.model_validate(job, from_attributes=True)


def reindex(db, user_id, version_id, request_id):
    version = lock_version(db, version_id, user_id)
    previous = db.get(ProcessingJob, request_id)
    if previous:
        if previous.user_id != user_id:
            raise HTTPException(404, "请求标识不可用")
        if previous.resource_id != version_id or previous.type != "INDEX":
            raise HTTPException(409, "请求标识已用于另一任务，请使用新标识")
        db.commit()
        return JobResponse.model_validate(previous, from_attributes=True)
    if not has_index_input(db, version, user_id):
        raise HTTPException(
            409, "此版本还没有成功提取正文或已确认人工文字，请先完成解析或补录"
        )
    jobs = db.scalars(
        select(ProcessingJob)
        .where(
            ProcessingJob.resource_id == version_id,
            ProcessingJob.user_id == user_id,
            ProcessingJob.type == "INDEX",
        )
        .order_by(ProcessingJob.created_at.desc(), ProcessingJob.id.desc())
    ).all()
    pending = next((row for row in jobs if row.status in {"QUEUED", "RUNNING"}), None)
    if pending:
        raise HTTPException(
            409,
            {
                "message": "此版本已有索引任务正在处理，请查看处理记录",
                "active_job_id": pending.id,
            },
        )
    if jobs and jobs[0].status in {"FAILED", "CANCELLED"}:
        raise HTTPException(
            409, "请先恢复已有失败/取消的索引任务；重建不能重置其尝试上限"
        )
    job = ProcessingJob(
        id=request_id, user_id=user_id, type="INDEX", resource_id=version_id
    )
    db.add(job)
    version.index_status = "QUEUED"
    db.commit()
    db.refresh(job)
    return JobResponse.model_validate(job, from_attributes=True)


def request_preview(db, user_id, version_id):
    """Serialize duplicate clicks and reuse failed jobs without resetting budgets."""
    from pathlib import Path
    from .preview_runtime import office_executable

    version = lock_version(db, version_id, user_id)
    source = Path(version.source_path)
    if source.suffix.lower() not in {".pdf", ".pptx", ".docx"}:
        raise HTTPException(422, "该格式使用文本阅读；PDF预览支持PDF/PPTX/DOCX")
    if not source.is_file():
        raise HTTPException(404, "原始文件不可用，无法生成预览")
    jobs = db.scalars(
        select(ProcessingJob)
        .where(
            ProcessingJob.resource_id == version_id,
            ProcessingJob.user_id == user_id,
            ProcessingJob.type == "PREVIEW",
        )
        .order_by(ProcessingJob.created_at.desc(), ProcessingJob.id.desc())
    ).all()
    pending = next((job for job in jobs if job.status in {"QUEUED", "RUNNING"}), None)
    if pending:
        db.commit()
        return JobResponse.model_validate(pending, from_attributes=True)
    if (
        version.preview_status == "SUCCEEDED"
        and version.preview_path
        and Path(version.preview_path).is_file()
    ):
        from .preview_integrity import check_preview_mapping

        try:
            check_preview_mapping(source, Path(version.preview_path))
        except ValueError:
            if db.scalar(
                select(Asset.id)
                .where(
                    Asset.user_id == user_id,
                    Asset.source_version_id == version_id,
                    Asset.deleted.is_(False),
                )
                .limit(1)
            ):
                raise HTTPException(
                    409,
                    "旧预览页号不完整且已有截图，请先人工核对截图来源；不会静默改变现有来源",
                )
        else:
            raise HTTPException(409, "预览已就绪，请直接打开PDF预览")
    if source.suffix.lower() != ".pdf" and not office_executable():
        raise HTTPException(
            409,
            "本机未找到可执行的LibreOffice，请先安装或修复转换器，再重试预览；原文仍可阅读",
        )
    if jobs and jobs[0].status in {"FAILED", "CANCELLED"}:
        return retry_job(db, user_id, jobs[0].id)
    job = ProcessingJob(user_id=user_id, type="PREVIEW", resource_id=version_id)
    db.add(job)
    version.preview_status = "QUEUED"
    version.preview_error = None
    db.commit()
    db.refresh(job)
    return JobResponse.model_validate(job, from_attributes=True)
