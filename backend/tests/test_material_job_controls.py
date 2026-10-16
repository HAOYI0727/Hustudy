from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from app.main import app
from app.core.database import SessionLocal
from app.models import ProcessingJob, DocumentChunk
from app.workers import materials
from test_materialhub import context, upload
from test_preview_assets import import_pdf
from test_manual_transcripts import draft, confirm


def test_queued_cancel_restore_is_idempotent_and_preserves_original():
    with TestClient(app) as c:
        h, course = context(c)
        foreign, _ = context(c)
        job = upload(c, h, course, "# 窗口机制\n\n取消不删除原件。")
        url = f"/api/v1/jobs/{job['id']}"
        version = f"/api/v1/versions/{job['resource_id']}"
        assert c.post(url + "/cancel", headers=foreign).status_code == 404
        for _ in range(2):
            r = c.post(url + "/cancel", headers=h)
            assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
            assert r.json()["attempt_count"] == 0
        v = c.get(version, headers=h).json()
        assert (
            v["parse_status"] == v["preview_status"] == v["index_status"] == "CANCELLED"
        )
        assert "取消不删除" in c.get(version + "/original", headers=h).text
        assert c.get(version + "/chunks", headers=h).json() == []
        materials.drain_jobs()
        assert c.get(url, headers=h).json()["status"] == "CANCELLED"
        for _ in range(2):
            r = c.post(url + "/retry", headers=h)
            assert r.status_code == 202 and r.json()["id"] == job["id"]
        materials.drain_jobs()
        v = c.get(version, headers=h).json()
        assert v["parse_status"] == v["index_status"] == "SUCCEEDED"
        assert c.post(url + "/cancel", headers=h).status_code == 409
        assert c.get(url, headers=h).json()["attempt_count"] == 1


def test_cancelled_running_lease_cannot_overwrite_resumed_task(monkeypatch):
    with TestClient(app) as c:
        h, course = context(c)
        job = upload(c, h, course, "# 原文\n\n正常来源。")
        url = f"/api/v1/jobs/{job['id']}"

        def delayed_parse(_source):
            assert c.get(url, headers=h).json()["status"] == "RUNNING"
            assert c.post(url + "/cancel", headers=h).status_code == 200
            assert c.post(url + "/retry", headers=h).status_code == 202
            return [
                {
                    "locator_type": "heading",
                    "locator_value": "伪迟到结果",
                    "text": "迟到文本",
                    "start_offset": 0,
                    "end_offset": 4,
                }
            ]

        with monkeypatch.context() as patch:
            patch.setattr(materials, "parse_isolated", delayed_parse)
            assert materials.run_once()
        with SessionLocal() as db:
            assert db.get(ProcessingJob, job["id"]).status == "QUEUED"
            assert not db.scalar(
                select(DocumentChunk.id).where(
                    DocumentChunk.version_id == job["resource_id"]
                )
            )
            materials.recover_jobs(db)
        materials.drain_jobs()
        assert c.get(url, headers=h).json()["attempt_count"] == 2
        chunks = c.get(
            f"/api/v1/versions/{job['resource_id']}/chunks", headers=h
        ).json()
        assert chunks[0]["text"] == "正常来源。"
        assert all("迟到" not in row["text"] for row in chunks)


def test_reindex_preserves_citation_and_rejects_budget_bypass(monkeypatch):
    with TestClient(app) as c:
        h, course = context(c)
        other, _ = context(c)
        job = upload(c, h, course, "# 索引重建\n\n引用身份始终稳定。")
        materials.drain_jobs()
        version = job["resource_id"]
        url = f"/api/v1/versions/{version}/reindex"
        chunk = c.get(f"/api/v1/versions/{version}/chunks", headers=h).json()[0]
        note = c.post(
            "/api/v1/notes",
            headers=h,
            json={
                "title": "稳定引用",
                "course_id": course,
                "citations": [
                    {
                        "version_id": version,
                        "chunk_id": chunk["id"],
                        "quote": "身份始终稳定",
                    }
                ],
            },
        ).json()
        request = {"request_id": str(uuid4())}
        assert c.post(url, headers=other, json=request).status_code == 404
        assert c.post(url, headers=h, json={"request_id": "invalid"}).status_code == 422
        new = c.post(url, headers=h, json=request)
        assert new.status_code == 202
        new = new.json()
        collision = c.post(url, headers=h, json={"request_id": str(uuid4())})
        assert collision.status_code == 409
        assert collision.json()["error"]["details"]["active_job_id"] == new["id"]

        def failure(db, _version):
            db.execute(
                text("DELETE FROM chunk_search WHERE chunk_id=:id"), {"id": chunk["id"]}
            )
            raise RuntimeError("injected index write failure")

        with monkeypatch.context() as patch:
            patch.setattr(materials, "index_version", failure)
            materials.drain_jobs()
        with SessionLocal() as db:
            assert (
                db.execute(
                    text("SELECT chunk_id FROM chunk_search WHERE chunk_id=:id"),
                    {"id": chunk["id"]},
                ).scalar()
                == chunk["id"]
            )
        assert (
            c.post(url, headers=h, json={"request_id": str(uuid4())}).status_code == 409
        )
        assert c.post(f"/api/v1/jobs/{new['id']}/retry", headers=h).status_code == 202
        materials.drain_jobs()
        assert (
            c.get(f"/api/v1/versions/{version}/chunks", headers=h).json()[0]["id"]
            == chunk["id"]
        )
        assert c.post(url, headers=h, json=request).json()["id"] == new["id"]
        assert (
            c.get(f"/api/v1/notes/{note['id']}/citations", headers=h).json()[0][
                "chunk_id"
            ]
            == chunk["id"]
        )
        assert (
            c.get(
                f"/api/v1/courses/{course}/search", headers=h, params={"q": "引用身份"}
            ).json()[0]["chunk_id"]
            == chunk["id"]
        )
        again = c.post(url, headers=h, json={"request_id": str(uuid4())}).json()
        with SessionLocal() as db:
            row = db.get(ProcessingJob, again["id"])
            row.status = "FAILED"
            row.attempt_count = row.max_attempts
            db.commit()
        assert (
            c.post(url, headers=h, json={"request_id": str(uuid4())}).status_code == 409
        )
        assert c.post(f"/api/v1/jobs/{again['id']}/retry", headers=h).status_code == 409


