"""Single-process durable SQLite worker. Claim and completion use lease tokens."""

import argparse
from datetime import timedelta
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from uuid import uuid4

from sqlalchemy import case, select, update
from ..core.database import SessionLocal, init_db
from ..models import Document, DocumentChunk, DocumentVersion, ProcessingJob
from ..models.base import utc_now
from ..services.search import index_version
from .material_exports import run_export_once
from .note_exports import run_note_export_once
from .note_trash import run_trash_cleanup
from .note_capture import run_capture_once
from .ai_queries import run_ai_once
from .bank_ocr import run_bank_ocr_once
from .bank_ai import run_bank_ai_once

LEASE_SECONDS = 180


def recover_jobs(db):
    expired = db.scalars(
        select(ProcessingJob).where(
            ProcessingJob.type.in_(["PARSE", "INDEX", "PREVIEW"]),
            ProcessingJob.status == "RUNNING",
            (ProcessingJob.lease_until < utc_now())
            | ProcessingJob.lease_until.is_(None),
        )
    ).all()
    for job in expired:
        state = "QUEUED" if job.attempt_count < job.max_attempts else "FAILED"
        recovered = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job.id,
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_token == job.lease_token,
                (ProcessingJob.lease_until < utc_now())
                | ProcessingJob.lease_until.is_(None),
            )
            .values(
                status=state,
                error="worker 租约过期，已恢复待重试"
                if state == "QUEUED"
                else "任务重试次数已达上限",
                lease_token=None,
                lease_until=None,
            )
            .execution_options(synchronize_session=False)
        )
        if recovered.rowcount != 1:
            continue
        version = db.get(DocumentVersion, job.resource_id)
        if version:
            field = {
                "PARSE": "parse_status",
                "INDEX": "index_status",
                "PREVIEW": "preview_status",
            }.get(job.type)
            if field:
                setattr(version, field, state)
    db.commit()
    db.expire_all()


def claim_job(db, kinds=("PARSE", "INDEX", "PREVIEW")):
    recover_jobs(db)
    for job_id in db.scalars(
        select(ProcessingJob.id)
        .where(
            ProcessingJob.status == "QUEUED",
            ProcessingJob.type.in_(kinds),
            ProcessingJob.attempt_count < ProcessingJob.max_attempts,
        )
        .order_by(
            case((ProcessingJob.type == "PREVIEW", 1), else_=0),
            ProcessingJob.created_at,
            ProcessingJob.id,
        )
        .limit(10)
    ).all():
        token = str(uuid4())
        result = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.status == "QUEUED",
                ProcessingJob.attempt_count < ProcessingJob.max_attempts,
            )
            .values(
                status="RUNNING",
                lease_token=token,
                lease_until=utc_now() + timedelta(seconds=LEASE_SECONDS),
                attempt_count=ProcessingJob.attempt_count + 1,
                progress=10,
                error=None,
            )
        )
        if result.rowcount == 1:
            db.expire_all()
            claimed = db.get(ProcessingJob, job_id)
            version = db.get(DocumentVersion, claimed.resource_id)
            document = db.get(Document, version.document_id) if version else None
            if (
                not version
                or not document
                or document.deleted_at
                or version.user_id != claimed.user_id
                or document.user_id != claimed.user_id
            ):
                claimed.status = "CANCELLED"
                claimed.error = "来源资料不存在或已删除"
                claimed.lease_token = None
                claimed.lease_until = None
                db.commit()
                continue
            setattr(
                version,
                {
                    "PARSE": "parse_status",
                    "INDEX": "index_status",
                    "PREVIEW": "preview_status",
                }[claimed.type],
                "RUNNING",
            )
            db.commit()
            return claimed
        db.commit()
    return None


def parse_isolated(source):
    from ..core.storage import check_capacity

    check_capacity(Path(tempfile.gettempdir()), 132 * 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="hustudy-parser-") as folder:
        output = Path(folder) / "chunks.json"
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])}
        subprocess.run(
            [sys.executable, "-m", "app.workers.parse_file", str(source), str(output)],
            timeout=60,
            check=True,
            capture_output=True,
            env=env,
        )
        if output.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("解析输出超过32MiB预算")
        result = json.loads(output.read_text(encoding="utf-8"))
        if "error" in result:
            raise ValueError(result["error"])
        return result["chunks"]


