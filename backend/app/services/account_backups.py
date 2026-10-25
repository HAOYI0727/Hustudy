"""Account archive coordinator: module adapters, immutable blobs, atomic restore."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import time
from uuid import UUID
from zoneinfo import ZoneInfo
import zipfile

from fastapi import HTTPException
from sqlalchemy import select, update, func
from ..core import backup_contract as contract
from ..core.config import get_settings, get_user_settings
from ..core.storage import LocalFileStorage, check_capacity, map_disk_error
from ..models import User, Course, ProcessingJob, AccountArchive
from . import material_backup, note_backup, ai_backup, exam_backup

ADAPTERS = [material_backup, note_backup, ai_backup, exam_backup]
MODELS = [Course]
REVISION = "0021_bank_library"
LEGACY_REVISION = "0012_account_archives"
MAX_ZIP = 256 * 1024 * 1024
MAX_CONTENT = 512 * 1024 * 1024
MAX_MEMBERS = 70000
SECONDS = 120


def storage():
    return LocalFileStorage(Path(get_settings().storage_root))


def archive_path(user_id, archive_id, suffix=".zip"):
    return storage().checked(
        storage().root
        / str(UUID(user_id))
        / ".archives"
        / (str(UUID(archive_id)) + suffix)
    )


def hash_file(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(65536):
            result.update(block)
    return result.hexdigest()


def empty(db, user_id):
    contract.assert_empty(db, user_id, MODELS)
    for adapter in ADAPTERS:
        adapter.empty(db, user_id)


def owned(db, user_id, archive_id):
    row = db.scalar(
        select(AccountArchive).where(
            AccountArchive.id == archive_id, AccountArchive.user_id == user_id
        )
    )
    if not row:
        raise HTTPException(404, "备份任务不存在")
    return row


def active_sources(db, user_id, sources):
    material_backup.require_sources(db, user_id, sources)


def response(db, row):
    job = db.get(ProcessingJob, row.job_id)
    return {
        "id": row.id,
        "purpose": row.purpose,
        "created_at": row.created_at,
        "sha256": row.sha256,
        "size_bytes": row.size_bytes,
        "counts": row.counts,
        "job": {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "error": job.error,
        },
    }


def create(db, user_id, purpose, upload=None):
    # Serialize competing control tasks; business mutations are rechecked in the worker.
    db.execute(
        update(User).where(User.id == user_id).values(updated_at=User.updated_at)
    )
    if (
        db.scalar(
            select(func.count())
            .select_from(AccountArchive)
            .where(AccountArchive.user_id == user_id)
        )
        or 0
    ) >= 50:
        raise HTTPException(409, "最多保留50条备份恢复记录，请先移除不再需要的记录")
    if db.scalar(
        select(ProcessingJob.id).where(
            ProcessingJob.user_id == user_id,
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
            ProcessingJob.type.in_(["ACCOUNT_BACKUP", "ACCOUNT_RESTORE"]),
        )
    ):
        raise HTTPException(409, "账户已有备份或恢复正在执行")
    if purpose == "restore":
        try:
            empty(db, user_id)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
    elif db.scalar(
        select(ProcessingJob.id).where(
            ProcessingJob.user_id == user_id,
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
    ):
        raise HTTPException(409, "请先等待或取消正在运行的资料/AI任务，再生成完整备份")
    row = AccountArchive(user_id=user_id, purpose=purpose, counts={}, sources={})
    job = ProcessingJob(
        user_id=user_id,
        type="ACCOUNT_RESTORE" if purpose == "restore" else "ACCOUNT_BACKUP",
        max_attempts=1,
    )
    db.add(job)
    db.flush()
    row.job_id = job.id
    db.add(row)
    db.flush()
    job.resource_id = row.id
    path = None
    published = False
    try:
        if upload is not None:
            upload.file.seek(0, 2)
            size = upload.file.tell()
            upload.file.seek(0)
            if not 0 < size <= MAX_ZIP:
                raise HTTPException(422, "备份ZIP不能为空且不能超过256MiB")
            path = archive_path(user_id, row.id, ".input.zip")
            storage().write_stream(path, upload.file, size)
            published = True
            row.artifact_path, row.size_bytes = str(path), size
        db.commit()
        return row
    except Exception:
        db.rollback()
        if path and published:
            path.unlink(missing_ok=True)
        raise


def export_package(db, user_id, output):
    connection = db.connection()
    if not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN")
    if db.scalar(
        select(ProcessingJob.id).where(
            ProcessingJob.user_id == user_id,
            ProcessingJob.type.not_in(["ACCOUNT_BACKUP", "ACCOUNT_RESTORE"]),
            ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
        )
    ):
        raise ValueError("仍有运行中的业务任务，请等待完成后重新备份")
    tables = contract.serialize(db, user_id, MODELS)
    files = []
    for adapter in ADAPTERS:
        values, attachments = adapter.snapshot(db, user_id)
        tables.update(values)
        files.extend(attachments)
    contract.ids(tables)
    user = db.get(User, user_id)
    manifest = {
        "format": "hustudy-account-v1",
        "schema_revision": REVISION,
        "source_user_id": user_id,
        "timezone": user.timezone,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tables": tables,
        "files": [],
        "omitted": [
            "account credentials",
            "configuration secrets",
            "derived material ZIP bytes",
        ],
    }
    if len(files) + 1 > MAX_MEMBERS:
        raise ValueError("备份文件数量超过预算")
    estimate = sum(item["source"].stat().st_size for item in files)
    if estimate > MAX_CONTENT:
        raise ValueError("备份文件超过512MiB预算")
    check_capacity(output.parent, estimate + contract.MAX_METADATA + 2 * 1024 * 1024)
    output.parent.mkdir(parents=True, exist_ok=True)
    started, total = time.monotonic(), 0
    try:
        with zipfile.ZipFile(
            output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1
        ) as archive:
            for item in files:
                digest, size = hashlib.sha256(), 0
                check_capacity(output.parent)
                with (
                    item["source"].open("rb") as source,
                    archive.open(item["member"], "w") as target,
                ):
                    while block := source.read(65536):
                        total += len(block)
                        size += len(block)
                        if total > MAX_CONTENT or time.monotonic() - started > SECONDS:
                            raise ValueError("账户备份超过内容或时间预算")
                        digest.update(block)
                        target.write(block)
                actual = digest.hexdigest()
                if item["expected_hash"] and item["expected_hash"] != actual:
                    raise ValueError("备份原件hash不符，请核对存储")
                manifest["files"].append(
                    {key: item[key] for key in ("id", "member", "course_id", "suffix")}
                    | {"sha256": actual, "size_bytes": size}
                )
            material_backup.verify_files(tables, manifest["files"])
            material_backup.verify_citations(tables, tables["citations"])
            encoded = json.dumps(manifest, ensure_ascii=False, allow_nan=False).encode()
            if len(encoded) > contract.MAX_METADATA:
                raise ValueError("账户备份清单超过16MiB预算")
            for secret in (
                get_settings().jwt_secret,
                get_settings().zhipu_api_key.get_secret_value(),
                get_user_settings(user_id).zhipu_api_key.get_secret_value(),
            ):
                if secret and secret.encode() in encoded:
                    raise ValueError(
                        "备份文本包含当前服务凭据，请从业务内容中移除后重试"
                    )
            archive.writestr("manifest.json", encoded)
        if output.stat().st_size > MAX_ZIP:
            raise ValueError("压缩备份超过256MiB预算")
        sources = {
            "versions": [
                row["id"] for row in tables["document_versions"] if row["source_path"]
            ],
            "assets": [row["id"] for row in tables["assets"] if row["storage_path"]],
            "transcripts": [
                row["id"]
                for row in tables["manual_transcripts"]
                if row["text"] and row["status"] in {"CONFIRMED", "SUPERSEDED"}
            ],
        }
        return {
            "counts": {key: len(rows) for key, rows in tables.items()},
            "sources": sources,
            "sha256": hash_file(output),
            "size_bytes": output.stat().st_size,
        }
    except OSError as error:
        output.unlink(missing_ok=True)
        map_disk_error(error)
    except Exception:
        output.unlink(missing_ok=True)
        raise


def inspect_package(path):
    if path.stat().st_size > MAX_ZIP:
        raise ValueError("备份ZIP超过256MiB")
    archive = zipfile.ZipFile(path)
    try:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if (
            len(infos) > MAX_MEMBERS
            or len(set(names)) != len(names)
            or "manifest.json" not in names
        ):
            raise ValueError("备份ZIP成员缺失、重复或超限")
        if sum(item.file_size for item in infos) > MAX_CONTENT + contract.MAX_METADATA:
            raise ValueError("备份解压内容超过预算")
        for info in infos:
            if (
                info.flag_bits & 1
                or stat.S_ISLNK(info.external_attr >> 16)
                or info.filename.startswith("/")
                or ".." in Path(info.filename).parts
                or "\\" in info.filename
            ):
                raise ValueError("备份包含不安全的文件路径/加密/符号链接")
        if archive.getinfo("manifest.json").file_size > contract.MAX_METADATA:
            raise ValueError("备份清单超过16MiB预算")
        manifest = contract.strict_json(archive.read("manifest.json"))
        if (
            set(manifest)
            != {
                "format",
                "schema_revision",
                "source_user_id",
                "timezone",
                "created_at",
                "tables",
                "files",
                "omitted",
            }
            or manifest["format"] != "hustudy-account-v1"
            or manifest["schema_revision"]
            not in (
                LEGACY_REVISION,
                "0013_note_tags",
                "0014_note_exports",
                "0015_note_folders",
                "0016_note_trash",
                "0019_exam_bank",
                "0020_exam_analysis",
                REVISION,
            )
        ):
            raise ValueError("备份格式或数据库版本不兼容")
        if not isinstance(manifest["tables"], dict) or not isinstance(
            manifest["files"], list
        ):
            raise ValueError("备份结构不正确")
        UUID(manifest["source_user_id"])
        ZoneInfo(manifest["timezone"])
        expected = {model.__tablename__ for model in MODELS}
        for adapter in ADAPTERS:
            expected.update(model.__tablename__ for model in adapter.MODELS)
        if manifest["schema_revision"] not in (
            "0015_note_folders",
            "0016_note_trash",
            "0019_exam_bank",
            "0020_exam_analysis",
            REVISION,
        ):
            expected.remove("note_folders")
        if manifest["schema_revision"] not in (
            "0016_note_trash",
            "0019_exam_bank",
            "0020_exam_analysis",
            REVISION,
        ):
            expected.remove("note_trash_policies")
        if manifest["schema_revision"] not in ("0020_exam_analysis", REVISION):
            expected.remove("exam_analysis_reports")
        if set(manifest["tables"]) != expected:
            raise ValueError("备份模块集合不完整或包含未知表")
        if manifest["schema_revision"] == LEGACY_REVISION:
            note_backup.upgrade_legacy_tags(manifest["tables"])
        if manifest["schema_revision"] not in (
            "0015_note_folders",
            "0016_note_trash",
            "0019_exam_bank",
            "0020_exam_analysis",
            REVISION,
        ):
            note_backup.upgrade_legacy_folders(manifest["tables"])
        if manifest["schema_revision"] not in (
            "0016_note_trash",
            "0019_exam_bank",
            "0020_exam_analysis",
            REVISION,
        ):
            note_backup.upgrade_legacy_trash(manifest["tables"])
        if manifest["schema_revision"] not in (
            "0019_exam_bank",
            "0020_exam_analysis",
            REVISION,
        ):
            exam_backup.upgrade_legacy(manifest["tables"])
        if manifest["schema_revision"] not in ("0020_exam_analysis", REVISION):
            exam_backup.upgrade_legacy_analysis(manifest["tables"])
        if manifest["schema_revision"] != REVISION:
            for doc in manifest["tables"]["documents"]:
                doc.setdefault("library_scope", "material")
        all_ids = contract.ids(manifest["tables"])
        members, file_ids = {"manifest.json"}, set()
        for item in manifest["files"]:
            if set(item) != {
                "id",
                "member",
                "course_id",
                "suffix",
                "sha256",
                "size_bytes",
            }:
                raise ValueError("备份文件字段不正确")
            UUID(item["id"])
            if (
                item["id"] in file_ids
                or item["suffix"]
                not in {
                    ".pptx",
                    ".pdf",
                    ".docx",
                    ".md",
                    ".markdown",
                    ".txt",
                    ".png",
                    ".jpg",
                    ".webp",
                }
                or item["member"] != "files/" + item["id"] + item["suffix"]
            ):
                raise ValueError("备份文件标识或类型不正确")
            if (
                item["course_id"] is not None
                and item["course_id"] not in all_ids["courses"]
            ):
                raise ValueError("备份文件缺少所属课程")
            if (
                type(item["size_bytes"]) is not int
                or item["size_bytes"] < 0
                or not isinstance(item["sha256"], str)
                or len(item["sha256"]) != 64
            ):
                raise ValueError("备份文件大小或hash格式不正确")
            if archive.getinfo(item["member"]).file_size != item["size_bytes"]:
                raise ValueError("备份文件大小不一致")
            file_ids.add(item["id"])
            members.add(item["member"])
        if set(names) != members:
            raise ValueError("备份ZIP含清单以外或缺失文件")
        return archive, manifest, all_ids
    except Exception:
        archive.close()
        raise


def cleanup_restore(user_id, archive_id):
    root = storage().root / user_id
    if root.exists():
        for path in root.rglob("restore-" + archive_id + "-*"):
            storage().checked(path).unlink(missing_ok=True)


def restore_package(db, user_id, record):
    empty(db, user_id)
    source = storage().checked(Path(record.artifact_path))
    archive, manifest, all_ids = inspect_package(source)
    paths = {
        "file:" + item["id"]: storage().checked(
            storage().root
            / user_id
            / (item["course_id"] or "_global")
            / ("restore-" + record.id + "-" + item["id"] + item["suffix"])
        )
        for item in manifest["files"]
    }
    try:
        material_backup.verify_files(manifest["tables"], manifest["files"])
        material_backup.verify_citations(
            manifest["tables"], manifest["tables"]["citations"]
        )
        decoded = contract.validate(
            db,
            user_id,
            manifest["source_user_id"],
            MODELS,
            manifest["tables"],
            all_ids,
            paths,
        )
        groups = [
            adapter.validate(
                db,
                user_id,
                manifest["source_user_id"],
                manifest["tables"],
                all_ids,
                paths,
            )
            for adapter in ADAPTERS
        ]
        check_capacity(
            storage().root, sum(item["size_bytes"] for item in manifest["files"])
        )
        started = time.monotonic()
        for item in manifest["files"]:
            path = paths["file:" + item["id"]]
            with archive.open(item["member"]) as stream:
                storage().write_stream(path, stream, item["size_bytes"])
            if hash_file(path) != item["sha256"]:
                raise ValueError("恢复文件hash校验失败")
            if time.monotonic() - started > SECONDS:
                raise ValueError("恢复超过120秒预算")
        contract.apply(db, MODELS, decoded)
        for adapter, group in zip(ADAPTERS, groups):
            adapter.apply(db, group)
        db.get(User, user_id).timezone = manifest["timezone"]
        return {key: len(rows) for key, rows in manifest["tables"].items()}
    except Exception:
        cleanup_restore(user_id, record.id)
        raise
    finally:
        archive.close()


def remove(db, user_id, archive_id):
    row = owned(db, user_id, archive_id)
    job = db.get(ProcessingJob, row.job_id)
    if job.status in {"QUEUED", "RUNNING"}:
        raise HTTPException(409, "运行中的备份或恢复不能移除，请等待结束")
    path = storage().checked(Path(row.artifact_path)) if row.artifact_path else None
    db.delete(job)
    db.commit()
    if path:
        path.unlink(missing_ok=True)
