"""Explicit, local image-bank OCR jobs; no uploads to an external provider."""

import hashlib
import importlib.util
import json
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from ..models import PastPaper, ProcessingJob
from ..repositories.assets import active_asset
from .courses import owned_course
from . import question_bank as bank


def job_response(db, paper):
    meta = json.loads(paper.bank_meta_json)
    topic_id = meta.get("ai_topic_index", {}).get("job_id")
    topic_job = db.get(ProcessingJob, topic_id) if topic_id else None
    job = db.get(ProcessingJob, meta["image_job_id"])
    return {
        "paper_id": paper.id,
        "title": paper.title,
        "id": job.id,
        "status": job.status,
        "error": job.error,
        "progress": job.progress,
        "asset_ids": meta["image_import"]["asset_ids"],
        "layout": meta["image_import"]["layout"],
        "pdf_version_id": meta.get("pdf_import", {}).get("version_id"),
        "engine": meta["image_import"].get("engine", "local"),
        "completed_pages": len(meta.get("vision_checkpoints", [])),
        "auto_topic_status": topic_job.status
        if topic_job
        else meta.get("auto_topic_status"),
        "force_ocr": meta.get("pdf_import", {}).get("force_ocr", False),
    }


def enqueue(db, user_id, course_id, payload):
    owned_course(db, user_id, course_id, lock=True)
    bank.no_active_attempt(db, user_id, course_id)
    bank.topic_rows(db, user_id, course_id, payload.default_topic_ids)
    ids = [str(i) for i in payload.asset_ids]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "同一批不能重复选择同一图片")
    hashes = []
    for aid in ids:
        asset = active_asset(db, aid, user_id)
        if asset.course_id != course_id:
            raise HTTPException(404, "图片不属于本课程")
        hashes.append(asset.sha256)
    config = payload.model_dump(mode="json")
    if payload.engine == "ai":
        from . import bank_vision, bank_pdf

        if not payload.confirm_remote_send:
            raise HTTPException(422, "请明确确认发送图片给AI")
        config["vision_config"] = bank_vision.require_config()
        config["topic_snapshot"] = (
            bank_pdf.bank_topic_snapshot(db, user_id, course_id)
            if payload.classify_topics
            else []
        )
    previous = db.get(PastPaper, str(payload.request_id))
    if previous:
        if previous.user_id != user_id or previous.course_id != course_id:
            raise HTTPException(404, "导入请求不可访问")
        if json.loads(previous.bank_meta_json).get("image_import") != config:
            raise HTTPException(409, "相同请求标识不能更改图片或顺序")
        return job_response(db, previous)
    digest = hashlib.sha256(
        bank.encode(
            {
                "image_hashes": hashes,
                "layout": payload.layout,
                "engine": payload.engine,
                "questions_only": payload.questions_only,
                "classify_topics": payload.classify_topics,
            }
        ).encode()
    ).hexdigest()
    duplicates = db.scalars(
        select(PastPaper).where(
            PastPaper.user_id == user_id,
            PastPaper.course_id == course_id,
            PastPaper.content_hash == digest,
        )
    ).all()
    for duplicate in duplicates:
        meta = json.loads(duplicate.bank_meta_json)
        job = (
            db.get(ProcessingJob, meta.get("image_job_id"))
            if meta.get("image_job_id")
            else None
        )
        if (
            job
            and job.status in {"QUEUED", "RUNNING", "SUCCEEDED"}
            and not meta.get("deleted_by_user")
        ):
            return job_response(db, duplicate)
    if not importlib.util.find_spec("rapidocr_onnxruntime"):
        raise HTTPException(
            409,
            "本地OCR尚未安装，请安装backend/requirements-bank-ocr.lock并重启后端与worker；也可手动粘贴文字",
        )
    job = ProcessingJob(
        id=str(uuid4()),
        user_id=user_id,
        type="BANK_OCR",
        resource_id=str(payload.request_id),
        max_attempts=1,
    )
    paper = PastPaper(
        id=str(payload.request_id),
        user_id=user_id,
        course_id=course_id,
        title=payload.title,
        year=payload.year,
        content="",
        content_hash=digest,
        bank_meta_json=bank.encode(
            {
                "image_job_id": job.id,
                "image_import": config,
                "parser": "bank-image-v2",
                "provenance": "用户图片，GLM-5.3-Flash转写待审核" if payload.engine == "ai" else "用户上传图片，本地OCR草稿",
            }
        ),
    )
    db.add_all([job, paper])
    db.commit()
    return job_response(db, paper)


