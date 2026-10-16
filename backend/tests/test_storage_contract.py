import errno
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.core import storage
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.models import DocumentVersion
from app.workers.materials import drain_jobs, parse_isolated, preview_file
from app.workers.material_exports import run_export_once
from test_materialhub import context, upload
from test_material_exports import create
from test_preview_assets import png


def low_disk(monkeypatch):
    monkeypatch.setattr(storage.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))


def test_atomic_publish_does_not_overwrite_or_leave_partial_files(
    tmp_path, monkeypatch
):
    store = storage.LocalFileStorage(tmp_path)
    target = store.new_path(str(uuid4()), str(uuid4()), ".md")
    store.write(target, b"original")
    with pytest.raises(FileExistsError):
        store.write(target, b"replacement")
    assert target.read_bytes() == b"original"
    assert not list(tmp_path.rglob(".upload-*"))
    failed = target.with_name("failed.md")

    def disk_full(*_):
        raise OSError(errno.ENOSPC, "injected disk full")

    monkeypatch.setattr(storage.os, "fsync", disk_full)
    with pytest.raises(storage.InsufficientStorage):
        store.write(failed, b"new data")
    assert not failed.exists()
    assert not list(tmp_path.rglob(".upload-*"))
    assert target.read_bytes() == b"original"


def test_storage_rejects_traversal_symlink_and_low_capacity(tmp_path, monkeypatch):
    root = tmp_path / "store"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    store = storage.LocalFileStorage(root)
    for path in [outside / "x", root / ".." / "outside" / "x", root / "link" / "x"]:
        with pytest.raises(ValueError):
            store.write(path, b"forbidden")
    low_disk(monkeypatch)
    with pytest.raises(storage.InsufficientStorage):
        store.write(root / "new.md", b"content")
    assert not list(outside.iterdir())
    assert not (root / "new.md").exists()


def test_low_disk_upload_and_images_return_507_keep_prior_data(tmp_path, monkeypatch):
    with TestClient(app) as client:
        headers, course = context(client)
        original = upload(client, headers, course, "# 原文\n\n必须保留的数据。")
        drain_jobs()
        documents = f"/api/v1/courses/{course}/documents"
        before = client.get(documents, headers=headers).json()
        with SessionLocal() as db:
            source = Path(db.get(DocumentVersion, original["resource_id"]).source_path)
        before_bytes = source.read_bytes()
        before_files = set(source.parent.rglob("*"))
        low_disk(monkeypatch)
        for path, name, body in [
            (documents, "new.md", b"# another source"),
            (f"/api/v1/courses/{course}/assets", "image.png", png()),
        ]:
            response = client.post(path, headers=headers, files={"file": (name, body)})
            assert response.status_code == 507, response.text
            assert response.json()["error"]["code"] == "INSUFFICIENT_STORAGE"
            assert (
                response.json()["error"]["request_id"]
                == response.headers["X-Request-ID"]
            )
        assert client.get(documents, headers=headers).json() == before
        assert (
            client.get(
                f"/api/v1/versions/{original['resource_id']}/original", headers=headers
            ).content
            == before_bytes
        )
        assert source.read_bytes() == before_bytes
        assert set(source.parent.rglob("*")) == before_files
        # Hash duplicate returns the original task even with no writable capacity.
        assert upload(client, headers, course, before_bytes)["id"] == original["id"]


def test_database_commit_failure_removes_only_newly_published_file(monkeypatch):
    with TestClient(app) as client:
        headers, course = context(client)
        original = upload(client, headers, course, "# 原资料\n\n保留原文。")
        with SessionLocal() as db:
            source = Path(db.get(DocumentVersion, original["resource_id"]).source_path)
        before = set(source.parent.rglob("*"))
        from sqlalchemy.orm import Session

        def fail_commit(_):
            raise RuntimeError("injected commit failure")

        monkeypatch.setattr(Session, "commit", fail_commit)
        # Preserve the application's production error response, not TestClient re-raise.
        with TestClient(app, raise_server_exceptions=False) as safe:
            response = safe.post(
                f"/api/v1/courses/{course}/documents",
                headers=headers,
                files={"file": ("next.md", b"# rejected new file")},
            )
        assert response.status_code == 500
        assert set(source.parent.rglob("*")) == before
        assert source.is_file()


def test_parse_preview_and_export_fail_explicitly_on_low_disk(monkeypatch, tmp_path):
    source = tmp_path / "source.docx"
    source.write_bytes(b"test")
    with TestClient(app) as client:
        headers, course = context(client)
        job = upload(client, headers, course, "# 已保存\n\n保留检索。")
        drain_jobs()
        package = create(client, headers, course)
        low_disk(monkeypatch)
        monkeypatch.setattr(
            "app.services.preview_runtime.office_executable", lambda: "/fake/soffice"
        )
        with pytest.raises(storage.InsufficientStorage):
            parse_isolated(source)
        with pytest.raises(storage.InsufficientStorage):
            preview_file(source)
        assert run_export_once()
        failed = client.get(
            f"/api/v1/material-exports/{package['id']}", headers=headers
        ).json()
        assert failed["job"]["status"] == "FAILED"
        assert "磁盘" in failed["job"]["error"]
        assert (
            client.get(
                f"/api/v1/versions/{job['resource_id']}/original", headers=headers
            ).status_code
            == 200
        )
        user_id = client.get("/api/v1/auth/me", headers=headers).json()["id"]
        root = Path(get_settings().storage_root) / user_id / course
        assert not list(root.rglob("*.zip"))