def test_preview_cancel_discards_only_own_output_and_dependencies_keep_budget(
    monkeypatch,
):
    with TestClient(app) as c:
        h, course = context(c)
        v = import_pdf(c, h, course)
        with SessionLocal() as db:
            preview = db.scalar(
                select(ProcessingJob).where(
                    ProcessingJob.resource_id == v["id"],
                    ProcessingJob.type == "PREVIEW",
                )
            )
            preview.status = "FAILED"
            preview_id = preview.id
            db.commit()
        assert c.post(f"/api/v1/jobs/{preview_id}/retry", headers=h).status_code == 202
        outputs = []

        def delayed_preview(source):
            output = source.with_name(source.stem + ".preview-" + uuid4().hex + ".pdf")
            output.write_bytes(b"temporary result")
            outputs.append(output)
            assert (
                c.post(f"/api/v1/jobs/{preview_id}/cancel", headers=h).status_code
                == 200
            )
            return str(output)

        with monkeypatch.context() as patch:
            patch.setattr(materials, "preview_file", delayed_preview)
            assert materials.run_once()
        assert not outputs[0].exists()
        assert c.get(
            f"/api/v1/versions/{v['id']}/original", headers=h
        ).content.startswith(b"%PDF")
        assert (
            c.get(f"/api/v1/versions/{v['id']}", headers=h).json()["preview_status"]
            == "CANCELLED"
        )
        # Retrying scanned parsing must not replace the cancelled/failed preview job.
        parse = next(
            j
            for j in c.get(f"/api/v1/courses/{course}/jobs", headers=h).json()
            if j["type"] == "PARSE"
        )
        assert c.post(f"/api/v1/jobs/{parse['id']}/retry", headers=h).status_code == 202
        materials.drain_jobs()
        rows = c.get(f"/api/v1/courses/{course}/jobs", headers=h).json()
        assert len([j for j in rows if j["type"] == "PREVIEW"]) == 1
        assert (
            c.get(f"/api/v1/jobs/{preview_id}", headers=h).json()["status"]
            == "CANCELLED"
        )
        assert c.post(f"/api/v1/jobs/{preview_id}/retry", headers=h).status_code == 202
        materials.drain_jobs()
        assert (
            c.get(f"/api/v1/versions/{v['id']}/preview", headers=h).status_code == 200
        )


def test_manual_only_reindex_does_not_fake_parse_success_and_deleted_source_revokes_controls():
    with TestClient(app) as c:
        h, course = context(c)
        version = import_pdf(c, h, course)
        url = f"/api/v1/versions/{version['id']}/reindex"
        assert (
            c.post(url, headers=h, json={"request_id": str(uuid4())}).status_code == 409
        )
        transcript = confirm(c, h, draft(c, h, version))
        request = {"request_id": str(uuid4())}
        job = c.post(url, headers=h, json=request).json()
        materials.drain_jobs()
        v = c.get(f"/api/v1/versions/{version['id']}", headers=h).json()
        assert v["parse_status"] == "FAILED" and v["index_status"] == "SUCCEEDED"
        assert c.post(url, headers=h, json=request).json()["id"] == job["id"]
        assert (
            c.get(
                f"/api/v1/courses/{course}/search", headers=h, params={"q": "滑动窗口"}
            ).json()[0]["chunk_id"]
            == transcript["chunk_id"]
        )
        assert (
            c.delete(
                f"/api/v1/documents/{version['document_id']}", headers=h
            ).status_code
            == 204
        )
        assert (
            c.post(url, headers=h, json={"request_id": str(uuid4())}).status_code == 404
        )
        for action in ("retry", "cancel"):
            assert (
                c.post(f"/api/v1/jobs/{job['id']}/{action}", headers=h).status_code
                == 404
            )
