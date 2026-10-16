from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import zipfile
from fastapi.testclient import TestClient
from docx import Document as WordDocument
from pptx import Presentation
from app.main import app
from app.core.database import SessionLocal
from app.models import MaterialExport, DocumentVersion, ProcessingJob
from app.models.base import utc_now
from app.workers.materials import drain_jobs, claim_job
from app.workers.material_exports import claim_export, run_export_once
from app.services import material_exports as service
from test_materialhub import context, upload
from test_preview_assets import import_pdf, capture, png
from test_manual_transcripts import draft, confirm


def create(c, h, course, request=None):
    r = c.post(
        f"/api/v1/courses/{course}/material-exports",
        headers=h,
        json={"request_id": request or str(uuid4())},
    )
    assert r.status_code == 202, r.text
    return r.json()


def download(c, h, package):
    r = c.get(f"/api/v1/material-exports/{package['id']}/download", headers=h)
    assert r.status_code == 200, r.text
    return r.content


def test_four_formats_versions_images_manual_sources_hashes_and_scope(tmp_path):
    with TestClient(app) as c:
        h, course = context(c)
        foreign, other = context(c)
        md = upload(c, h, course, "# 旧版\n\n🙂保留旧引用。", "中文.md")
        drain_jobs()
        version = c.get(f"/api/v1/versions/{md['resource_id']}", headers=h).json()
        r = c.post(
            f"/api/v1/documents/{version['document_id']}/versions",
            headers=h,
            files={"file": ("第二版.md", "# 新版\n\n这是新版本。", "text/markdown")},
        )
        assert r.status_code == 202
        word = WordDocument()
        word.add_paragraph("DOCX段落")
        word.add_table(rows=1, cols=1).cell(0, 0).text = "DOCX表格"
        buffer = io.BytesIO()
        word.save(buffer)
        upload(c, h, course, buffer.getvalue(), "课件.docx")
        ppt = Presentation()
        slide = ppt.slides.add_slide(ppt.slide_layouts[6])
        slide.shapes.add_textbox(0, 0, 1000000, 1000000).text = "PPTX原文"
        buffer = io.BytesIO()
        ppt.save(buffer)
        upload(c, h, course, buffer.getvalue(), "slides.pptx")
        pdf = import_pdf(c, h, course)
        confirmed = confirm(c, h, draft(c, h, pdf))
        draft(c, h, pdf, text="不该导出的未确认文字", page=2)
        screenshot = capture(c, h, course, pdf["id"]).json()
        for name in ("one.png", "two.png"):
            assert (
                c.post(
                    f"/api/v1/courses/{course}/assets",
                    headers=h,
                    files={"file": (name, png(), "image/png")},
                ).status_code
                == 201
            )
        upload(c, foreign, other, "# 私有\n\n不可泄露内容。")
        drain_jobs()
        request = str(uuid4())
        package = create(c, h, course, request)
        assert create(c, h, course, request)["id"] == package["id"]
        assert (
            c.post(
                f"/api/v1/courses/{course}/material-exports",
                headers=h,
                json={"request_id": str(uuid4())},
            ).status_code
            == 409
        )
        assert (
            c.get(
                f"/api/v1/material-exports/{package['id']}/download", headers=h
            ).status_code
            == 409
        )
        drain_jobs()
        data = download(c, h, package)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            assert len(manifest["documents"]) == 4 and len(manifest["versions"]) == 5
            assert len(manifest["assets"]) == 3 and len(manifest["transcripts"]) == 1
            assert manifest["transcripts"][0]["chunk_id"] == confirmed["chunk_id"]
            assert (
                next(a for a in manifest["assets"] if a["id"] == screenshot["id"])[
                    "source_version_id"
                ]
                == pdf["id"]
            )
            assert {Path(v["original_file"]).suffix for v in manifest["versions"]} == {
                ".md",
                ".pdf",
                ".pptx",
                ".docx",
            }
            for item in manifest["files"]:
                content = archive.read(item["path"])
                assert (
                    len(content) == item["size_bytes"]
                    and hashlib.sha256(content).hexdigest() == item["sha256"]
                )
            serialized = json.dumps(manifest, ensure_ascii=False)
            assert "不该导出" not in serialized and "不可泄露" not in serialized
            assert (
                "storage_path" not in serialized
                and "source_path" not in serialized
                and "password" not in serialized
            )
            assert "不是完整账户备份" in archive.read("README.md").decode()
        saved = c.get(f"/api/v1/material-exports/{package['id']}", headers=h).json()
        assert (
            saved["job"]["status"] == "SUCCEEDED"
            and saved["sha256"] == hashlib.sha256(data).hexdigest()
        )
        assert saved["snapshot_at"].endswith(("Z", "+00:00"))
        assert saved["counts"]["documents"] == 4 and saved["counts"]["assets"] == 3
        path = tmp_path / "package.zip"
        path.write_bytes(data)
        result = subprocess.run(
            [sys.executable, "scripts/verify_material_package.py", str(path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        for suffix in ("", "/download"):
            assert (
                c.get(
                    f"/api/v1/material-exports/{package['id']}" + suffix,
                    headers=foreign,
                ).status_code
                == 404
            )
        assert (
            c.get(
                f"/api/v1/courses/{course}/material-exports", headers=foreign
            ).status_code
            == 404
        )
        assert (
            c.post(
                f"/api/v1/material-exports/{package['id']}/retry", headers=foreign
            ).status_code
            == 404
        )
        assert (
            c.delete(
                f"/api/v1/material-exports/{package['id']}", headers=foreign
            ).status_code
            == 404
        )
        assert (
            c.delete(f"/api/v1/material-exports/{package['id']}", headers=h).status_code
            == 204
        )
        assert (
            c.get(f"/api/v1/material-exports/{package['id']}", headers=h).status_code
            == 404
        )
        assert (
            c.get(f"/api/v1/jobs/{package['job']['id']}", headers=h).json()["status"]
            == "SUCCEEDED"
        )


def test_hash_failure_budget_retry_and_restart_recovery(monkeypatch):
    with TestClient(app) as c:
        h, course = context(c)
        job = upload(c, h, course, "# 来源\n\n文件内容必须一致。")
        drain_jobs()
        with SessionLocal() as db:
            path = Path(db.get(DocumentVersion, job["resource_id"]).source_path)
            original = path.read_bytes()
            path.write_bytes(b"corrupted")
        package = create(c, h, course)
        drain_jobs()
        url = f"/api/v1/material-exports/{package['id']}"
        assert c.get(url, headers=h).json()["job"]["status"] == "FAILED"
        with SessionLocal() as db:
            assert db.get(MaterialExport, package["id"]).zip_path is None
        assert c.get(url + "/download", headers=h).status_code == 409
        path.write_bytes(original)
        assert c.post(url + "/retry", headers=h).status_code == 202
        with monkeypatch.context() as patch:
            patch.setattr(service, "MAX_CONTENT", 1)
            drain_jobs()
        assert c.get(url, headers=h).json()["job"]["attempt_count"] == 2
        assert c.post(url + "/retry", headers=h).status_code == 202
        with SessionLocal() as db:
            leased = claim_export(db)
            assert leased.id == package["id"]
            leased.lease_until = utc_now() - timedelta(seconds=1)
            db.commit()
        drain_jobs()
        assert c.get(url, headers=h).json()["job"]["status"] == "FAILED"
        assert c.post(url + "/retry", headers=h).status_code == 409
        again = create(c, h, course)
        with SessionLocal() as db:
            leased = claim_export(db)
            stored_root = path.parent / "exports"
            stored_root.mkdir(exist_ok=True)
            stale = stored_root / (leased.id + "-" + leased.lease_token + ".zip")
            stale.write_bytes(b"partial from interrupted worker")
            leased.lease_until = utc_now() - timedelta(seconds=1)
            db.commit()
        drain_jobs()
        assert not stale.exists()
        assert download(c, h, again).startswith(b"PK")
        assert (
            c.get(f"/api/v1/material-exports/{again['id']}", headers=h).json()["job"][
                "attempt_count"
            ]
            == 2
        )


def test_source_revocation_corrupt_archive_removal_and_late_completion(monkeypatch):
    with TestClient(app) as c:
        h, course = context(c)
        pdf = import_pdf(c, h, course)
        transcript = confirm(c, h, draft(c, h, pdf))
        first = create(c, h, course)
        drain_jobs()
        url = f"/api/v1/material-exports/{first['id']}"
        with SessionLocal() as db:
            path = Path(db.get(MaterialExport, first["id"]).zip_path)
            original = path.read_bytes()
            path.write_bytes(b"bad package")
        assert c.get(url + "/download", headers=h).status_code == 409
        path.write_bytes(original)
        assert (
            c.post(
                f"/api/v1/transcripts/{transcript['id']}/withdraw",
                headers=h,
                json={"revision": transcript["revision"]},
            ).status_code
            == 200
        )
        assert c.get(url, headers=h).json()["availability"] == "unavailable"
        assert c.get(url + "/download", headers=h).status_code == 404
        second = create(c, h, course)
        drain_jobs()
        assert (
            c.delete(f"/api/v1/documents/{pdf['document_id']}", headers=h).status_code
            == 204
        )
        assert (
            c.get(
                f"/api/v1/material-exports/{second['id']}/download", headers=h
            ).status_code
            == 404
        )
        upload(c, h, course, "# 安全\n\n仅本课程可读。")
        drain_jobs()
        late = create(c, h, course)
        real = service.build_package
        outputs = []

        def delayed(db, row, output):
            result = real(db, row, output)
            outputs.append(output)
            assert (
                c.delete(
                    f"/api/v1/material-exports/{late['id']}", headers=h
                ).status_code
                == 204
            )
            return result

        with monkeypatch.context() as patch:
            patch.setattr("app.workers.material_exports.build_package", delayed)
            assert run_export_once()
        assert not outputs[0].exists()
        assert (
            c.get(f"/api/v1/material-exports/{late['id']}", headers=h).status_code
            == 404
        )
        pending = create(c, h, course)
        assert (
            c.delete(f"/api/v1/courses/{course}?revision=1", headers=h).status_code
            == 204
        )
        drain_jobs()
        assert (
            c.get(
                f"/api/v1/material-exports/{pending['id']}/download", headers=h
            ).status_code
            == 404
        )


def test_export_rejects_outside_owned_storage_and_offline_verifier_rejects_bad_package(
    tmp_path,
):
    with TestClient(app) as c:
        h, course = context(c)
        other, foreign_course = context(c)
        owned = upload(c, h, course, "# 自己\n\n有效文本。")
        foreign = upload(c, other, foreign_course, "# 外部\n\n私有文件。")
        drain_jobs()
        with SessionLocal() as db:
            source = db.get(DocumentVersion, foreign["resource_id"])
            target = db.get(DocumentVersion, owned["resource_id"])
            target.source_path = source.source_path
            target.size_bytes = source.size_bytes
            target.sha256 = source.sha256
            db.commit()
        record = create(c, h, course)
        drain_jobs()
        assert (
            c.get(f"/api/v1/material-exports/{record['id']}", headers=h).json()["job"][
                "status"
            ]
            == "FAILED"
        )
        assert (
            c.get(
                f"/api/v1/material-exports/{record['id']}/download", headers=h
            ).status_code
            == 409
        )
        path = tmp_path / "bad.zip"
        for member in ("../escape.txt", "file.txt"):
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(member, b"body")
                archive.writestr("README.md", "test")
                archive.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "format": "hustudy-material-package",
                            "schema_version": 1,
                            "files": [
                                {"path": member, "size_bytes": 4, "sha256": "incorrect"}
                            ],
                        }
                    ),
                )
            result = subprocess.run(
                [sys.executable, "scripts/verify_material_package.py", str(path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode != 0 and "校验失败" in result.stderr
        assert not (tmp_path.parent / "escape.txt").exists()


def test_parser_lease_recovery_from_a_new_session_and_export_empty_course():
    with TestClient(app) as c:
        h, course = context(c)
        assert (
            c.post(
                f"/api/v1/courses/{course}/material-exports",
                headers=h,
                json={"request_id": str(uuid4())},
            ).status_code
            == 409
        )
        queued = upload(c, h, course, "# 租约\n\n重启后恢复。")
        with SessionLocal() as db:
            claimed = claim_job(db)
            assert claimed.id == queued["id"]
            claimed.lease_until = utc_now() - timedelta(seconds=1)
            db.commit()
        drain_jobs()
        with SessionLocal() as db:
            assert db.get(ProcessingJob, queued["id"]).status == "SUCCEEDED"
            assert db.get(ProcessingJob, queued["id"]).attempt_count == 2
