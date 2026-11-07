import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import SessionLocal
from app.main import create_app
from app.models import DocumentVersion, ProcessingJob
from app.services import worker_runtime as runtime
from app.services import worker_supervisor as supervisor
from app.services import preview_runtime
from app.workers import materials

ROOT = Path(__file__).resolve().parents[3]


def test_autostart_defaults_and_explicit_external_mode():
    assert Settings(
        _env_file=None, env="development", worker_autostart=None
    ).manage_worker
    assert not Settings(
        _env_file=None, env="production", worker_autostart=None
    ).manage_worker
    assert not Settings(_env_file=None, worker_autostart=False).manage_worker
    assert Settings(
        _env_file=None, env="production", worker_autostart=True
    ).manage_worker


def test_production_native_reading_does_not_require_office_converter():
    assert Settings(_env_file=None, env="production").office_compatibility_enabled is False
    assert Settings(_env_file=None, env="development").office_compatibility_enabled is True


def test_runtime_readonly_lock_freshness_and_duplicate_process(tmp_path, monkeypatch):
    folder = tmp_path / "runtime"
    monkeypatch.setattr(runtime, "runtime_directory", lambda: folder)
    assert runtime.processing_status() == "unavailable"
    assert not folder.exists()
    with runtime.WorkerRuntime() as owner:
        assert runtime.processing_status() == "starting"
        owner.ready = True
        owner.publish()
        assert runtime.processing_status() == "ready"
        with pytest.raises(runtime.WorkerAlreadyRunning):
            with runtime.WorkerRuntime():
                pytest.fail("duplicate worker acquired a held lock")
        code = "from pathlib import Path; import sys; from app.services import worker_runtime as r; r.runtime_directory=lambda:Path(sys.argv[1]);\ntry:\n with r.WorkerRuntime(): pass\nexcept r.WorkerAlreadyRunning: sys.exit(73)"
        result = subprocess.run(
            [sys.executable, "-c", code, str(folder)],
            env={**os.environ, "PYTHONPATH": str(ROOT / "backend")},
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 73
        heartbeat = folder / "heartbeat.json"
        original = json.loads(heartbeat.read_text())
        owner.stop.set()
        owner.thread.join(timeout=3)
        for raw in [
            b"x" * 1025,
            b"{}",
            json.dumps({**original, "updated_at": time.time() - 60}).encode(),
            json.dumps({**original, "updated_at": float("nan")}).encode(),
        ]:
            heartbeat.write_bytes(raw)
            assert runtime.processing_status() == "unavailable"
        owner.publish()
        assert runtime.processing_status() == "ready"
    # A fresh file from a stopped process must not count as available.
    assert runtime.processing_status() == "unavailable"


def test_status_authenticated_safe_projection_and_no_job_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "runtime_directory", lambda: tmp_path / "runtime")
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/processing/status").status_code == 401
        auth = client.post(
            "/api/v1/auth/register",
            json={
                "username": "runtime_" + uuid4().hex,
                "password": "test-password-2026",
            },
        ).json()
        headers = {"Authorization": "Bearer " + auth["access_token"]}
        with SessionLocal() as db:
            before = list(db.scalars(select(ProcessingJob.id)))
        response = client.get("/api/v1/processing/status", headers=headers)
        assert response.status_code == 200
        assert set(response.json()) == {"state", "checked_at", "message"}
        assert response.json()["state"] == "unavailable"
        assert str(tmp_path) not in response.text
        assert not (tmp_path / "runtime").exists()
        with SessionLocal() as db:
            assert list(db.scalars(select(ProcessingJob.id))) == before