def preview_file(source):
    from ..core.storage import check_capacity, get_storage
    from ..core.config import get_settings

    if source.suffix.lower() == ".pdf":
        return str(source)
    if source.suffix.lower() not in {".pptx", ".docx"}:
        return None
    if not get_settings().office_compatibility_enabled:
        raise ValueError(
            "服务器未启用兼容PDF转换；PPTX/DOCX仍可直接原格式阅读，无需安装额外服务"
        )
    from ..services.preview_runtime import office_executable

    executable = office_executable()
    if not executable:
        raise ValueError(
            "未找到可执行的LibreOffice；PPTX/DOCX需转换后预览，可继续读文本。安装/修复后重试预览即可，无需重新上传"
        )
    check_capacity(Path(tempfile.gettempdir()), 256 * 1024 * 1024)
    check_capacity(source.parent, 100 * 1024 * 1024)
    # Unique user profile and scratch directory prevent another conversion attaching to this process.
    with tempfile.TemporaryDirectory(prefix="hustudy-preview-") as folder:
        scratch = Path(folder)
        export_format = (
            'pdf:impress_pdf_Export:{"ExportHiddenSlides":{"type":"boolean","value":"true"}}'
            if source.suffix.lower() == ".pptx"
            else "pdf:writer_pdf_Export"
        )
        try:
            subprocess.run(
                [
                    executable,
                    f"-env:UserInstallation={(scratch / 'profile').as_uri()}",
                    "--headless",
                    "--nologo",
                    "--nodefault",
                    "--norestore",
                    "--convert-to",
                    export_format,
                    "--outdir",
                    str(scratch),
                    str(source.resolve()),
                ],
                timeout=120,
                check=True,
                capture_output=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError(
                "Office转PDF超过120秒，已停止；可继续读文本，或自行导出PDF后上传"
            ) from exc
        except (subprocess.CalledProcessError, OSError) as exc:
            raise ValueError(
                "Office转换器未能完成转PDF，请检查本机安装或文件，修复后重试；可继续读文本"
            ) from exc
        generated = scratch / (source.stem + ".pdf")
        if (
            not generated.is_file()
            or not 0 < generated.stat().st_size <= 100 * 1024 * 1024
        ):
            raise ValueError("预览转换未产生有效PDF，可继续读文本或自行上传PDF")
        try:
            from pypdf import PdfReader

            document = PdfReader(str(generated))
            if document.is_encrypted or not 0 < len(document.pages) <= 2000:
                raise ValueError("无可读页或页数超预算")
        except Exception as exc:
            raise ValueError(
                "转换结果不是可阅读的PDF，可继续读文本或自行上传PDF"
            ) from exc
        from ..services.preview_integrity import check_preview_mapping

        check_preview_mapping(source, generated)
        target = source.with_name(source.stem + ".preview-" + uuid4().hex + ".pdf")
        get_storage().copy(generated, target)
        return str(target)


def run_once(kinds=("PARSE", "INDEX", "PREVIEW")):
    with SessionLocal() as db:
        job = claim_job(db, kinds)
        if job is None:
            return False
        job_id, token, kind, version_id = (
            job.id,
            job.lease_token,
            job.type,
            job.resource_id,
        )
        version = db.get(DocumentVersion, version_id)
        source = Path(version.source_path) if version else None
        db.commit()
        result, error = None, None
        try:
            document = db.get(Document, version.document_id) if version else None
            if not version or not document or document.deleted_at:
                raise ValueError("资料已删除")
            if kind == "PARSE":
                result = parse_isolated(source)
            elif kind == "PREVIEW":
                result = preview_file(source)
        except Exception as exc:
            error = str(exc)[:1000] or type(exc).__name__
        # Complete only our own lease; this write also serializes against document deletion.
        locked = db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.id == job_id,
                ProcessingJob.status == "RUNNING",
                ProcessingJob.lease_token == token,
            )
            .values(progress=90)
        )
        if locked.rowcount != 1:
            db.rollback()
            # Only remove this attempt's converted file; original PDFs stay intact.
            if (
                kind == "PREVIEW"
                and result
                and source
                and Path(result).parent == source.parent
                and Path(result).name.startswith(source.stem + ".preview-")
            ):
                Path(result).unlink(missing_ok=True)
            return True
        db.expire_all()
        job, version = (
            db.get(ProcessingJob, job_id),
            db.get(DocumentVersion, version_id),
        )
        document = db.get(Document, version.document_id) if version else None
        if not document or document.deleted_at:
            job.status = "CANCELLED"
            job.error = "资料已删除"
        elif error:
            job.status = "FAILED"
            job.error = error
            setattr(
                version,
                {
                    "PARSE": "parse_status",
                    "INDEX": "index_status",
                    "PREVIEW": "preview_status",
                }[kind],
                "FAILED",
            )
            if kind == "PARSE":
                version.parse_error = error
            elif kind == "PREVIEW":
                version.preview_error = error
        else:
            if kind == "PARSE":
                # An immutable successful version is never re-parsed or given new chunk IDs.
                if not db.scalar(
                    select(DocumentChunk.id)
                    .where(
                        DocumentChunk.version_id == version_id,
                        DocumentChunk.source_kind == "extracted",
                    )
                    .limit(1)
                ):
                    for ordinal, chunk in enumerate(result):
                        db.add(
                            DocumentChunk(
                                user_id=job.user_id,
                                version_id=version_id,
                                ordinal=ordinal,
                                **chunk,
                            )
                        )
                version.parse_status = "SUCCEEDED"
                version.parse_error = None
                enqueue(db, version, "INDEX")
            elif kind == "INDEX":
                db.flush()
                try:
                    index_version(db, version_id)
                    version.index_status = "SUCCEEDED"
                except Exception as exc:
                    db.rollback()
                    failed = db.execute(
                        update(ProcessingJob)
                        .where(
                            ProcessingJob.id == job_id,
                            ProcessingJob.status == "RUNNING",
                            ProcessingJob.lease_token == token,
                        )
                        .values(
                            status="FAILED",
                            error=str(exc)[:1000],
                            lease_until=None,
                            lease_token=None,
                        )
                    )
                    if failed.rowcount == 1:
                        db.expire_all()
                        version = db.get(DocumentVersion, version_id)
                        version.index_status = "FAILED"
                        db.commit()
                    else:
                        db.rollback()
                    return True
            else:
                version.preview_path = result
                version.preview_error = None
                version.preview_status = "SUCCEEDED" if result else "TEXT_ONLY"
            job.status = "SUCCEEDED"
            job.error = None
            job.progress = 100
        job.lease_token = None
        job.lease_until = None
        db.commit()
        return True


