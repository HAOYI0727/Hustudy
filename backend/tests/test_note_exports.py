"""Portable M3 ZIP and lifecycle tests use only disposable accounts/storage."""

from datetime import timedelta
import hashlib
import io
import json
import posixpath
import re
from urllib.parse import unquote
from pathlib import Path
import importlib.util
from uuid import uuid4
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.database import SessionLocal
from app.models import NoteExport, Note, Asset, ProcessingJob
from app.models.base import utc_now
from app.services import note_package
from app.workers import note_exports as worker
from app.workers.materials import drain_jobs
from test_materialhub import context, upload
from test_note_tags import create as note
from test_preview_assets import png
from test_account_backups import exported


def create(client, headers, request_id=None, **options):
    response = client.post(
        "/api/v1/note-exports",
        headers=headers,
        json={
            "request_id": request_id or str(uuid4()),
            "include_images": True,
            **options,
        },
    )
    assert response.status_code == 202, response.text
    return response.json()


def done(client, headers, row):
    assert worker.run_note_export_once()
    return client.get("/api/v1/note-exports/" + row["id"], headers=headers).json()


def downloaded(client, headers, row):
    result = client.get(f"/api/v1/note-exports/{row['id']}/download", headers=headers)
    assert result.status_code == 200, result.text
    assert hashlib.sha256(result.content).hexdigest() == row["sha256"]
    return zipfile.ZipFile(io.BytesIO(result.content))


def image(client, headers, course):
    result = client.post(
        f"/api/v1/courses/{course}/assets",
        headers=headers,
        files={"file": ("../恶意名称.png", png(), "image/png")},
    )
    assert result.status_code == 201
    return result.json()


def test_package_relative_links_exact_bodies_assets_citations_and_ownership(tmp_path):
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, other = context(client)
        foreign = note(client, stranger, other, title="不应泄露的秘密")
        foreign_image = image(client, stranger, other)
        target = note(client, owner, None, title="跨课程或未分类目标")
        asset = image(client, owner, course)
        source = upload(client, owner, course, "# 引用资料\n\n这段来源支持笔记。")
        drain_jobs()
        chunk = client.get(
            f"/api/v1/versions/{source['resource_id']}/chunks", headers=owner
        ).json()[0]
        body = f"中文🙂\n[[note:{target['id']}|稳定链接]]\n![[asset:{asset['id']}|图片]]\n[[note:{foreign['id']}]]\n![[asset:{foreign_image['id']}]]\n![](https://example.invalid/not-fetched.png)"
        current = note(
            client,
            owner,
            course,
            content=body,
            tags=["期末"],
            citations=[
                {
                    "version_id": source["resource_id"],
                    "chunk_id": chunk["id"],
                    "quote": chunk["text"],
                }
            ],
        )
        request_id = str(uuid4())
        row = create(client, owner, request_id)
        assert create(client, owner, request_id)["id"] == row["id"]
        assert (
            client.post(
                "/api/v1/note-exports", headers=owner, json={"request_id": str(uuid4())}
            ).status_code
            == 409
        )
        assert (
            client.get(
                f"/api/v1/note-exports/{row['id']}/download", headers=owner
            ).status_code
            == 409
        )
        for method, suffix in (
            ("get", ""),
            ("get", "/download"),
            ("post", "/retry"),
            ("delete", ""),
        ):
            assert (
                getattr(client, method)(
                    f"/api/v1/note-exports/{row['id']}{suffix}", headers=stranger
                ).status_code
                == 404
            )
        # Simulate a job created by the previous application version.
        with SessionLocal() as db:
            db.get(NoteExport, row["id"]).sources_json = {}
            db.commit()
        row = done(client, owner, row)
        assert row["layout"] == "legacy"
        assert row["job"]["status"] == "SUCCEEDED", row
        with downloaded(client, owner, row) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            assert len(manifest["notes"]) == 2 and len(manifest["assets"]) == 1
            saved = next(n for n in manifest["notes"] if n["id"] == current["id"])
            assert saved["tags"] == ["期末"]
            assert archive.read(saved["content_file"]) == body.encode("utf-8")
            assert saved["content_sha256"] == hashlib.sha256(body.encode()).hexdigest()
            md = archive.read(saved["markdown_file"]).decode()
            assert saved["markdown_file"] == "notes/资料测试/调度笔记.md"
            assert saved["content_file"] == "sources/资料测试/调度笔记.md"
            linked_paths = [
                posixpath.normpath(
                    posixpath.join(
                        posixpath.dirname(saved["markdown_file"]), unquote(url)
                    )
                )
                for url in re.findall(r"\]\(([^)]+)\)", md)
                if not url.startswith("https:")
            ]
            assert "notes/未分类/跨课程或未分类目标.md" in linked_paths
            assert manifest["assets"][0]["file"] in linked_paths
            assert all(path in archive.namelist() for path in linked_paths)
            assert "图片不可用" in md and "目标笔记不可用" in md
            assert "不应泄露的秘密" not in archive.read("manifest.json").decode()
            assert all(
                ".." not in name and not name.startswith("/")
                for name in archive.namelist()
            )
            for entry in manifest["files"]:
                data = archive.read(entry["path"])
                assert len(data) == entry["size_bytes"]
                assert hashlib.sha256(data).hexdigest() == entry["sha256"]
            assert archive.read(manifest["assets"][0]["file"]) == png()
            assert row["filename"].startswith("Hustudy-笔记知识库-")
            response = client.get(
                f"/api/v1/note-exports/{row['id']}/download", headers=owner
            )
            assert (
                unquote(
                    response.headers["content-disposition"]
                    .split("UTF-8''")[-1]
                    .split("utf-8''")[-1]
                )
                == row["filename"]
            )
            citation = manifest["citations"][0]
            assert (
                citation["version_id"] == source["resource_id"]
                and citation["chunk_id"] == chunk["id"]
            )
            assert (
                citation["quote_hash"]
                == hashlib.sha256(chunk["text"].encode()).hexdigest()
            )
        assert client.get("/api/v1/note-exports", headers=stranger).json() == []
        package = tmp_path / "notes.zip"
        package.write_bytes(
            client.get(
                f"/api/v1/note-exports/{row['id']}/download", headers=owner
            ).content
        )
        spec = importlib.util.spec_from_file_location(
            "verify_notes",
            Path(__file__).resolve().parents[2] / "scripts/verify_note_package.py",
        )
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        assert verifier.verify(package) == (2, 1, 5)
        with zipfile.ZipFile(package, "a") as archive:
            archive.writestr("unexpected.txt", b"tampered")
        with pytest.raises(ValueError, match="清单"):
            verifier.verify(package)
        # Disposable export control rows and jobs never enter full-account business data.
        backup, _ = exported(client, owner)
        with zipfile.ZipFile(io.BytesIO(backup)) as archive:
            tables = json.loads(archive.read("manifest.json"))["tables"]
            assert "note_exports" not in tables
            assert all(j["type"] != "NOTE_EXPORT" for j in tables["processing_jobs"])