def test_supervisor_adopts_external_and_restarts_only_owned_child(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(supervisor.time, "monotonic", lambda: clock[0])
    locked = [True]
    monkeypatch.setattr(supervisor, "inspect_runtime", lambda: (locked[0], None))
    children = []

    class Child:
        code = None

        def __init__(self):
            self.pid = 123456 + len(children)

        def terminate(self):
            self.code = -15

        def kill(self):
            self.code = -9

        def poll(self):
            return self.code

        def wait(self, timeout):
            self.code = -15

    def spawn(*args, **kwargs):
        child = Child()
        children.append(child)
        assert kwargs["env"]["PYTHONPATH"] == str(ROOT / "backend")
        return child

    monkeypatch.setattr(supervisor.subprocess, "Popen", spawn)
    killed = []
    monkeypatch.setattr(
        supervisor.os, "killpg", lambda pid, sig: killed.append(pid), raising=False
    )
    manager = supervisor.ManagedWorker()
    manager.tick()
    manager.close()
    assert not children and not killed
    manager = supervisor.ManagedWorker()
    locked[0] = False
    manager.tick()
    assert len(children) == 1
    manager.tick()
    assert len(children) == 1
    children[0].code = 1
    manager.tick()
    assert len(children) == 1 and manager.delay == 2
    clock[0] += 1
    manager.tick()
    assert len(children) == 2
    manager.close()
    if os.name != "nt":
        assert killed == [children[0].pid, children[1].pid]


def test_slow_preview_does_not_block_parse_index_and_cancel_keeps_lease(
    monkeypatch, tmp_path
):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import get_db

    engine = create_engine(
        "sqlite:///" + str(tmp_path / "lanes.db"),
        connect_args={"check_same_thread": False},
    )
    config = Config(str(ROOT / "backend/alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(materials, "SessionLocal", factory)

    def isolated_db():
        with factory() as db:
            yield db

    app = create_app()
    app.dependency_overrides[get_db] = isolated_db
    entered, release = threading.Event(), threading.Event()

    def slow(source):
        entered.set()
        assert release.wait(15)
        return str(source)

    with TestClient(app) as client:
        auth = client.post(
            "/api/v1/auth/register",
            json={
                "username": "slow_preview_" + uuid4().hex,
                "password": "test-password-2026",
            },
        ).json()
        headers = {"Authorization": "Bearer " + auth["access_token"]}
        course = client.post(
            "/api/v1/courses", headers=headers, json={"name": "slow preview isolation"}
        ).json()["id"]
        first = client.post(
            f"/api/v1/courses/{course}/documents",
            headers=headers,
            files={
                "file": (
                    "preview.pptx",
                    io.BytesIO((ROOT / "fixtures/preview_demo.pptx").read_bytes()),
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )
            },
        ).json()
        materials.run_once(("PARSE", "INDEX"))
        materials.run_once(("PARSE", "INDEX"))
        monkeypatch.setattr(materials, "preview_file", slow)
        monkeypatch.setattr(preview_runtime, "office_executable", lambda: "/fake/office")
        requested = client.post(
            f"/api/v1/versions/{first['resource_id']}/preview-jobs", headers=headers
        )
        assert requested.status_code == 202
        errors = []

        def preview():
            try:
                materials.run_once(("PREVIEW",))
            except Exception as error:
                errors.append(error)

        thread = threading.Thread(target=preview)
        thread.start()
        try:
            assert entered.wait(5)
            second = client.post(
                f"/api/v1/courses/{course}/documents",
                headers=headers,
                files={
                    "file": (
                        "next.md",
                        io.BytesIO(
                            "# New source\nDo not wait for PDF conversion.".encode()
                        ),
                        "text/markdown",
                    )
                },
            ).json()
            materials.run_once(("PARSE", "INDEX"))
            materials.run_once(("PARSE", "INDEX"))
            with factory() as db:
                version = db.get(DocumentVersion, second["resource_id"])
                assert version.parse_status == version.index_status == "SUCCEEDED"
                preview_job = db.scalar(
                    select(ProcessingJob).where(
                        ProcessingJob.resource_id == first["resource_id"],
                        ProcessingJob.type == "PREVIEW",
                    )
                )
                assert (
                    preview_job.status == "RUNNING" and preview_job.attempt_count == 1
                )
                preview_id = preview_job.id
            assert (
                client.post(
                    f"/api/v1/jobs/{preview_id}/cancel", headers=headers
                ).status_code
                == 200
            )
        finally:
            release.set()
            thread.join(timeout=5)
        assert not errors and not thread.is_alive()
        with factory() as db:
            assert db.get(ProcessingJob, preview_id).status == "CANCELLED"
    engine.dispose()
