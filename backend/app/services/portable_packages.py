"""Bounded ZIP transport and atomic, idempotent portable-content imports."""

from copy import deepcopy
from datetime import timedelta
import hashlib
import io
import json
import logging
from pathlib import Path
import re
import stat
import struct
import time
import unicodedata
from uuid import UUID, uuid4
import warnings
import zipfile
import zlib

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select

from ..core.backup_contract import strict_json
from ..core.config import get_settings
from ..core.database import begin_read_snapshot
from ..core.storage import LocalFileStorage, check_capacity
from ..models import PackageImport, PackagePreview
from ..models.base import utc_now
from . import portable_content as content
from .courses import owned_course
from .note_export_names import safe_name
from .note_folders import lock_owner

MAX_ZIP = 100 * 1024 * 1024
MAX_CONTENT = 256 * 1024 * 1024
MAX_MEMBERS = 3000
MAX_METADATA = 8 * 1024 * 1024
MAX_FILE = 30 * 1024 * 1024
MAX_IMAGE = 10 * 1024 * 1024
MAX_RATIO = 200
SECONDS = 120
PREVIEW_HOURS = 24
MAX_PREVIEWS = 10
FORMAT = "hustudy-package-v1"
SUFFIXES = {
    ".pdf",
    ".docx",
    ".pptx",
    ".md",
    ".markdown",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}
logger = logging.getLogger(__name__)


class SelectionChanged(HTTPException):
    error_code = "PACKAGE_SELECTION_CHANGED"

    def __init__(self):
        super().__init__(409, "所选内容或依赖已改变，请重新核对范围后确认")


def storage():
    return LocalFileStorage(Path(get_settings().storage_root))


def deadline_check(deadline):
    if time.monotonic() > deadline:
        raise ValueError("包处理超过120秒预算，请减少所选内容后重试")


def control_path(user_id, key, suffix=".zip"):
    return storage().checked(
        storage().root / str(UUID(user_id)) / ".packages" / (str(UUID(key)) + suffix)
    )


def cleanup_file(path):
    try:
        storage().remove(path)
    except OSError:
        # Cleanup must not turn a committed success into a retryable failure.
        logger.warning("portable package temporary file cleanup deferred")


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def fingerprint(payload):
    value = payload.model_dump(mode="json", exclude={"request_id"})
    value["selection"] = {key: sorted(ids) for key, ids in value["selection"].items()}
    return hashlib.sha256(canonical(value)).hexdigest()


def selection_json(payload):
    return {
        key: [str(value) for value in values]
        for key, values in payload.selection.items()
    }


def selection_digest(manifest):
    """Stable across snapshot-local file UUIDs; covers contents and dependencies."""
    normalized = deepcopy(manifest)
    blobs = {
        "file:" + item["id"]: {
            key: value for key, value in item.items() if key not in {"id", "member"}
        }
        for item in manifest["files"]
    }
    for rows in normalized["tables"].values():
        rows.sort(key=lambda row: row["id"])
        for row in rows:
            for field in ("source_path", "storage_path", "preview_path", "zip_path"):
                if row.get(field) in blobs:
                    row[field] = blobs[row[field]]
    normalized["files"] = sorted(blobs.values(), key=canonical)
    normalized["warnings"] = sorted(set(normalized["warnings"]))
    return hashlib.sha256(canonical(normalized)).hexdigest()


def check_confirmation(manifest, expected):
    if expected is not None and selection_digest(manifest) != expected:
        raise SelectionChanged()


def _central_budget(stream, size, *, members=MAX_MEMBERS):
    """Reject huge central directories before ZipFile allocates every entry."""
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or len(tail) - offset < 22:
        raise ValueError("ZIP结构不完整")
    _, disk, central_disk, on_disk, count, central_size, central_offset, comment = (
        struct.unpack_from("<4s4H2LH", tail, offset)
    )
    if (
        disk
        or central_disk
        or on_disk != count
        or count > members
        or count == 65535
        or central_size > members * 1024
        or central_offset + central_size > size
        or offset + 22 + comment != len(tail)
    ):
        raise ValueError("ZIP成员、目录或分卷结构超过预算")
    stream.seek(0)
    return count


