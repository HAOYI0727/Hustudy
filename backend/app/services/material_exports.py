"""M1 course packages: owned metadata, immutable source files, bounded ZIP output."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import zipfile

from fastapi import HTTPException
from sqlalchemy import select, update, func, cast, LargeBinary
from ..core.config import get_settings
from ..models import (
    Course,
    Document,
    DocumentVersion,
    DocumentChunk,
    ManualTranscript,
    Asset,
    MaterialExport,
    ProcessingJob,
)
from ..models.base import utc_now
from ..repositories.assets import available_assets
from ..schemas.material import JobResponse
from ..schemas.material_exports import MaterialExportResponse

MAX_CONTENT = 256 * 1024 * 1024
MAX_METADATA = 16 * 1024 * 1024
MAX_CHUNKS = 50000
EXPORT_SECONDS = 120


def owned_course(db, course_id, user_id):
    from .courses import owned_course as active_course

    return active_course(db, user_id, course_id)


def owned_export(db, export_id, user_id):
    row = db.scalar(
        select(MaterialExport).where(
            MaterialExport.id == export_id, MaterialExport.user_id == user_id
        )
    )
    if not row:
        raise HTTPException(404, "资料包不存在")
    owned_course(db, row.course_id, user_id)
    return row


def sources_available(db, row):
    refs = row.sources_json
    for model, key, predicate in (
        (
            Document,
            "documents",
            Document.deleted_at.is_(None) & (Document.course_id == row.course_id),
        ),
        (Asset, "assets", available_assets(row.user_id, row.course_id)),
        (
            ManualTranscript,
            "transcripts",
            ManualTranscript.status.in_(["CONFIRMED", "SUPERSEDED"]),
        ),
    ):
        ids = refs.get(key, [])
        selected = func.json_each(json.dumps(ids)).table_valued("value")
        if ids and db.scalar(
            select(func.count())
            .select_from(model)
            .where(
                model.id.in_(select(selected.c.value)),
                model.user_id == row.user_id,
                predicate,
            )
        ) != len(ids):
            return False
    return True


def response(db, row):
    job = db.get(ProcessingJob, row.job_id)
    availability = "pending"
    if job.status == "SUCCEEDED":
        availability = (
            "active"
            if row.zip_path
            and Path(row.zip_path).is_file()
            and sources_available(db, row)
            else "unavailable"
        )
    return MaterialExportResponse(
        id=row.id,
        course_id=row.course_id,
        created_at=row.created_at,
        snapshot_at=row.snapshot_at,
        sha256=row.sha256,
        size_bytes=row.size_bytes,
        counts=row.counts_json,
        availability=availability,
        job=JobResponse.model_validate(job, from_attributes=True),
    )


def create_export(db, course_id, user_id, request_id):
    owned_course(db, course_id, user_id)
    # Serialize request de-duplication, limits, retries and course deletion.
    db.execute(
        update(Course)
        .where(Course.id == course_id, Course.user_id == user_id)
        .values(updated_at=Course.updated_at)
        .execution_options(synchronize_session=False)
    )
    db.expire_all()
    owned_course(db, course_id, user_id)
    existing = db.get(MaterialExport, request_id)
    if existing:
        if existing.user_id != user_id:
            raise HTTPException(404, "请求标识不可用")
        if existing.course_id != course_id:
            raise HTTPException(409, "此请求标识已用于另一课程")
        db.commit()
        return response(db, existing)
    if db.get(ProcessingJob, request_id):
        raise HTTPException(409, "请求标识已使用，请使用新的标识")
    if db.scalar(
        select(MaterialExport.id)
        .join(ProcessingJob, MaterialExport.job_id == ProcessingJob.id)
        .where(
            MaterialExport.course_id == course_id,
            MaterialExport.user_id == user_id,
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
    ):
        raise HTTPException(409, "已有资料包正在生成，请查看导出记录")
    if (
        db.scalar(
            select(func.count())
            .select_from(MaterialExport)
            .where(
                MaterialExport.course_id == course_id, MaterialExport.user_id == user_id
            )
        )
        >= 20
    ):
        raise HTTPException(409, "当前课程最多保留20条导出记录，请先移除旧记录")
    if not db.scalar(
        select(Document.id)
        .where(
            Document.course_id == course_id,
            Document.user_id == user_id,
            Document.deleted_at.is_(None),
        )
        .limit(1)
    ) and not db.scalar(
        select(Asset.id).where(available_assets(user_id, course_id)).limit(1)
    ):
        raise HTTPException(409, "课程还没有可导出的资料或图片")
    job = ProcessingJob(
        id=request_id, user_id=user_id, type="MATERIAL_EXPORT", resource_id=request_id
    )
    db.add(job)
    db.flush()
    row = MaterialExport(
        id=request_id, user_id=user_id, course_id=course_id, job_id=job.id
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return response(db, row)


def retry_export(db, export_id, user_id):
    row = owned_export(db, export_id, user_id)
    db.execute(
        update(Course)
        .where(Course.id == row.course_id)
        .values(updated_at=Course.updated_at)
    )
    db.expire_all()
    row = owned_export(db, export_id, user_id)
    job = db.get(ProcessingJob, row.job_id)
    if job.status in {"QUEUED", "RUNNING"}:
        db.commit()
        return response(db, row)
    if job.status != "FAILED" or job.attempt_count >= job.max_attempts:
        raise HTTPException(409, "只有未达尝试上限的失败导出可重试")
    if db.scalar(
        select(MaterialExport.id)
        .join(ProcessingJob, MaterialExport.job_id == ProcessingJob.id)
        .where(
            MaterialExport.course_id == row.course_id,
            MaterialExport.id != row.id,
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
    ):
        raise HTTPException(409, "课程已有其他导出正在处理")
    job.status = "QUEUED"
    job.progress = 0
    job.error = None
    job.lease_until = None
    job.lease_token = None
    db.commit()
    return response(db, row)


def remove_export(db, export_id, user_id):
    row = owned_export(db, export_id, user_id)
    db.execute(
        update(Course)
        .where(Course.id == row.course_id, Course.user_id == user_id)
        .values(updated_at=Course.updated_at)
        .execution_options(synchronize_session=False)
    )
    db.expire_all()
    row = owned_export(db, export_id, user_id)
    job = db.get(ProcessingJob, row.job_id)
    if job.status in {"QUEUED", "RUNNING"}:
        job.status = "CANCELLED"
        job.lease_token = None
        job.lease_until = None
        job.error = "导出记录已移除"
    stored = row.zip_path
    db.delete(row)
    db.commit()
    if stored:
        cleanup(Path(stored))


def cleanup(path):
    try:
        path.unlink(missing_ok=True)
    except OSError:
        # Removal still revokes reads; an inaccessible orphan can be cleaned later.
        pass


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(65536):
            digest.update(block)
    return digest.hexdigest()


def download_path(db, row):
    job = db.get(ProcessingJob, row.job_id)
    if job.status != "SUCCEEDED" or not row.zip_path:
        raise HTTPException(409, "资料包尚未成功生成")
    if not sources_available(db, row):
        raise HTTPException(404, "包内来源已删除或撤回，请重新导出")
    path = Path(row.zip_path)
    expected_root = (
        Path(get_settings().storage_root) / row.user_id / row.course_id / "exports"
    ).resolve()
    if not path.resolve().is_relative_to(expected_root) or not path.is_file():
        raise HTTPException(404, "资料包文件不可用")
    if path.stat().st_size != row.size_bytes or hash_file(path) != row.sha256:
        raise HTTPException(409, "资料包文件校验失败，请重新导出")
    return path


def metadata(row, skip=()):
    result = {}
    for column in row.__table__.columns:
        if column.name in {"user_id", *skip}:
            continue
        value = getattr(row, column.name)
        if isinstance(value, datetime):
            value = (
                value.replace(tzinfo=timezone.utc).isoformat()
                if value.tzinfo is None
                else value.astimezone(timezone.utc).isoformat()
            )
        result[column.name] = value
    return result


def snapshot(db, row):
    course = owned_course(db, row.course_id, row.user_id)
    documents = db.scalars(
        select(Document)
        .where(
            Document.course_id == row.course_id,
            Document.user_id == row.user_id,
            Document.deleted_at.is_(None),
        )
        .order_by(Document.id)
        .limit(2001)
    ).all()
    if len(documents) > 2000:
        raise ValueError("课程资料超过导出预算（2000份）")
    versions = db.scalars(
        select(DocumentVersion)
        .join(Document)
        .where(
            Document.course_id == row.course_id,
            Document.user_id == row.user_id,
            Document.deleted_at.is_(None),
            DocumentVersion.user_id == row.user_id,
        )
        .order_by(DocumentVersion.document_id, DocumentVersion.version_no)
        .limit(10001)
    ).all()
    if len(versions) > 10000:
        raise ValueError("资料版本超过导出预算（10000个）")
    ids = [v.id for v in versions]
    if sum(v.size_bytes for v in versions) > MAX_CONTENT:
        raise ValueError("原件总量超过256MiB导出内容预算")
    transcripts = db.scalars(
        select(ManualTranscript)
        .where(
            ManualTranscript.version_id.in_(ids),
            ManualTranscript.user_id == row.user_id,
            ManualTranscript.status.in_(["CONFIRMED", "SUPERSEDED"]),
        )
        .order_by(ManualTranscript.id)
        .limit(MAX_CHUNKS + 1)
    ).all()
    if len(transcripts) > MAX_CHUNKS:
        raise ValueError("人工来源超过导出预算（50000条）")
    chunk_scope = (
        select(DocumentChunk)
        .join(DocumentVersion)
        .where(
            DocumentChunk.version_id.in_(ids),
            DocumentChunk.user_id == row.user_id,
            (
                (DocumentChunk.source_kind == "extracted")
                & (DocumentVersion.parse_status == "SUCCEEDED")
            )
            | select(ManualTranscript.id)
            .where(
                ManualTranscript.chunk_id == DocumentChunk.id,
                ManualTranscript.user_id == row.user_id,
                ManualTranscript.status.in_(["CONFIRMED", "SUPERSEDED"]),
            )
            .exists(),
        )
    )
    # Check UTF-8 bytes in SQLite before loading large parsed bodies into Python.
    text_bytes = (
        db.scalar(
            chunk_scope.with_only_columns(
                func.sum(func.length(cast(DocumentChunk.text, LargeBinary)))
            )
        )
        or 0
    )
    if text_bytes + sum(v.size_bytes for v in versions) > MAX_CONTENT:
        raise ValueError("原件与解析文本超过256MiB导出内容预算")
    chunks = db.scalars(
        chunk_scope.order_by(
            DocumentChunk.version_id, DocumentChunk.ordinal, DocumentChunk.id
        ).limit(MAX_CHUNKS + 1)
    ).all()
    if len(chunks) > MAX_CHUNKS:
        raise ValueError("资料切片超过导出预算（50000个）")
    assets = db.scalars(
        select(Asset)
        .where(available_assets(row.user_id, row.course_id))
        .order_by(Asset.id)
        .limit(10001)
    ).all()
    if len(assets) > 10000:
        raise ValueError("图片超过导出预算（10000张）")
    manifest = {
        "format": "hustudy-material-package",
        "schema_version": 1,
        "scope": "course_materials",
        "snapshot_at": utc_now().isoformat(),
        "course": metadata(course),
        "documents": [metadata(d, ("storage_path",)) for d in documents],
        "versions": [],
        "chunks": [],
        "transcripts": [],
        "assets": [],
        "files": [],
    }
    files = []
    for version in versions:
        value = metadata(
            version, ("source_path", "preview_path", "parse_error", "preview_error")
        )
        suffix = Path(version.original_filename).suffix.lower()
        if suffix not in {".pdf", ".pptx", ".docx", ".md", ".markdown", ".txt"}:
            raise ValueError("原件格式不在资料包支持范围")
        member = f"originals/{version.id}{suffix}"
        value["original_file"] = member
        value["preview_file"] = None
        files.append(
            (member, Path(version.source_path), version.size_bytes, version.sha256)
        )
        if version.preview_status == "SUCCEEDED" and version.preview_path:
            if (
                Path(version.preview_path).resolve()
                == Path(version.source_path).resolve()
            ):
                value["preview_file"] = member
            else:
                member = f"previews/{version.id}.pdf"
                value["preview_file"] = member
                files.append((member, Path(version.preview_path), None, None))
        manifest["versions"].append(value)
    text_by_chunk = {}
    for chunk in chunks:
        body = chunk.text.encode("utf-8")
        member = f"text/{chunk.id}.txt"
        text_by_chunk[chunk.id] = chunk.text
        value = metadata(chunk, ("text",))
        value.update(
            text_file=member,
            text_sha256=hashlib.sha256(body).hexdigest(),
            unicode_length=len(chunk.text),
        )
        manifest["chunks"].append(value)
        files.append((member, body, len(body), value["text_sha256"]))
    for transcript in transcripts:
        if (
            text_by_chunk.get(transcript.chunk_id) != transcript.text
            or hashlib.sha256(transcript.text.encode("utf-8")).hexdigest()
            != transcript.text_hash
        ):
            raise ValueError("人工来源与确认切片不一致，请先排查资料")
        value = metadata(transcript, ("text",))
        value["text_file"] = f"text/{transcript.chunk_id}.txt"
        manifest["transcripts"].append(value)
    for asset in assets:
        suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(
            asset.mime_type
        )
        if not suffix:
            raise ValueError("图片格式不在导出范围")
        member = f"assets/{asset.id}{suffix}"
        value = metadata(asset, ("storage_path",))
        value["file"] = member
        manifest["assets"].append(value)
        files.append((member, Path(asset.storage_path), asset.size_bytes, asset.sha256))
    sources = {
        "documents": [d.id for d in documents],
        "assets": [a.id for a in assets],
        "transcripts": [t.id for t in transcripts],
    }
    return manifest, files, sources


def build_package(db, row, output):
    from ..core.storage import check_capacity, LocalFileStorage, map_disk_error

    # An explicit read transaction gives all tables one WAL snapshot.
    connection = db.connection()
    if not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN")
    manifest, files, sources = snapshot(db, row)
    if len(files) + 2 > 70000:
        raise ValueError("资料包成员超过70000个预算")
    root = (Path(get_settings().storage_root) / row.user_id / row.course_id).resolve()
    started = time.monotonic()
    total = 0
    try:
        LocalFileStorage(Path(get_settings().storage_root)).checked(output)
        estimate = sum(
            source.stat().st_size if isinstance(source, Path) else len(source)
            for _, source, _, _ in files
        )
        check_capacity(output.parent, estimate + MAX_METADATA + 2 * 1024 * 1024)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(
            output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1
        ) as archive:
            for member, source, expected_size, expected_hash in files:
                check_capacity(output.parent)
                digest = hashlib.sha256()
                size = 0
                if isinstance(source, Path):
                    if (
                        not source.resolve().is_relative_to(root)
                        or not source.is_file()
                    ):
                        raise ValueError("资料文件缺失或不在当前课程存储范围")
                    stream = source.open("rb")
                else:
                    from io import BytesIO

                    stream = BytesIO(source)
                with stream, archive.open(member, "w") as target:
                    while block := stream.read(65536):
                        total += len(block)
                        size += len(block)
                        if (
                            total > MAX_CONTENT
                            or time.monotonic() - started > EXPORT_SECONDS
                        ):
                            raise ValueError(
                                "导出超过256MiB内容或120秒预算，请缩小资料范围"
                            )
                        digest.update(block)
                        target.write(block)
                actual_hash = digest.hexdigest()
                if (expected_size is not None and size != expected_size) or (
                    expected_hash is not None and actual_hash != expected_hash
                ):
                    raise ValueError("资料文件大小或hash与来源记录不符，请先排查原件")
                manifest["files"].append(
                    {"path": member, "size_bytes": size, "sha256": actual_hash}
                )
            encoded = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
            if len(encoded) > MAX_METADATA or total + len(encoded) > MAX_CONTENT:
                raise ValueError("导出元数据超过16MiB或总内容预算")
            archive.writestr("manifest.json", encoded)
            archive.writestr(
                "README.md",
                "# Hustudy 课程资料包\n\n包含未删除资料的各版本原件、可用预览、解析文本、已确认人工补录及有效图片。\n\nmanifest.json 保存UUID、版本、定位、Unicode偏移、每文件SHA-256与字节数；text为UTF-8。人工文字明确标manual_transcript，DOCX正文按block，预览页不等于Word页码。\n\n不含笔记、AI结果、真题/试卷/作答或复习记录；不是完整账户备份，当前不能恢复导入。未识别图中文字不作为正文。快照仅反映生成时状态。\n\n可在项目目录执行：python3 scripts/verify_material_package.py /path/to/package.zip\n",
            )
        counts = {
            key: len(manifest[key])
            for key in (
                "documents",
                "versions",
                "chunks",
                "transcripts",
                "assets",
                "files",
            )
        }
        return {
            "sources": sources,
            "counts": counts,
            "snapshot_at": datetime.fromisoformat(manifest["snapshot_at"]),
            "sha256": hash_file(output),
            "size_bytes": output.stat().st_size,
        }
    except OSError as error:
        cleanup(output)
        map_disk_error(error)
    except Exception:
        cleanup(output)
        raise
    finally:
        db.rollback()
