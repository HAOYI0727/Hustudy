"""Latest versions, usable sources and bounded task recovery form one M1 loop."""

import re
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from app.main import app
from app.core.database import SessionLocal, engine
from app.models import Document, DocumentVersion, DocumentChunk, ProcessingJob
from app.workers.materials import drain_jobs
from test_material_organization import setup_course, import_document
from test_preview_assets import import_pdf
from test_manual_transcripts import draft, confirm


def path(course):
    return f"/api/v1/courses/{course}/material-health"


def get(c, h, course, **params):
    r = c.get(path(course), headers=h, params=params)
    assert r.status_code == 200, r.status_code
    return r.json()


def test_current_version_counts_ignore_old_failures_and_do_not_project_content_or_write():
    with TestClient(app) as c:
        h, course = setup_course(c)
        foreign, _ = setup_course(c)
        doc, version = import_document(c, h, course, "# 原文\n只能在阅读器打开的正文。")
        uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        with SessionLocal() as db:
            db.add(
                ProcessingJob(
                    user_id=uid,
                    resource_id=version,
                    type="INDEX",
                    status="FAILED",
                    error="旧记录",
                    created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
                )
            )
            db.commit()
        sql = []

        def capture(_c, _cur, statement, _params, _ctx, _many):
            sql.append(statement.lower())

        event.listen(engine, "before_cursor_execute", capture)
        try:
            data = get(c, h, course, issue="all")
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert data["counts"] == dict(
            materials=1,
            attention=0,
            text=0,
            parse=0,
            index=0,
            preview=0,
            processing=0,
            readable=1,
        )
        row = data["items"][0]
        assert (
            row["version_id"] == version
            and row["document_id"] == doc
            and row["issues"] == []
        )
        assert (
            len(row["jobs"]) == 3
            and next(j for j in row["jobs"] if j["type"] == "INDEX")["status"]
            == "SUCCEEDED"
        )
        assert not {
            "source_path",
            "storage_path",
            "text",
            "lease_token",
            "lease_until",
        }.intersection(row)
        assert "只能在阅读器" not in str(data)
        projections = "\n".join(
            re.findall(r"\bselect\b(.*?)\bfrom\b", "\n".join(sql), re.S)
        )
        for forbidden in (
            "document_chunks.text",
            "document_versions.source_path",
            "document_versions.preview_path",
            "processing_jobs.lease_token",
            "processing_jobs.error",
        ):
            assert forbidden not in projections
        assert not any(re.match(r"\s*(insert|update|delete|replace)\b", s) for s in sql)
        overview = c.get(
            f"/api/v1/courses/{course}/workspace/materials", headers=h
        ).json()["counts"]
        assert overview["failed_jobs"] == 1 and overview["attention_materials"] == 0
        with SessionLocal() as db:
            db.get(DocumentVersion, version).parse_status = "FAILED"
            db.commit()
        assert get(c, h, course)["counts"]["attention"] == 1
        later = c.post(
            f"/api/v1/documents/{doc}/versions",
            headers=h,
            files={"file": ("新版.md", "# 新版\n新的不可变原文。", "text/markdown")},
        ).json()["resource_id"]
        drain_jobs()
        page = get(c, h, course, issue="all")
        assert page["total"] == 1 and page["items"][0]["version_id"] == later
        assert page["counts"]["attention"] == 0
        assert c.get(path(course), headers=foreign).status_code == 404
        assert c.get(path(course)).status_code == 401


def test_status_filters_text_manual_confirmation_withdrawal_and_scope():
    with TestClient(app) as c:
        h, course = setup_course(c)
        doc, version = import_document(c, h, course, "# 中文\n有效原文。")
        with SessionLocal() as db:
            v = db.get(DocumentVersion, version)
            v.index_status = "FAILED"
            v.preview_status = "FAILED"
            db.commit()
        # Text formats use text view; an irrelevant preview failure isn't a check item.
        page = get(c, h, course)
        assert page["counts"]["index"] == 1 and page["counts"]["preview"] == 0
        assert page["items"][0]["has_text"] is True
        with SessionLocal() as db:
            db.get(DocumentVersion, version).parse_status = "RUNNING"
            db.commit()
        assert get(c, h, course, issue="text")["total"] == 0
        assert get(c, h, course, issue="processing")["total"] == 1
        pdf = import_pdf(c, h, course)
        with SessionLocal() as db:
            v = db.get(DocumentVersion, pdf["id"])
            v.parse_status = "FAILED"
            db.commit()
        candidate = draft(c, h, pdf, text="人工补全的可核对正文。")
        before = next(
            row
            for row in get(c, h, course, issue="all")["items"]
            if row["version_id"] == pdf["id"]
        )
        assert "text" in before["issues"]
        saved = confirm(c, h, candidate)
        after = next(
            row
            for row in get(c, h, course, issue="all")["items"]
            if row["version_id"] == pdf["id"]
        )
        assert after["has_text"] is True and "text" not in after["issues"]
        assert (
            c.post(
                f"/api/v1/transcripts/{saved['id']}/withdraw",
                headers=h,
                json={"revision": saved["revision"]},
            ).status_code
            == 200
        )
        withdrawn = next(
            row
            for row in get(c, h, course, issue="all")["items"]
            if row["version_id"] == pdf["id"]
        )
        assert withdrawn["has_text"] is False and "text" in withdrawn["issues"]
        with SessionLocal() as db:
            db.get(Document, doc).library_scope = "question_bank"
            db.get(DocumentVersion, pdf["id"]).preview_status = "FAILED"
            db.commit()
        assert get(c, h, course, issue="preview")["total"] == 1
        assert get(c, h, course, issue="all")["total"] == 1
        assert (
            c.delete(f"/api/v1/documents/{pdf['document_id']}", headers=h).status_code
            == 204
        )
        assert get(c, h, course, issue="all")["total"] == 0


