"""Optional scanned-PDF recognition; M1 versions stay read-only."""

import hashlib
import importlib.util
import json
import os
from .topic_tree import active_clause
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from ..core.storage import get_storage
from ..models import PastPaper, ProcessingJob
from ..repositories.materials import active_version
from . import bank_ocr, question_bank as bank, topic_tree
from .courses import owned_course


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    title: str = Field(min_length=1, max_length=240)
    year: int | None = Field(default=None, ge=1900, le=2200)
    default_topic_ids: list[UUID] = Field(default_factory=list, max_length=12)
    force_ocr: bool = False
    engine: str = Field(default="local", pattern="^(local|ai)$")
    confirm_remote_send: bool = False
    questions_only: bool = False
    classify_topics: bool = False
    layout: str = Field(default="single", pattern="^(single|double)$")


def pdf_source(db, user_id, course_id, version_id):
    version = active_version(db, version_id, user_id, course_id)
    if Path(version.original_filename).suffix.lower() != ".pdf":
        raise HTTPException(422, "此入口只支持PDF")
    path = get_storage().checked(Path(version.source_path))
    if not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise HTTPException(422, "PDF文件不可用或超过32MiB")
    return version, path


def examine(path):
    from pypdf import PdfReader
    import re

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError("不支持加密PDF，请先解密")
    if not 1 <= len(reader.pages) <= 20:
        raise ValueError("单批PDF最多20页，请先拆分PDF再上传")
    pages, total = [], 0
    for n, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        total += len(text)
        if total > 240000:
            raise ValueError("PDF文字超过24万字符，请拆分文件")
        count = len(re.findall(r"[A-Za-z\u3400-\u9fff]", text))
        resources = page.get("/Resources", {})
        resources = (
            resources.get_object() if hasattr(resources, "get_object") else resources
        )
        objects = resources.get("/XObject", {})
        objects = objects.get_object() if hasattr(objects, "get_object") else objects
        large_image = any(
            obj.get_object().get("/Subtype") == "/Image"
            and int(obj.get_object().get("/Width", 0))
            * int(obj.get_object().get("/Height", 0))
            > 90000
            for obj in objects.values()
        )
        pages.append(
            {
                "number": n,
                "text": text,
                "needs_ocr": count < 12 or (large_image and count < 80),
            }
        )
    return pages


def subprocess_pdf(path, folder, render=False, force=False):
    request, result = Path(folder) / "request.json", Path(folder) / "result.json"
    request.write_text(
        bank.encode({"path": str(path), "render": render, "force": force}),
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, "-m", "app.services.bank_pdf", str(request), str(result)],
        timeout=120 if render else 30,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
            "PYTHONUTF8": "1",
        },
    )
    if not result.is_file() or result.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("PDF检测结果超过预算")
    data = json.loads(result.read_text(encoding="utf-8"))
    if data.get("error"):
        raise ValueError(data["error"])
    return data["pages"]


def inspect(db, user_id, course_id, version_id):
    owned_course(db, user_id, course_id)
    bank.no_active_attempt(db, user_id, course_id)
    version, path = pdf_source(db, user_id, course_id, version_id)
    try:
        with tempfile.TemporaryDirectory(prefix="hustudy-pdf-check-") as folder:
            pages = subprocess_pdf(path, folder)
    except (ValueError, subprocess.SubprocessError) as exc:
        raise HTTPException(
            422,
            str(exc)
            if isinstance(exc, ValueError)
            else "PDF检测超时或失败，请拆分文件",
        ) from None
    return {
        "version_id": version.id,
        "pages": len(pages),
        "ocr_pages": [p["number"] for p in pages if p["needs_ocr"]],
        "ocr_available": all(
            importlib.util.find_spec(name) is not None
            for name in ["rapidocr_onnxruntime", "pypdfium2"]
        ),
    }