def _member_name(info):
    name = info.filename
    if (
        not name
        or len(name) > 500
        or info.orig_filename != name
        or "\\" in name
        or name.startswith("/")
        or info.is_dir()
        or ":" in name
        or any(unicodedata.category(c).startswith("C") for c in name)
    ):
        raise ValueError("ZIP路径不安全或包含冒名目录")
    parts = name.split("/")
    if any(not p or p in {".", ".."} or p.endswith((".", " ")) for p in parts):
        raise ValueError("ZIP路径不安全")
    normalized = unicodedata.normalize("NFKC", name).casefold()
    if (
        any(p in {".", ".."} for p in normalized.split("/"))
        or "\\" in normalized
        or ":" in normalized
    ):
        raise ValueError("ZIP路径规范化后不安全")
    mode = info.external_attr >> 16
    if (
        stat.S_IFMT(mode) not in {0, stat.S_IFREG}
        or info.flag_bits & 1
        or info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
        or len(info.extra) > 1024
    ):
        raise ValueError("ZIP含链接、加密或不支持的成员")
    return normalized


def _read_member(archive, info, limit, deadline):
    if info.file_size > limit:
        raise ValueError("ZIP单文件超过安全预算")
    output = io.BytesIO()
    with archive.open(info) as stream:
        while block := stream.read(65536):
            deadline_check(deadline)
            if (
                output.tell() + len(block) > limit
                or output.tell() + len(block) > info.file_size
            ):
                raise ValueError("ZIP成员实际大小超过声明或预算")
            output.write(block)
    if output.tell() != info.file_size:
        raise ValueError("ZIP成员大小不符")
    return output.getvalue()


def _file_type(data, suffix, deadline):
    deadline_check(deadline)
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        if len(data) > MAX_IMAGE:
            raise ValueError("图片超过10MiB预算")
        expected = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}[
            suffix
        ]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as image:
                    if (
                        image.format != expected
                        or image.width * image.height > 20_000_000
                        or getattr(image, "n_frames", 1) != 1
                    ):
                        raise ValueError("图片实际格式、尺寸或帧数不合法")
                    image.verify()
                with Image.open(io.BytesIO(data)) as image:
                    image.load()
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as error:
            raise ValueError("图片损坏或超过安全预算") from error
    elif suffix in {".md", ".markdown", ".txt"}:
        if b"\0" in data:
            raise ValueError("文本文件含非法空字符")
        try:
            data.decode("utf-8-sig", errors="strict")
        except UnicodeError as error:
            raise ValueError("文本文件必须为UTF-8编码") from error
    elif suffix == ".pdf":
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
            raise ValueError("PDF实际格式不正确")
    elif suffix in {".docx", ".pptx"}:
        stream = io.BytesIO(data)
        _central_budget(stream, len(data), members=6000)
        with zipfile.ZipFile(stream) as office:
            entries = office.infolist()
            names, expanded = set(), 0
            for entry in entries:
                # Office containers legitimately contain directory entries.
                if entry.is_dir():
                    continue
                key = _member_name(entry)
                if key in names:
                    raise ValueError("Office文件含重复成员")
                names.add(key)
                expanded += entry.file_size
                if (
                    expanded > 128 * 1024 * 1024
                    or entry.file_size > MAX_FILE
                    or entry.file_size > MAX_RATIO * max(1, entry.compress_size)
                ):
                    raise ValueError("Office文件解压预算过大")
            primary = (
                "word/document.xml" if suffix == ".docx" else "ppt/presentation.xml"
            )
            if (
                primary not in names
                or "[content_types].xml" not in names
                or any("vbaproject" in name for name in names)
            ):
                raise ValueError("Office实际格式与后缀不一致")
            types = _read_member(
                office, office.getinfo("[Content_Types].xml"), 1024 * 1024, deadline
            )
            marker = (
                b"wordprocessingml.document.main+xml"
                if suffix == ".docx"
                else b"presentationml.presentation.main+xml"
            )
            if marker not in types or b"<!DOCTYPE" in types.upper():
                raise ValueError("Office内容类型不受支持")
    deadline_check(deadline)