def list_jobs(db, user_id, course_id):
    rows = db.scalars(
        select(PastPaper)
        .where(PastPaper.user_id == user_id, PastPaper.course_id == course_id)
        .order_by(PastPaper.created_at.desc())
    ).all()
    return [
        job_response(db, p)
        for p in rows
        if json.loads(p.bank_meta_json).get("image_job_id")
        and not json.loads(p.bank_meta_json).get("deleted_by_user")
    ][:100]


def read_images(items, layout):
    import numpy as np
    from PIL import Image, ImageOps
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)
    pages = []
    for item in items:
        with Image.open(item["path"]) as raw:
            if raw.width * raw.height > 20_000_000:
                raise ValueError("图片超过2000万像素")
            image = ImageOps.exif_transpose(raw).convert("RGB")
        w, h = image.size
        for col in range(2 if layout == "double" else 1):
            left, right = (
                (col * w // 2, (col + 1) * w // 2) if layout == "double" else (0, w)
            )
            result, _ = engine(np.asarray(image.crop((left, 0, right, h))))
            lines = []
            for box, text, score in result or []:
                xs, ys = [p[0] + left for p in box], [p[1] for p in box]
                lines.append(
                    {
                        "text": str(text),
                        "y": max(0, min(1, min(ys) / h)),
                        "x": min(xs) / w,
                        "bottom": max(ys) / h,
                        "low": float(score) < 0.8,
                    }
                )
            lines.sort(key=lambda line: (round(line["y"] * h / 12), line["x"]))
            pages.append(
                {
                    "asset_id": item["asset_id"],
                    "left": left / w,
                    "width": (right - left) / w,
                    "lines": lines,
                }
            )
    return pages


def assemble(pages):
    """Keep cross-page continuation in text and map question spans back to image strips."""
    # One photo per question is common. Without ANY numbered boundary, do not
    # collapse every uploaded photo into one question. Columns remain independent.
    unnumbered = not any(
        bank.START.match(line["text"]) for page in pages for line in page["lines"]
    )
    empty_regions = sum(not page["lines"] for page in pages)
    if unnumbered:
        numbered = []
        for page in pages:
            lines = [dict(line) for line in page["lines"]]
            if lines:
                lines[0]["text"] = f"{len(numbered) + 1}. " + lines[0]["text"]
                numbered.append({**page, "lines": lines})
        pages = numbered
    text, segments = "", []
    for page in pages:
        for line in page["lines"]:
            start = len(text)
            text += line["text"] + "\n"
            segments.append((start, len(text), page, line))
    if len(text) > 240000:
        raise ValueError("识别文字超过24万字符，请拆分批次")
    parsed = bank.parse_text(text)
    # Include figures between the question's first line and the next question boundary.
    for item in parsed:
        groups = {}
        for start, end, page, line in segments:
            if start < item["end"] and end > item["start"]:
                key = (page["asset_id"], page["left"])
                groups.setdefault(
                    key, {"page": page, "top": line["y"], "bottom": line["bottom"]}
                )
                groups[key]["bottom"] = max(groups[key]["bottom"], line["bottom"])
        item["source_images"] = []
        for group in groups.values():
            page, top = group["page"], max(0, group["top"] - 0.012)
            later = [
                line["y"]
                for start, _, p, line in segments
                if p is page and start >= item["end"] and bank.START.match(line["text"])
            ]
            bottom = max(group["bottom"] + 0.012, min(later) - 0.006 if later else 1)
            item["source_images"].append(
                {
                    "asset_id": page["asset_id"],
                    "box": [page["left"], top, page["width"], min(1, bottom) - top],
                    "alt": "OCR原图区域（仅审核，不在作答展示）",
                }
            )
        item["warnings"].append(
            "OCR可能误识别文字、公式或图中文字，请对照原图校正；插图请另行裁取并审核"
        )
        if unnumbered:
            item["warnings"].append(
                "未检测到题号，暂按每张图片/每栏一题分开；题号为系统页序，请核对并按需拆合"
            )
        if empty_regions:
            item["warnings"].append(
                f"有{empty_regions}个图片/栏没有识别到文字，未自动关联；请在识别任务中核对原图并手动上传所需插图"
            )
    return text, parsed


if __name__ == "__main__":
    import sys
    from pathlib import Path

    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        result = {"pages": read_images(request["items"], request["layout"])}
    except Exception as exc:
        result = {"error": str(exc)[:1000]}
    Path(sys.argv[2]).write_text(bank.encode(result), encoding="utf-8")
