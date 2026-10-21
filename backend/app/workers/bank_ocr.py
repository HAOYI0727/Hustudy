"""One bounded OCR subprocess per explicit batch; lease guards all completion writes."""

from datetime import timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import uuid4
from sqlalchemy import select, update
from ..core.database import SessionLocal
from ..core.storage import get_storage
from ..models import PastPaper, ProcessingJob, PastQuestion
from ..models.base import utc_now
from ..repositories.assets import active_asset
from ..services import bank_ocr, bank_pdf, bank_vision, question_bank as bank
from ..services.courses import owned_course


def recognize(items, layout):
    with tempfile.TemporaryDirectory(prefix="hustudy-bank-") as folder:
        request, result = Path(folder) / "input.json", Path(folder) / "output.json"
        request.write_text(
            bank.encode({"items": items, "layout": layout}), encoding="utf-8"
        )
        subprocess.run(
            [sys.executable, "-m", "app.services.bank_ocr", str(request), str(result)],
            timeout=360,
            check=True,
            capture_output=True,
            env={
                **os.environ,
                "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
                "PYTHONUTF8": "1",
            },
        )
        if result.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("识别结果超过预算，请减少单批图片")
        data = json.loads(result.read_text(encoding="utf-8"))
        if "error" in data:
            raise ValueError(data["error"])
        return data["pages"]


def run_bank_ocr_once():
    with SessionLocal() as db:
        db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.type == "BANK_OCR",
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_until < utc_now(),
            )
            .values(
                status="FAILED",
                error="识别已中断，请显式重试",
                lease_token=None,
                lease_until=None,
            )
        )
        db.commit()
        jid = db.scalar(
            select(ProcessingJob.id)
            .where(ProcessingJob.type == "BANK_OCR", ProcessingJob.status == "QUEUED")
            .order_by(ProcessingJob.created_at)
            .limit(1)
        )
        if not jid:
            return False
        token = str(uuid4())
        claimed = db.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id == jid, ProcessingJob.status == "QUEUED")
            .values(
                status="RUNNING",
                lease_token=token,
                lease_until=utc_now() + timedelta(seconds=480),
                attempt_count=1,
            )
        )
        db.commit()
        if claimed.rowcount != 1:
            return True
        job = db.get(ProcessingJob, jid)
        user_id, pid = job.user_id, job.resource_id
        paper = db.get(PastPaper, pid)
        try:
            owned_course(db, user_id, paper.course_id)
            paper_meta = json.loads(paper.bank_meta_json)
            pdf_mode = bool(paper_meta.get("pdf_import"))
            if pdf_mode:
                bank_pdf.validate(db, paper)
            meta = paper_meta["image_import"]
            vision_mode = meta.get("engine") == "ai"
            items = []
            for aid in meta["asset_ids"]:
                asset = active_asset(db, aid, user_id)
                if asset.course_id != paper.course_id:
                    raise ValueError("图片课程不匹配")
                items.append(
                    {
                        "asset_id": aid,
                        "path": str(get_storage().checked(Path(asset.storage_path))),
                    }
                )
        except Exception:
            job.status, job.error = "FAILED", "来源图片或课程已不可用"
            job.lease_token, job.lease_until = None, None
            db.commit()
            return True
    pages, error = None, None
    try:
        if pdf_mode and not (
            vision_mode and items and paper_meta.get("pdf_render_complete")
        ):
            items = bank_pdf.prepare(pid, jid, token)
        if vision_mode:
            pages = bank_vision.recognize_job(pid, jid, token, items)
        elif pdf_mode:
            meta["asset_ids"] = [item["asset_id"] for item in items]
            ocr_items = [item for item in items if item["needs_ocr"]]
            recognized = recognize(ocr_items, meta["layout"]) if ocr_items else []
            pages = bank_pdf.merge_pages(items, recognized)
        else:
            pages = recognize(items, meta["layout"])
    except bank_vision.ProviderFailure as exc:
        error = f"{exc.code}（{exc.provider_code or '无服务码'}）：{exc.message}"
    except subprocess.TimeoutExpired:
        error = "图片识别超过6分钟，请减少批次并显式重试"
    except Exception as exc:
        error = (
            str(exc)[:800]
            if isinstance(exc, ValueError)
            else (
                "AI视觉识别失败，已完成页保留，请显式续跑"
                if vision_mode
                else "本地OCR失败，请检查组件、图片或减少批次后重试"
            )
        )
    with SessionLocal() as db:
        job = db.get(ProcessingJob, jid)
        if (
            not job
            or job.status != "RUNNING"
            or job.lease_token != token
            or not job.lease_until
            or job.lease_until.replace(tzinfo=timezone.utc) <= utc_now()
        ):
            return True
        paper = db.get(PastPaper, pid)
        try:
            owned_course(db, user_id, paper.course_id, lock=True)
            bank.no_active_attempt(db, user_id, paper.course_id)
            if pdf_mode:
                bank_pdf.validate(db, paper)
            for aid in meta["asset_ids"]:
                active_asset(db, aid, user_id)
            if error:
                raise ValueError(error)
            if db.scalar(
                select(PastQuestion.id).where(PastQuestion.paper_id == pid).limit(1)
            ):
                raise ValueError("此批次已有题目，禁止重复写入")
            if vision_mode:
                bank_vision.check_job(db, pid, jid, token)
            content, parsed = (
                bank_vision.assemble(pages) if vision_mode else bank_ocr.assemble(pages)
            )
            if not content.strip():
                raise ValueError("没有识别到题目文字，请检查空白页或图片清晰度")
            if pdf_mode:
                for item in parsed:
                    item["source_version_id"] = json.loads(paper.bank_meta_json)[
                        "pdf_import"
                    ]["version_id"]
            bank.populate_bank(
                db,
                user_id,
                paper.course_id,
                paper,
                content,
                parsed,
                default_topic_ids=meta.get("default_topic_ids", []),
            )
            paper.content = content
            metadata = json.loads(paper.bank_meta_json)
            metadata["content_profile"] = {
                key: sum(i["content_profile"] == key for i in parsed)
                for key in {i["content_profile"] for i in parsed}
            }
            paper.bank_meta_json = bank.encode(metadata)
            job.status, job.error, job.progress = "SUCCEEDED", None, 100
        except Exception as exc:
            db.rollback()
            job = db.get(ProcessingJob, jid)
            if job.status != "RUNNING" or job.lease_token != token:
                return True
            job.status, job.error = (
                "FAILED",
                str(exc.detail)[:800] if hasattr(exc, "detail") else str(exc)[:800],
            )
        job.lease_token, job.lease_until = None, None
        db.commit()
    if vision_mode:
        with SessionLocal() as db:
            completed = db.get(ProcessingJob, jid).status == "SUCCEEDED"
        if completed:
            bank_vision.auto_topics(pid)
    return True