def enqueue(db, version, kind):
    existing = db.scalar(
        select(ProcessingJob)
        .where(
            ProcessingJob.resource_id == version.id,
            ProcessingJob.type == kind,
        )
        .order_by(ProcessingJob.created_at.desc(), ProcessingJob.id.desc())
    )
    if not existing:
        db.add(
            ProcessingJob(user_id=version.user_id, type=kind, resource_id=version.id)
        )
        setattr(
            version,
            {"INDEX": "index_status", "PREVIEW": "preview_status"}[kind],
            "QUEUED",
        )


def drain_jobs(limit=100):
    from .account_archives import run_archive_once

    for _ in range(limit):
        run_trash_cleanup()
        if (
            not run_once()
            and not run_note_export_once()
            and not run_capture_once()
            and not run_bank_ocr_once()
            and not run_bank_ai_once()
            and not run_export_once()
            and not run_ai_once()
            and not run_archive_once()
        ):
            return
    raise RuntimeError("worker exceeded drain limit")


def run_core_once():
    from ..services.bank_answer_import import run_once as run_answer_once
    from .account_archives import run_archive_once

    run_trash_cleanup()
    return (
        run_once(("PARSE", "INDEX"))
        or run_note_export_once()
        or run_capture_once()
        or run_bank_ocr_once()
        or run_bank_ai_once()
        or run_answer_once()
        or run_export_once()
        or run_ai_once()
        or run_archive_once()
    )


def run_preview_lane(stop):
    while not stop.is_set():
        if not run_once(("PREVIEW",)):
            stop.wait(0.5)


def serve():
    from ..services.worker_runtime import WorkerRuntime

    # Each lane uses its own SessionLocal. A single slow Office conversion must
    # not occupy the thread that claims new PARSE/INDEX tasks.
    stop = threading.Event()
    with WorkerRuntime() as runtime:
        preview = threading.Thread(
            target=run_preview_lane, args=(stop,), daemon=True, name="material-preview"
        )
        preview.start()
        runtime.ready = True
        runtime.publish()
        try:
            while True:
                if not preview.is_alive():
                    runtime.ready = False
                    runtime.publish()
                    raise RuntimeError(
                        "Preview lane stopped; restart the processing worker"
                    )
                if not run_core_once():
                    stop.wait(0.5)
        finally:
            stop.set()
            preview.join(timeout=1)


if __name__ == "__main__":
    from .account_archives import run_archive_once
    from ..services.worker_runtime import WorkerAlreadyRunning

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Process one queued job")
    args = parser.parse_args()
    init_db()
    if args.once:
        run_trash_cleanup(force=True)
        if (
            not run_once()
            and not run_note_export_once()
            and not run_capture_once()
            and not run_bank_ocr_once()
            and not run_bank_ai_once()
        ):
            if not run_export_once():
                if not run_ai_once():
                    run_archive_once()
    else:
        try:
            serve()
        except WorkerAlreadyRunning:
            logging.getLogger(__name__).info(
                "Processing worker already running; leaving existing owner in place"
            )
            raise SystemExit(73)
