"""Bounded image ingestion and validated preview-page provenance (M1)."""

import hashlib
import io
from pathlib import Path
import warnings
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from ..core.storage import get_storage
from ..models import Asset
from ..repositories.materials import active_version

MAX_IMAGE_BYTES = 10 * 1024 * 1024


def preview_source(db, user_id, course_id, version_id, page):
    if (version_id is None) != (page is None):
        raise HTTPException(422, "来源版本与预览页号必须同时提供")
    if version_id is None:
        return None
    version = active_version(db, version_id, user_id, course_id)
    if (
        version.preview_status != "SUCCEEDED"
        or not version.preview_path
        or not Path(version.preview_path).is_file()
    ):
        raise HTTPException(409, "来源 PDF 预览尚不可用")
    from .preview_integrity import check_preview_mapping

    try:
        check_preview_mapping(Path(version.source_path), Path(version.preview_path))
        total = len(PdfReader(version.preview_path).pages)
    except Exception as exc:
        raise HTTPException(409, "来源 PDF 无法读取，请检查预览") from exc
    if not 1 <= page <= total:
        raise HTTPException(422, "截图页号超出来源预览页数")
    suffix = Path(version.original_filename).suffix.lower()
    return {
        "source_version_id": version.id,
        "source_page": page,
        "source_locator_type": "slide"
        if suffix == ".pptx"
        else "page"
        if suffix == ".pdf"
        else "preview_page",
    }


def save_asset(db, user_id, course_id, file, alt, source):
    data = file.file.read(MAX_IMAGE_BYTES + 1)
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(422, "图片不能为空且不能超过 10 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                mime = {
                    "PNG": "image/png",
                    "JPEG": "image/jpeg",
                    "WEBP": "image/webp",
                }.get(image.format)
                if (
                    not mime
                    or image.width * image.height > 20_000_000
                    or getattr(image, "n_frames", 1) != 1
                ):
                    raise ValueError("图片类型、尺寸或帧数超过预算")
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise HTTPException(422, "图片无法解码或超过安全预算") from exc
    storage = get_storage()
    extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[mime]
    stored = storage.new_path(user_id, course_id, extension, "assets")
    asset = Asset(
        user_id=user_id,
        course_id=course_id,
        original_filename=Path(file.filename or "asset").name[:255],
        name=Path(file.filename or "asset").name[:255] or "课程图片",
        mime_type=mime,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        storage_path=str(stored),
        alt=alt,
        **(source or {}),
    )
    published = False
    try:
        storage.write(stored, data)
        published = True
        db.add(asset)
        db.commit()
    except Exception:
        db.rollback()
        if published:
            storage.remove(stored)
        raise
    db.refresh(asset)
    return asset