def inspect_package(stream, *, deadline=None):
    """Validate every declared byte, including unselected members, without extracting."""
    deadline = deadline or time.monotonic() + SECONDS
    stream.seek(0, 2)
    size = stream.tell()
    if not 0 < size <= MAX_ZIP:
        raise ValueError("标准ZIP不能为空且不能超过100MiB")
    count = _central_budget(stream, size)
    try:
        with zipfile.ZipFile(stream) as archive:
            entries = archive.infolist()
            if len(entries) != count or len(entries) > MAX_MEMBERS:
                raise ValueError("ZIP成员数量不符或超过3000项")
            normalized, expanded = set(), 0
            for info in entries:
                key = _member_name(info)
                if key in normalized or any(
                    key.startswith(parent + "/") for parent in normalized
                ):
                    raise ValueError("ZIP含重复名称或文件目录冲突")
                if any(parent.startswith(key + "/") for parent in normalized):
                    raise ValueError("ZIP含文件目录冲突")
                normalized.add(key)
                expanded += info.file_size
                if (
                    expanded > MAX_CONTENT
                    or info.file_size > MAX_FILE
                    or info.file_size > MAX_RATIO * max(1, info.compress_size)
                ):
                    raise ValueError("ZIP解压大小或压缩比超过安全预算")
                deadline_check(deadline)
            if "manifest.json" not in archive.namelist():
                raise ValueError(
                    "缺少标准包manifest.json；普通阅读ZIP请使用Markdown导入"
                )
            manifest = strict_json(
                _read_member(
                    archive, archive.getinfo("manifest.json"), MAX_METADATA, deadline
                )
            )
            if (
                not isinstance(manifest, dict)
                or manifest.get("format") != FORMAT
                or set(manifest)
                != {
                    "format",
                    "kind",
                    "source_course_id",
                    "source_user_id",
                    "course",
                    "tables",
                    "files",
                    "warnings",
                }
            ):
                raise ValueError("不支持的包格式、版本或清单字段")
            files = manifest["files"]
            if not isinstance(files, list) or len(files) >= MAX_MEMBERS:
                raise ValueError("文件清单不合法或超过预算")
            declared = {"manifest.json"}
            for item in files:
                if not isinstance(item, dict) or set(item) != {
                    "id",
                    "member",
                    "course_id",
                    "suffix",
                    "sha256",
                    "size_bytes",
                }:
                    raise ValueError("文件清单字段不合法")
                key = item["id"]
                if not isinstance(key, str) or str(UUID(key)) != key:
                    raise ValueError("文件ID必须是规范UUID")
                if (
                    item["suffix"] not in SUFFIXES
                    or item["member"] != "files/" + key + item["suffix"]
                    or item["member"] in declared
                    or type(item["size_bytes"]) is not int
                    or not 0 < item["size_bytes"] <= MAX_FILE
                    or not isinstance(item["sha256"], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
                ):
                    raise ValueError("文件路径、大小或SHA-256不合法")
                declared.add(item["member"])
            if declared != set(archive.namelist()):
                raise ValueError("ZIP存在缺失或未声明文件")
            content.validate_manifest(manifest)
            for item in files:
                info = archive.getinfo(item["member"])
                if info.file_size != item["size_bytes"]:
                    raise ValueError("文件大小与清单不一致")
                data = _read_member(archive, info, MAX_FILE, deadline)
                if hashlib.sha256(data).hexdigest() != item["sha256"]:
                    raise ValueError("文件SHA-256校验失败")
                _file_type(data, item["suffix"], deadline)
            deadline_check(deadline)
            return manifest
    except (
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        KeyError,
        TypeError,
        RecursionError,
        UnicodeError,
        OverflowError,
        zlib.error,
        EOFError,
    ) as error:
        raise ValueError("标准ZIP损坏或清单结构不合法") from error


def _hash_stream(stream, deadline):
    stream.seek(0)
    digest, size = hashlib.sha256(), 0
    while block := stream.read(65536):
        size += len(block)
        if size > MAX_ZIP:
            raise ValueError("标准ZIP超过100MiB")
        deadline_check(deadline)
        digest.update(block)
    stream.seek(0)
    return digest.hexdigest(), size


def _preview(db, user_id, preview_id):
    row = db.scalar(
        select(PackagePreview).where(
            PackagePreview.id == str(preview_id), PackagePreview.user_id == user_id
        )
    )
    if row is None:
        raise HTTPException(404, "包预览不存在")
    if row.expires_at <= utc_now():
        raise HTTPException(410, "包预览已过期，请重新上传核对")
    expected = control_path(user_id, row.id)
    if Path(row.artifact_path) != expected or not expected.is_file():
        raise HTTPException(409, "预览文件已不可用，请重新上传")
    return row, expected


def preview_manifest(db, user_id, preview_id, deadline):
    row, path = _preview(db, user_id, preview_id)
    with path.open("rb") as stream:
        digest, size = _hash_stream(stream, deadline)
        if digest != row.sha256 or size != row.size_bytes:
            raise ValueError("预览ZIP已改变，请重新上传核对")
        return inspect_package(stream, deadline=deadline)


def _cleanup_expired(db, user_id):
    rows = db.scalars(
        select(PackagePreview)
        .where(
            PackagePreview.user_id == user_id, PackagePreview.expires_at <= utc_now()
        )
        .order_by(PackagePreview.expires_at)
        .limit(25)
    ).all()
    paths = []
    for row in rows:
        paths.append(control_path(user_id, row.id))
        db.delete(row)
    return paths


def create_preview(db, user_id, upload):
    deadline = time.monotonic() + SECONDS
    manifest = inspect_package(upload.file, deadline=deadline)
    digest, size = _hash_stream(upload.file, deadline)
    key, path, stale = str(uuid4()), None, []
    try:
        lock_owner(db, user_id)
        stale = _cleanup_expired(db, user_id)
        db.flush()
        count = db.scalar(
            select(func.count())
            .select_from(PackagePreview)
            .where(PackagePreview.user_id == user_id)
        )
        if count >= MAX_PREVIEWS:
            raise HTTPException(409, "最多保留10份未过期预览，请先移除旧预览")
        path = control_path(user_id, key)
        storage().write_stream(path, upload.file, size)
        deadline_check(deadline)
        row = PackagePreview(
            id=key,
            user_id=user_id,
            artifact_path=str(path),
            sha256=digest,
            size_bytes=size,
            expires_at=utc_now() + timedelta(hours=PREVIEW_HOURS),
        )
        db.add(row)
        db.commit()
        for old in stale:
            cleanup_file(old)
        return content.catalog(manifest) | {
            "preview_id": key,
            "sha256": digest,
            "expires_at": row.expires_at,
        }
    except Exception:
        db.rollback()
        if path:
            cleanup_file(path)
        raise


def remove_preview(db, user_id, preview_id):
    lock_owner(db, user_id)
    row = db.scalar(
        select(PackagePreview).where(
            PackagePreview.id == str(preview_id), PackagePreview.user_id == user_id
        )
    )
    if row is None:
        raise HTTPException(404, "包预览不存在")
    path = control_path(user_id, row.id)
    db.delete(row)
    db.commit()
    cleanup_file(path)


def list_previews(db, user_id):
    rows = db.scalars(
        select(PackagePreview)
        .where(PackagePreview.user_id == user_id)
        .order_by(PackagePreview.created_at.desc(), PackagePreview.id)
        .limit(MAX_PREVIEWS + 25)
    ).all()
    return [
        {
            "id": row.id,
            "created_at": row.created_at,
            "expires_at": row.expires_at,
            "size_bytes": row.size_bytes,
            "sha256": row.sha256,
        }
        for row in rows
    ]


def source_catalog(db, user_id, course_id, kind, folder_id):
    if kind == "course" and folder_id is not None:
        raise ValueError("课程包不能同时指定笔记文件夹")
    begin_read_snapshot(db)
    manifest, _files = content.snapshot(
        db,
        user_id,
        str(course_id),
        kind=kind,
        folder_id=str(folder_id) if folder_id else None,
    )
    return content.catalog(manifest)


def selection_preview(db, user_id, payload):
    deadline = time.monotonic() + SECONDS
    if payload.preview_id:
        manifest = preview_manifest(db, user_id, payload.preview_id, deadline)
    else:
        begin_read_snapshot(db)
        manifest, _files = content.snapshot(
            db,
            user_id,
            str(payload.course_id),
            kind=payload.kind,
            folder_id=str(payload.folder_id) if payload.folder_id else None,
        )
    subset, notes = content.select_content(manifest, selection_json(payload))
    if payload.preview_id:
        target = (
            str(payload.target_course_id) if payload.target_course_id else str(uuid4())
        )
        if subset["kind"] == "folder" and not payload.target_course_id:
            raise ValueError("文件夹包请选择目标课程")
        if payload.target_course_id:
            owned_course(db, user_id, target)
        if subset["kind"] == "course" and payload.parent_folder_id:
            raise ValueError("课程包不能指定笔记父文件夹")
        content.validate_target(
            db,
            user_id,
            subset,
            target,
            parent_folder_id=str(payload.parent_folder_id)
            if payload.parent_folder_id
            else None,
            title=payload.title,
        )
    result = content.catalog(subset)
    actual = {}
    for item in result["items"]:
        actual.setdefault(item["category"], []).append(item["id"])
    deadline_check(deadline)
    return result | {
        "selection_sha256": selection_digest(subset),
        "selection": actual,
        "warnings": list(dict.fromkeys([*result.get("warnings", []), *notes])),
    }


def _zip_write(archive, name, data):
    # Highly repetitive legitimate notes must round-trip under the ratio guard.
    compressor = zlib.compressobj(level=1, wbits=-15)
    compressed = compressor.compress(data) + compressor.flush()
    method = (
        zipfile.ZIP_STORED
        if len(data) > MAX_RATIO * max(1, len(compressed))
        else zipfile.ZIP_DEFLATED
    )
    archive.writestr(name, data, compress_type=method, compresslevel=1)


def export_package(db, user_id, payload):
    deadline = time.monotonic() + SECONDS
    begin_read_snapshot(db)
    manifest, sources = content.snapshot(
        db,
        user_id,
        str(payload.course_id),
        kind=payload.kind,
        folder_id=str(payload.folder_id) if payload.folder_id else None,
    )
    subset, _notes = content.select_content(manifest, selection_json(payload))
    check_confirmation(subset, payload.expected_sha256)
    encoded = canonical(subset)
    if len(encoded) > MAX_METADATA or len(subset["files"]) + 1 > MAX_MEMBERS:
        raise ValueError("包清单或文件数量超过预算")
    total = len(encoded) + sum(item["size_bytes"] for item in subset["files"])
    if total > MAX_CONTENT:
        raise ValueError("包解压后超过256MiB")
    source_map = {item["id"]: item for item in sources}
    path = control_path(user_id, str(uuid4()), ".export.zip")
    check_capacity(path.parent, total + 1024 * 1024)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(path, "x") as archive:
            _zip_write(archive, "manifest.json", encoded)
            for item in subset["files"]:
                source = storage().checked(Path(source_map[item["id"]]["source"]))
                if not source.is_relative_to(
                    storage().root / user_id / str(payload.course_id)
                ):
                    raise ValueError("包文件不在本人课程目录")
                with source.open("rb") as stream:
                    data = stream.read(MAX_FILE + 1)
                if (
                    len(data) != item["size_bytes"]
                    or len(data) > MAX_FILE
                    or hashlib.sha256(data).hexdigest() != item["sha256"]
                ):
                    raise ValueError("来源文件已改变或SHA-256不符，请重新核对")
                _file_type(data, item["suffix"], deadline)
                _zip_write(archive, item["member"], data)
                if path.stat().st_size > MAX_ZIP:
                    raise ValueError("生成ZIP超过100MiB，请减少所选内容")
                deadline_check(deadline)
        if path.stat().st_size > MAX_ZIP:
            raise ValueError("生成ZIP超过100MiB，请减少所选内容")
        # Use the same checker as upload; our own output must be importable.
        with path.open("rb") as stream:
            inspect_package(stream, deadline=deadline)
        name = (
            safe_name(
                content.catalog(subset)["title"],
                "课程包" if payload.kind == "course" else "笔记包",
            )
            + ".zip"
        )
        return path, name
    except Exception:
        storage().remove(path)
        raise


def import_status(db, user_id, request_id):
    row = db.scalar(
        select(PackageImport).where(
            PackageImport.user_id == user_id,
            PackageImport.request_id == str(request_id),
        )
    )
    if row is None:
        raise HTTPException(404, "尚未找到成功导入记录；可使用原请求重试")
    return row.result


def import_package(db, user_id, payload):
    deadline = time.monotonic() + SECONDS
    request_hash = fingerprint(payload)
    published = []
    import_id = None
    try:
        # SQLite's owner UPDATE serializes confirmations, including across workers.
        # The receipt commits in exactly the same transaction as all business rows.
        lock_owner(db, user_id)
        previous = db.scalar(
            select(PackageImport).where(
                PackageImport.user_id == user_id,
                PackageImport.request_id == str(payload.request_id),
            )
        )
        if previous:
            if previous.fingerprint != request_hash:
                raise HTTPException(409, "相同请求ID已用于不同导入参数，请核对原结果")
            result = previous.result
            db.rollback()
            return result
        row, source = _preview(db, user_id, payload.preview_id)
        with source.open("rb") as stream:
            digest, size = _hash_stream(stream, deadline)
            if digest != row.sha256 or size != row.size_bytes:
                raise ValueError("预览ZIP已改变，请重新上传核对")
            manifest = inspect_package(stream, deadline=deadline)
            subset, notices = content.select_content(manifest, selection_json(payload))
            check_confirmation(subset, payload.expected_sha256)
            if manifest["kind"] == "course":
                if payload.parent_folder_id:
                    raise ValueError("课程包不能指定笔记父文件夹")
                target = (
                    str(payload.target_course_id)
                    if payload.target_course_id
                    else str(uuid4())
                )
            else:
                if not payload.target_course_id:
                    raise ValueError("文件夹包请选择目标课程")
                target = str(payload.target_course_id)
            if payload.target_course_id:
                owned_course(db, user_id, target, lock=True)
            content.validate_target(
                db,
                user_id,
                subset,
                target,
                parent_folder_id=str(payload.parent_folder_id)
                if payload.parent_folder_id
                else None,
                title=payload.title,
            )
            import_id = str(uuid4())
            paths = {}
            check_capacity(
                storage().root, sum(item["size_bytes"] for item in subset["files"])
            )
            with zipfile.ZipFile(stream) as archive:
                for item in subset["files"]:
                    deadline_check(deadline)
                    path = storage().checked(
                        storage().root
                        / user_id
                        / target
                        / (".package-" + import_id)
                        / (str(uuid4()) + item["suffix"])
                    )
                    published.append(path)
                    data = _read_member(
                        archive, archive.getinfo(item["member"]), MAX_FILE, deadline
                    )
                    if hashlib.sha256(data).hexdigest() != item["sha256"]:
                        raise ValueError("导入时文件SHA-256已改变")
                    storage().write_stream(path, io.BytesIO(data), item["size_bytes"])
                    paths["file:" + item["id"]] = path
            applied = content.import_content(
                db,
                user_id,
                subset,
                paths,
                target_course_id=target,
                parent_folder_id=str(payload.parent_folder_id)
                if payload.parent_folder_id
                else None,
                title=payload.title,
            )
            deadline_check(deadline)
            counts = applied.get("counts", {})
            result = applied | {
                "import_id": import_id,
                "course_id": target,
                "note_count": counts.get("notes", 0),
                "folder_count": counts.get("folders", counts.get("note_folders", 0)),
                "warnings": list(
                    dict.fromkeys([*subset.get("warnings", []), *notices])
                ),
            }
            db.add(
                PackageImport(
                    id=import_id,
                    user_id=user_id,
                    request_id=str(payload.request_id),
                    fingerprint=request_hash,
                    result=result,
                )
            )
            db.commit()
            return result
    except Exception:
        db.rollback()
        # A driver may report an error after COMMIT reached durable storage.
        # Never delete files belonging to an already committed receipt.
        if import_id is not None:
            try:
                committed = db.get(PackageImport, import_id)
            except Exception:
                # State is unknown: preserve staged bytes until the receipt can
                # be checked; deleting them could corrupt a successful import.
                raise
            if committed is not None and committed.fingerprint == request_hash:
                return committed.result
        for path in reversed(published):
            cleanup_file(path)
        raise