def enqueue(db, user_id, course_id, version_id, payload):
    owned_course(db, user_id, course_id, lock=True)
    bank.no_active_attempt(db, user_id, course_id)
    bank.topic_rows(db, user_id, course_id, payload.default_topic_ids)
    version, _ = pdf_source(db, user_id, course_id, version_id)
    config = payload.model_dump(mode="json") | {
        "version_id": version.id,
        "source_hash": version.sha256,
    }
    if payload.engine == "ai":
        from . import bank_vision

        if not payload.confirm_remote_send:
            raise HTTPException(422, "请核对原件范围并明确确认发送AI")
        config["vision_config"] = bank_vision.require_config()
        config["topic_snapshot"] = (
            bank_topic_snapshot(db, user_id, course_id)
            if payload.classify_topics
            else []
        )
    previous = db.get(PastPaper, str(payload.request_id))
    if previous:
        if previous.user_id != user_id or previous.course_id != course_id:
            raise HTTPException(404, "识别请求不可访问")
        if json.loads(previous.bank_meta_json).get("pdf_import") != config:
            raise HTTPException(409, "重试不能改变原请求范围")
        return bank_ocr.job_response(db, previous)
    if not all(
        importlib.util.find_spec(n) is not None
        for n in (
            ["pypdfium2"]
            if payload.engine == "ai"
            else ["pypdfium2", "rapidocr_onnxruntime"]
        )
    ):
        raise HTTPException(
            409,
            "PDF识别组件未安装，请安装backend/requirements-bank-ocr.lock并重启worker",
        )
    digest = hashlib.sha256(
        bank.encode(
            {
                "pdf": version.sha256,
                "force": payload.force_ocr,
                "layout": payload.layout,
                "engine": payload.engine,
                "questions_only": payload.questions_only,
                "classify_topics": payload.classify_topics,
            }
        ).encode()
    ).hexdigest()
    for row in db.scalars(
        select(PastPaper).where(
            PastPaper.user_id == user_id,
            PastPaper.course_id == course_id,
            PastPaper.content_hash == digest,
        )
    ).all():
        meta = json.loads(row.bank_meta_json)
        job = db.get(ProcessingJob, meta.get("image_job_id"))
        if (
            meta.get("pdf_import", {}).get("version_id") == version.id
            and job
            and job.status in {"QUEUED", "RUNNING", "SUCCEEDED"}
            and not meta.get("deleted_by_user")
        ):
            return bank_ocr.job_response(db, row)
    job = ProcessingJob(
        id=str(uuid4()),
        user_id=user_id,
        type="BANK_OCR",
        resource_id=str(payload.request_id),
        max_attempts=1,
    )
    row = PastPaper(
        id=str(payload.request_id),
        user_id=user_id,
        course_id=course_id,
        title=payload.title,
        year=payload.year,
        content="",
        content_hash=digest,
        bank_meta_json=bank.encode(
            {
                "parser": "bank-pdf-ocr-v1",
                "version_id": version.id,
                "pdf_import": config,
                "image_job_id": job.id,
                "image_import": {
                    "asset_ids": [],
                    "engine": payload.engine,
                    "questions_only": payload.questions_only,
                    "classify_topics": payload.classify_topics,
                    "vision_config": config.get("vision_config"),
                    "topic_snapshot": config.get("topic_snapshot", []),
                    "layout": payload.layout,
                    "default_topic_ids": config["default_topic_ids"],
                },
                "provenance": "用户PDF，GLM-5.3-Flash转写待审核"
                if payload.engine == "ai"
                else "用户PDF，本地图片转文字草稿",
            }
        ),
    )
    db.add_all([job, row])
    db.commit()
    return bank_ocr.job_response(db, row)


def validate(db, paper):
    config = json.loads(paper.bank_meta_json)["pdf_import"]
    version, path = pdf_source(db, paper.user_id, paper.course_id, config["version_id"])
    if version.sha256 != config["source_hash"]:
        raise ValueError("PDF来源内容已变化")
    return config, path


