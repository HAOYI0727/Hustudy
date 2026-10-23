"""Selection packages retain their enqueue scope through retries and revocation."""

import io
import json
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.main import app
from app.core.database import SessionLocal
from app.models import MaterialExport, DocumentVersion, ProcessingJob
from app.workers.materials import drain_jobs
from test_materialhub import context, upload
from test_preview_assets import import_pdf, capture, png
from test_manual_transcripts import draft, confirm


def selected(c, h, course, ids, request=None):
    return c.post(
        f"/api/v1/courses/{course}/material-exports",
        headers=h,
        json={"request_id": request or str(uuid4()), "document_ids": ids},
    )


def doc(c, h, job):
    return c.get(f"/api/v1/versions/{job['resource_id']}", headers=h).json()[
        "document_id"
    ]


def manifest(c, h, record):
    response = c.get(f"/api/v1/material-exports/{record['id']}/download", headers=h)
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        return json.loads(archive.read("manifest.json"))


def test_selected_versions_assets_transcripts_and_revocation(tmp_path):
    with TestClient(app) as c:
        h, course = context(c)
        first = upload(c, h, course, "# 版本一\n范围内的原文。")
        other = upload(c, h, course, "# 未选择\n不能泄露进选择包。", "unselected.md")
        pdf = import_pdf(c, h, course)
        transcript = confirm(c, h, draft(c, h, pdf))
        image = capture(c, h, course, pdf["id"]).json()
        standalone = c.post(
            f"/api/v1/courses/{course}/assets",
            headers=h,
            files={"file": ("independent.png", png(), "image/png")},
        ).json()
        drain_jobs()
        first_id, other_id = doc(c, h, first), doc(c, h, other)
        second = c.post(
            f"/api/v1/documents/{first_id}/versions",
            headers=h,
            files={"file": ("v2.md", "# 版本二\n仍在选择范围。", "text/markdown")},
        ).json()
        drain_jobs()
        response = selected(c, h, course, [pdf["document_id"], first_id])
        assert response.status_code == 202, response.text
        record = response.json()
        assert record["scope"] == "selected" and record["selected_count"] == 2
        # A later version must not expand an already-enqueued selection.
        late = c.post(
            f"/api/v1/documents/{first_id}/versions",
            headers=h,
            files={"file": ("v3.md", "# 后来版本\n不得加入。", "text/markdown")},
        ).json()
        drain_jobs()
        result = manifest(c, h, record)
        assert result["scope"] == "selected_materials"
        assert {d["id"] for d in result["documents"]} == {first_id, pdf["document_id"]}
        assert {v["id"] for v in result["versions"]} == {
            first["resource_id"],
            second["resource_id"],
            pdf["id"],
        }
        assert late["resource_id"] not in result["selection"]["version_ids"]
        assert [a["id"] for a in result["assets"]] == [image["id"]]
        assert standalone["id"] not in json.dumps(result)
        assert [t["id"] for t in result["transcripts"]] == [transcript["id"]]
        assert "source_path" not in json.dumps(
            result
        ) and "storage_path" not in json.dumps(result)
        path = tmp_path / "selection.zip"
        path.write_bytes(
            c.get(
                f"/api/v1/material-exports/{record['id']}/download", headers=h
            ).content
        )
        from scripts.verify_material_package import verify_package

        assert verify_package(path)["versions"] == 3
        assert c.delete(f"/api/v1/documents/{other_id}", headers=h).status_code == 204
        assert manifest(c, h, record)["selection"] == result["selection"]
        assert (
            c.post(
                f"/api/v1/transcripts/{transcript['id']}/withdraw",
                headers=h,
                json={"revision": transcript["revision"]},
            ).status_code
            == 200
        )
        assert (
            c.get(
                f"/api/v1/material-exports/{record['id']}/download", headers=h
            ).status_code
            == 404
        )


def test_selection_idempotency_compares_sets_and_preserves_version_snapshot():
    with TestClient(app) as c:
        h, course = context(c)
        jobs = [
            upload(c, h, course, f"# 资料{i}\n内容{i}。", f"{i}.md") for i in range(2)
        ]
        drain_jobs()
        ids = [doc(c, h, job) for job in jobs]
        request = str(uuid4())
        first = selected(c, h, course, ids, request).json()
        assert selected(c, h, course, ids[::-1], request).json()["id"] == first["id"]
        assert selected(c, h, course, ids[:1], request).status_code == 409
        assert selected(c, h, course, None, request).status_code == 409
        drain_jobs()
        assert selected(c, h, course, ids, request).json()["scope"] == "selected"
        with SessionLocal() as db:
            stored = db.get(MaterialExport, request).sources_json
            assert stored["request"]["document_ids"] == sorted(ids)
            assert set(stored["request"]["version_ids"]) == {
                job["resource_id"] for job in jobs
            }
            assert stored["documents"] == sorted(ids)


