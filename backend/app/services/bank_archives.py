"""Bounded archive inspection. Never extract member paths onto the filesystem."""

import io
import re
import stat
import unicodedata
import zipfile
from pathlib import PurePosixPath
from fastapi import HTTPException, UploadFile
from .courses import owned_course
from . import question_bank as bank

DOCUMENTS = {".pdf", ".pptx", ".docx", ".md", ".markdown", ".txt"}
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_ZIP = 50 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024


def members(raw):
    if not raw or len(raw) > MAX_ZIP:
        raise HTTPException(413, "ZIP不能为空且不能超过50MiB")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        infos = archive.infolist()
        if len(infos) > 200:
            raise ValueError("ZIP最多200项（含目录与系统杂项）")
        seen, selected, expanded = set(), [], 0
        for item in infos:
            name = item.filename
            if not item.flag_bits & 0x800:
                try:
                    name = name.encode("cp437").decode("gbk")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            name = name.replace("\\", "/")
            parts = PurePosixPath(name).parts
            normalized = unicodedata.normalize("NFKC", name).casefold()
            if (
                not name
                or name.startswith("/")
                or re.match(r"^[a-zA-Z]:", name)
                or any(p in {"..", "."} or ":" in p for p in parts)
                or any(ord(c) < 32 for c in name)
                or len(name) > 500
                or stat.S_ISLNK(item.external_attr >> 16)
            ):
                raise ValueError("ZIP含越界路径、符号链接或非法文件名")
            if normalized in seen:
                raise ValueError("ZIP含重复路径或大小写冲突")
            seen.add(normalized)
            if item.flag_bits & 1:
                raise ValueError("不支持加密ZIP，请先解密")
            if item.is_dir():
                continue
            expanded += item.file_size
            if expanded > MAX_EXPANDED or item.file_size > 32 * 1024 * 1024:
                raise ValueError("ZIP解压总量最多128MiB，单个文档最多32MiB")
            if item.file_size and item.file_size / max(1, item.compress_size) > 200:
                raise ValueError("ZIP压缩比超过200，请拆分或取消过度压缩")
            suffix = PurePosixPath(name).suffix.lower()
            if suffix in {".zip", ".rar", ".7z", ".tar", ".gz"}:
                raise ValueError("不支持嵌套压缩包，请先整理为文档或图片")
            kind = (
                "document"
                if suffix in DOCUMENTS
                else "image"
                if suffix in IMAGES
                else "skip"
            )
            if any(p.startswith(".") or p == "__MACOSX" for p in parts):
                kind = "skip"
            if kind == "image" and item.file_size > 10 * 1024 * 1024:
                raise ValueError("ZIP单张图片最多10MiB")
            selected.append((item, name, kind))
        if sum(kind != "skip" for _, _, kind in selected) > 40:
            raise ValueError("ZIP每批最多40个可导入文件")
        if sum(kind == "image" for _, _, kind in selected) > 20:
            raise ValueError("ZIP每批最多20张图片")
        if not any(kind != "skip" for _, _, kind in selected):
            raise ValueError("ZIP内没有支持的文档或图片")
        selected.sort(
            key=lambda row: [
                (0, int(p)) if p.isdigit() else (1, p.casefold())
                for p in re.split(r"(\d+)", row[1])
            ]
        )
        # Read/check CRC for every accepted entry before any upload side effect.
        data = []
        for item, name, kind in selected:
            if kind == "skip":
                data.append((name, kind, b""))
                continue
            with archive.open(item) as source:
                content = source.read(min(item.file_size, 32 * 1024 * 1024) + 1)
            if len(content) != item.file_size:
                raise ValueError("ZIP成员实际尺寸与声明不符")
            data.append((name, kind, content))
        return data
    except (
        zipfile.BadZipFile,
        RuntimeError,
        NotImplementedError,
        ValueError,
        OSError,
    ) as exc:
        raise HTTPException(422, str(exc)) from None


def import_archive(db, user_id, course_id, raw, selected_paths=None, *, local=False):
    from .documents import save_upload
    from .assets import save_asset

    owned_course(db, user_id, course_id, lock=True)
    bank.no_active_attempt(db, user_id, course_id)
    entries = members(raw)
    if selected_paths is not None:
        if (
            not selected_paths
            or len(selected_paths) != len(set(selected_paths))
            or not set(selected_paths) <= {e[0] for e in entries if e[1] != "skip"}
        ):
            raise HTTPException(422, "请选择ZIP内有效且不重复的文件")
        entries = [e for e in entries if e[0] in selected_paths]
    if local:
        from .bank_strict_markdown import validate_file

        for name, kind, content in entries:
            if kind != "skip":
                validate_file(name, content)
        # Unsupported ZIP members must not be silently accepted as local data.
        if any(kind == "skip" and not any(p.startswith(".") or p == "__MACOSX" for p in PurePosixPath(name).parts) for name, kind, _ in entries):
            raise HTTPException(422, "本地ZIP仅允许Markdown文件，请移除其他类型或使用AI识别")
    result = []
    for name, kind, content in entries:
        row = {"path": name, "kind": kind}
        if kind == "skip":
            result.append(
                row | {"status": "skipped", "error": "系统杂项或不支持的类型，未导入"}
            )
            continue
        file = UploadFile(filename=PurePosixPath(name).name, file=io.BytesIO(content))
        try:
            owned_course(db, user_id, course_id, lock=True)
            bank.no_active_attempt(db, user_id, course_id)
            if kind == "document":
                _, version, _, _ = save_upload(
                    file, course_id, user_id, db, library_scope="question_bank",
                    defer_parse=not local and file.filename.lower().endswith(".pdf"),
                )
                row |= {"version_id": version.id}
            else:
                asset = save_asset(
                    db, user_id, course_id, file, "ZIP题库原图（未识别）", None
                )
                row |= {"asset_id": asset.id}
            result.append(row | {"status": "uploaded"})
        except Exception as exc:
            db.rollback()
            message = (
                str(exc.detail)
                if isinstance(exc, HTTPException)
                else str(exc)
                if isinstance(exc, ValueError)
                else "文件保存失败，请检查格式或存储空间"
            )
            result.append(row | {"status": "failed", "error": message[:500]})
            if isinstance(exc, HTTPException) and exc.status_code in {
                401,
                403,
                404,
                409,
                507,
            }:
                for remaining, remaining_kind, _ in entries[len(result) :]:
                    result.append(
                        {
                            "path": remaining,
                            "kind": remaining_kind,
                            "status": "failed",
                            "error": "课程状态或存储异常，已停止后续上传，请核对后重试",
                        }
                    )
                break
        finally:
            file.file.close()
    return {"entries": result}