@pytest.mark.parametrize("removed", ["note", "asset", "document", "course"])
def test_source_revocation_blocks_old_downloads_and_new_snapshot_marks_missing(removed):
    with TestClient(app) as client:
        owner, course = context(client)
        target = note(client, owner, course)
        asset = image(client, owner, course)
        source = upload(client, owner, course, "# 来源\n\n可引用的来源正文。")
        drain_jobs()
        chunk = client.get(
            f"/api/v1/versions/{source['resource_id']}/chunks", headers=owner
        ).json()[0]
        note(
            client,
            owner,
            course,
            content=f"[[note:{target['id']}]] ![[asset:{asset['id']}]]",
            citations=[
                {
                    "version_id": source["resource_id"],
                    "chunk_id": chunk["id"],
                    "quote": chunk["text"],
                }
            ],
        )
        row = done(client, owner, create(client, owner))
        version = client.get(
            f"/api/v1/versions/{source['resource_id']}", headers=owner
        ).json()
        path = {
            "note": f"notes/{target['id']}?revision=1",
            "asset": f"assets/{asset['id']}",
            "document": f"documents/{version['document_id']}",
            "course": f"courses/{course}?revision=1",
        }[removed]
        assert client.delete("/api/v1/" + path, headers=owner).status_code == 204
        assert (
            client.get(
                f"/api/v1/note-exports/{row['id']}/download", headers=owner
            ).status_code
            == 404
        )
        assert (
            client.get(f"/api/v1/note-exports/{row['id']}", headers=owner).json()[
                "availability"
            ]
            == "unavailable"
        )
        if removed == "course":
            assert (
                client.post(
                    "/api/v1/note-exports",
                    headers=owner,
                    json={"request_id": str(uuid4())},
                ).status_code
                == 409
            )
        else:
            fresh = done(client, owner, create(client, owner))
            with downloaded(client, owner, fresh) as archive:
                if removed == "document":
                    assert any(
                        "来源当前不可用" in archive.read(path).decode()
                        for path in archive.namelist()
                        if path.endswith(".md")
                    )