def prepare(paper_id, job_id, token):
    from ..core.database import SessionLocal
    from .assets import save_asset

    with SessionLocal() as db:
        paper = db.get(PastPaper, paper_id)
        config, path = validate(db, paper)
        user_id, course_id = paper.user_id, paper.course_id
    with SessionLocal() as db:
        paper, job = db.get(PastPaper, paper_id), db.get(ProcessingJob, job_id)
        if job.status != "RUNNING" or job.lease_token != token:
            raise ValueError("PDF识别已取消")
        meta = json.loads(paper.bank_meta_json)
        meta["image_import"]["asset_ids"] = []
        meta["pdf_render_complete"] = False
        paper.bank_meta_json = bank.encode(meta)
        db.commit()
    items = []
    with tempfile.TemporaryDirectory(prefix="hustudy-pdf-pages-") as folder:
        pages = subprocess_pdf(path, folder, render=True, force=config["force_ocr"])
        for page in pages:
            with SessionLocal() as db:
                owned_course(db, user_id, course_id, lock=True)
                paper, job = db.get(PastPaper, paper_id), db.get(ProcessingJob, job_id)
                validate(db, paper)
                if job.status != "RUNNING" or job.lease_token != token:
                    raise ValueError("PDF识别任务已取消")
                image_path = Path(folder) / page["image"]
                with image_path.open("rb") as stream:
                    asset = save_asset(
                        db,
                        user_id,
                        course_id,
                        UploadFile(
                            filename=f"PDF第{page['number']}页.png", file=stream
                        ),
                        "PDF原页，仅供题库审核",
                        {
                            "source_version_id": config["version_id"],
                            "source_page": page["number"],
                            "source_locator_type": "page",
                        },
                    )
                meta = json.loads(paper.bank_meta_json)
                meta["image_import"]["asset_ids"].append(asset.id)
                paper.bank_meta_json = bank.encode(meta)
                job.progress = int(20 * page["number"] / len(pages))
                db.commit()
                items.append(
                    {
                        "asset_id": asset.id,
                        "path": str(get_storage().checked(Path(asset.storage_path))),
                        "text": page["text"],
                        "needs_ocr": page["needs_ocr"],
                    }
                )
    with SessionLocal() as db:
        paper, job = db.get(PastPaper, paper_id), db.get(ProcessingJob, job_id)
        if job.status != "RUNNING" or job.lease_token != token:
            raise ValueError("PDF识别已取消")
        meta = json.loads(paper.bank_meta_json)
        meta["pdf_render_complete"] = True
        paper.bank_meta_json = bank.encode(meta)
        db.commit()
    return items


def merge_pages(items, recognized):
    pages = []
    for item in items:
        if item["needs_ocr"]:
            pages.extend(p for p in recognized if p["asset_id"] == item["asset_id"])
        else:
            # Text extraction has no reliable bounding boxes: show the whole source page.
            pages.append(
                {
                    "asset_id": item["asset_id"],
                    "left": 0,
                    "width": 1,
                    "lines": [
                        {"text": line, "x": 0, "y": 0, "bottom": 1, "low": False}
                        for line in item["text"].splitlines()
                        if line.strip()
                    ],
                }
            )
    return pages


def render_pages(path, folder, force):
    import pypdfium2 as pdfium

    pages = examine(path)
    total_bytes = 0
    document = pdfium.PdfDocument(str(path))
    try:
        for page in pages:
            rendered = document[page["number"] - 1]
            try:
                width, height = rendered.get_size()
                if width * height * 4 > 20_000_000:
                    raise ValueError("PDF单页超过2000万渲染像素，请缩小页面")
                bitmap = rendered.render(scale=2)
                try:
                    image = bitmap.to_pil().convert("RGB")
                    filename = f"page-{page['number']}.png"
                    image.save(Path(folder) / filename)
                    image.close()
                finally:
                    bitmap.close()
            finally:
                rendered.close()
            size = (Path(folder) / filename).stat().st_size
            total_bytes += size
            if size > 10 * 1024 * 1024 or total_bytes > 128 * 1024 * 1024:
                raise ValueError("PDF渲染图片超过单页10MiB/总计128MiB预算")
            page["image"], page["needs_ocr"] = filename, force or page["needs_ocr"]
    finally:
        document.close()
    return pages


if __name__ == "__main__":
    request_path, result_path = Path(sys.argv[1]), Path(sys.argv[2])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    try:
        pages = (
            render_pages(request["path"], request_path.parent, request["force"])
            if request["render"]
            else examine(request["path"])
        )
        result = {"pages": pages}
    except Exception as exc:
        result = {"error": str(exc)[:800]}
    result_path.write_text(bank.encode(result), encoding="utf-8")


def bank_topic_snapshot(db, user_id, course_id):
    from ..models import Topic

    return [
        {
            "id": t.id,
            "name": t.name,
            "aliases": json.loads(t.aliases_json),
            "parent_id": topic_tree.parent_id(t),
            "revision": t.revision,
        }
        for t in db.scalars(
            select(Topic)
            .where(
                active_clause(),
                Topic.user_id == user_id,
                Topic.course_id == course_id,
                Topic.merged_into_id.is_(None),
            )
            .order_by(Topic.id)
        ).all()
    ]