def test_stable_sql_paging_literal_search_empty_text_and_validation():
    with TestClient(app) as c:
        h, course = setup_course(c)
        ids = []
        for i in range(15):
            doc, version = import_document(
                c, h, course, f"# 章节{i}\n保留身份的测试正文。"
            )
            ids.append(doc)
            with SessionLocal() as db:
                db.get(Document, doc).name = f"章节{i:02}"
                db.get(Document, doc).updated_at = datetime(
                    2026, 1, 1, tzinfo=timezone.utc
                )
                db.get(DocumentVersion, version).index_status = "CANCELLED"
                if i == 0:
                    chunk = db.scalar(
                        select(DocumentChunk).where(DocumentChunk.version_id == version)
                    )
                    chunk.text = "　\n\t"
                db.commit()
        first = get(c, h, course)
        second = get(c, h, course, offset=12)
        assert (
            first["total"] == 15
            and len(first["items"]) == 12
            and len(second["items"]) == 3
        )
        assert [r["document_id"] for r in first["items"] + second["items"]] == sorted(
            ids
        )
        assert get(c, h, course, q="章节03")["total"] == 1
        assert get(c, h, course, q="%' OR 1=1 --")["total"] == 0
        assert get(c, h, course, issue="text")["total"] == 1
        assert get(c, h, course, offset=100)["items"] == []
        for bad in (
            {"issue": "unknown"},
            {"q": "字" * 201},
            {"offset": -1},
            {"offset": 1000001},
            {"limit": 0},
            {"limit": 51},
        ):
            assert c.get(path(course), headers=h, params=bad).status_code == 422
        assert (
            c.delete(f"/api/v1/courses/{course}?revision=1", headers=h).status_code
            == 204
        )
        assert c.get(path(course), headers=h).status_code == 404


def test_explicit_existing_task_recovery_budget_and_success_clear_current_check():
    with TestClient(app) as c:
        h, course = setup_course(c)
        doc, version = import_document(c, h, course, "# 引用源\n原文与引用保持不变。")
        with SessionLocal() as db:
            task = db.scalar(
                select(ProcessingJob).where(
                    ProcessingJob.resource_id == version, ProcessingJob.type == "INDEX"
                )
            )
            task.status = "FAILED"
            task.error = "internal-source:/private/temporary-file SECRET_EXCERPT"
            task.attempt_count = 1
            task.max_attempts = 3
            task_id = task.id
            db.get(DocumentVersion, version).index_status = "FAILED"
            db.add(
                ProcessingJob(
                    user_id=task.user_id,
                    resource_id=version,
                    type="INDEX",
                    status="FAILED",
                    created_at=task.created_at - timedelta(days=1),
                )
            )
            db.commit()
        record = get(c, h, course)["items"][0]
        assert "SECRET_EXCERPT" not in str(record) and "/private/" not in str(record)
        index = next(row for row in record["jobs"] if row["type"] == "INDEX")
        assert index["id"] == task_id and index["attempt_count"] == 1
        result = c.post(f"/api/v1/jobs/{task_id}/retry", headers=h)
        assert result.status_code == 202 and result.json()["attempt_count"] == 1
        drain_jobs()
        assert get(c, h, course)["total"] == 0
        counts = c.get(
            f"/api/v1/courses/{course}/workspace/materials", headers=h
        ).json()["counts"]
        assert counts["failed_jobs"] == 1 and counts["attention_materials"] == 0
        with SessionLocal() as db:
            task = db.get(ProcessingJob, task_id)
            task.status = "FAILED"
            task.attempt_count = task.max_attempts
            db.get(DocumentVersion, version).index_status = "FAILED"
            db.commit()
        assert c.post(f"/api/v1/jobs/{task_id}/retry", headers=h).status_code == 409
        assert get(c, h, course)["items"][0]["index_status"] == "FAILED"