def test_selection_validation_and_ownership_are_atomic():
    with TestClient(app) as c:
        h, course = context(c)
        foreign, other_course = context(c)
        own = upload(c, h, course, "# 有效\n原文。")
        other = upload(c, foreign, other_course, "# 他人\n不可访问。")
        drain_jobs()
        own_id, other_id = doc(c, h, own), doc(c, foreign, other)
        for invalid in (
            [],
            [own_id, own_id],
            ["not-uuid"],
            [str(uuid4()) for _ in range(101)],
        ):
            assert selected(c, h, course, invalid).status_code == 422
        own_other_course = c.post(
            "/api/v1/courses", headers=h, json={"name": "另一门"}
        ).json()["id"]
        cross = upload(c, h, own_other_course, "# 跨课程\n不可混入。")
        bank = upload(c, h, course, "# 独立题库\n不进入课程资料导出。", "bank.md")
        drain_jobs()
        bank_id = doc(c, h, bank)
        from app.models import Document

        with SessionLocal() as db:
            db.get(Document, bank_id).library_scope = "question_bank"
            db.commit()
        for inaccessible in (other_id, doc(c, h, cross), bank_id, str(uuid4())):
            assert selected(c, h, course, [own_id, inaccessible]).status_code == 404
        with SessionLocal() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(MaterialExport)
                    .where(MaterialExport.course_id == course)
                )
                == 0
            )
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(ProcessingJob)
                    .where(
                        ProcessingJob.type == "MATERIAL_EXPORT",
                        ProcessingJob.user_id
                        == c.get("/api/v1/auth/me", headers=h).json()["id"],
                    )
                )
                == 0
            )
        created = selected(c, h, course, [own_id]).json()
        assert (
            c.get(
                f"/api/v1/material-exports/{created['id']}", headers=foreign
            ).status_code
            == 404
        )
        assert (
            selected(c, foreign, other_course, [other_id], created["id"]).status_code
            == 404
        )


def test_selection_retry_keeps_versions_and_deleted_selection_fails_as_whole():
    with TestClient(app) as c:
        h, course = context(c)
        job = upload(c, h, course, "# 正确内容\n校验重试。")
        drain_jobs()
        document_id = doc(c, h, job)
        with SessionLocal() as db:
            source = Path(db.get(DocumentVersion, job["resource_id"]).source_path)
            original = source.read_bytes()
            source.write_bytes(b"corrupted")
        record = selected(c, h, course, [document_id]).json()
        drain_jobs()
        url = f"/api/v1/material-exports/{record['id']}"
        failed = c.get(url, headers=h).json()
        assert failed["job"]["status"] == "FAILED" and failed["selected_count"] == 1
        source.write_bytes(original)
        late = c.post(
            f"/api/v1/documents/{document_id}/versions",
            headers=h,
            files={"file": ("new.md", "# 新版本\n重试不得加入。", "text/markdown")},
        ).json()
        assert c.post(url + "/retry", headers=h).status_code == 202
        drain_jobs()
        result = manifest(c, h, record)
        assert [v["id"] for v in result["versions"]] == [job["resource_id"]]
        assert late["resource_id"] not in json.dumps(result)
        assert c.get(url, headers=h).json()["job"]["attempt_count"] == 2
        second = upload(c, h, course, "# 第二份\n即将删除。", "remove.md")
        drain_jobs()
        deleted_id = doc(c, h, second)
        pending = selected(c, h, course, [document_id, deleted_id]).json()
        assert c.delete(f"/api/v1/documents/{deleted_id}", headers=h).status_code == 204
        drain_jobs()
        status = c.get(f"/api/v1/material-exports/{pending['id']}", headers=h).json()
        assert (
            status["job"]["status"] == "FAILED" and "所选资料" in status["job"]["error"]
        )
        with SessionLocal() as db:
            assert db.get(MaterialExport, pending["id"]).zip_path is None
        assert (
            c.get(
                f"/api/v1/material-exports/{pending['id']}/download", headers=h
            ).status_code
            == 409
        )
        assert (
            c.delete(f"/api/v1/documents/{document_id}", headers=h).status_code == 204
        )
        assert c.get(url + "/download", headers=h).status_code == 404