def test_corrupt_image_failure_cleanup_retry_and_corrupt_download():
    with TestClient(app) as client:
        owner, course = context(client)
        asset = image(client, owner, course)
        note(client, owner, course, content=f"![[asset:{asset['id']}]]")
        with SessionLocal() as db:
            image_path = Path(db.get(Asset, asset["id"]).storage_path)
        original = image_path.read_bytes()
        image_path.write_bytes(b"bad image")
        row = done(client, owner, create(client, owner))
        assert row["job"]["status"] == "FAILED" and "hash" in row["job"]["error"]
        with SessionLocal() as db:
            stored = db.get(NoteExport, row["id"])
            assert stored.zip_path is None
            assert not list(
                note_package.output_path(
                    stored.user_id, stored.id, str(uuid4())
                ).parent.glob("*.zip")
            )
        image_path.write_bytes(original)
        assert (
            client.post(
                f"/api/v1/note-exports/{row['id']}/retry", headers=owner
            ).status_code
            == 202
        )
        row = done(client, owner, row)
        assert row["job"]["status"] == "SUCCEEDED" and row["job"]["attempt_count"] == 2
        with SessionLocal() as db:
            output = Path(db.get(NoteExport, row["id"]).zip_path)
        output.write_bytes(b"tampered")
        assert (
            client.get(
                f"/api/v1/note-exports/{row['id']}/download", headers=owner
            ).status_code
            == 409
        )
        assert (
            client.delete(
                f"/api/v1/note-exports/{row['id']}", headers=owner
            ).status_code
            == 204
        )
        assert not output.exists()


@pytest.mark.parametrize("kind", ["cancel", "delete_source"])
def test_late_worker_cannot_publish_after_revocation(monkeypatch, kind):
    with TestClient(app) as client:
        owner, course = context(client)
        current = note(client, owner, course)
        row = create(client, owner)
        build = worker.build_package
        outputs = []

        def interrupted(db, user_id, output, options=None):
            result = build(db, user_id, output, options=options)
            outputs.append(output)
            path = (
                f"note-exports/{row['id']}"
                if kind == "cancel"
                else f"notes/{current['id']}?revision=1"
            )
            assert client.delete("/api/v1/" + path, headers=owner).status_code == 204
            return result

        monkeypatch.setattr(worker, "build_package", interrupted)
        assert worker.run_note_export_once()
        assert all(not path.exists() for path in outputs)
        with SessionLocal() as db:
            job = db.get(ProcessingJob, row["job"]["id"])
            assert job.status == ("CANCELLED" if kind == "cancel" else "FAILED")


def test_expired_lease_recovers_and_budget_failure_stops_cleanly(monkeypatch):
    with TestClient(app) as client:
        owner, course = context(client)
        note(client, owner, course)
        row = create(client, owner)
        with SessionLocal() as db:
            job = worker.claim_export(db)
            assert job.id == row["job"]["id"]
            old_token = job.lease_token
            output = note_package.output_path(job.user_id, job.id, old_token)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"partial")
            job.lease_until = utc_now() - timedelta(seconds=1)
            db.commit()
        monkeypatch.setattr(note_package, "MAX_CONTENT", 1)
        row = done(client, owner, row)
        assert row["job"]["status"] == "FAILED" and row["job"]["attempt_count"] == 2
        assert not output.exists()
        assert "预算" in row["job"]["error"]


def test_delete_conflict_preserves_note_and_idempotent_create_retries():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, _ = context(client)
        request_id = str(uuid4())
        current = note(client, owner, course, request_id=request_id)
        assert note(client, owner, course, request_id=request_id)["id"] == current["id"]
        assert (
            client.post(
                "/api/v1/notes",
                headers=stranger,
                json={"title": "x", "request_id": request_id},
            ).status_code
            == 404
        )
        path = f"/api/v1/notes/{current['id']}"
        assert (
            client.patch(
                path, headers=owner, json={"revision": 1, "content": "其他窗口"}
            ).status_code
            == 200
        )
        conflict = client.delete(path + "?revision=1", headers=owner)
        assert (
            conflict.status_code == 409
            and conflict.json()["error"]["details"]["server_content"] == "其他窗口"
        )
        assert client.get(path, headers=owner).json()["content"] == "其他窗口"
        assert client.delete(path + "?revision=2", headers=stranger).status_code == 404
        assert client.delete(path + "?revision=2", headers=owner).status_code == 204
        assert client.get(path, headers=owner).status_code == 404
        with SessionLocal() as db:
            assert db.scalar(select(Note).where(Note.id == request_id)).deleted
