"""Actual API-owned subprocess lifecycle in a separate database/storage."""

import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]


def eventually(read, accept, timeout=30):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        try:
            last = read()
            if accept(last):
                return last
        except (httpx.HTTPError, OSError, ValueError):
            pass
        time.sleep(0.1)
    raise AssertionError(
        "isolated processing lifecycle did not reach expected state: " + str(last)
    )


@pytest.mark.skipif(
    os.name == "nt",
    reason="POSIX process-group lifecycle; Windows real-device cleanup is separately pending",
)
def test_api_starts_worker_duplicate_rejected_crash_restarts_and_shutdown_releases_lock(
    tmp_path, monkeypatch
):
    from app.services import worker_runtime

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    storage = tmp_path / "storage"
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "backend"),
        "HUSTUDY_ENV": "development",
        "HUSTUDY_DATABASE_URL": "sqlite:///" + str(tmp_path / "lifecycle.db"),
        "HUSTUDY_STORAGE_ROOT": str(storage),
        "HUSTUDY_JWT_SECRET": "isolated-worker-lifecycle-secret-2026-only",
        "HUSTUDY_WORKER_AUTOSTART": "true",
        "HUSTUDY_LLM_PROVIDER": "mock",
        "HUSTUDY_ZHIPU_API_KEY": "",
        "HUSTUDY_LIBREOFFICE_PATH": "/nonexistent/lifecycle-office",
    }
    with (
        (tmp_path / "api.log").open("w") as log,
        httpx.Client(
            base_url=f"http://127.0.0.1:{port}", timeout=10, trust_env=False
        ) as client,
    ):
        api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            eventually(
                lambda: client.get("/health").status_code, lambda value: value == 200
            )
            assert client.get("/api/v1/processing/status").status_code == 401
            auth = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "lifecycle_owner",
                    "password": "isolated-test-password",
                },
            ).json()
            headers = {"Authorization": "Bearer " + auth["access_token"]}

            def status():
                return client.get("/api/v1/processing/status", headers=headers).json()

            ready = eventually(status, lambda value: value.get("state") == "ready")
            assert set(ready) == {"state", "message", "checked_at"}
            assert str(storage) not in json.dumps(ready)
            course = client.post(
                "/api/v1/courses",
                headers=headers,
                json={"name": "managed process isolation"},
            ).json()["id"]
            started = time.monotonic()
            upload = client.post(
                f"/api/v1/courses/{course}/documents",
                headers=headers,
                files={
                    "file": (
                        "native.pptx",
                        (ROOT / "fixtures/native_preview.pptx").read_bytes(),
                        "application/octet-stream",
                    )
                },
            )
            assert upload.status_code == 202
            first = upload.json()

            def version():
                return client.get(
                    f"/api/v1/versions/{first['resource_id']}", headers=headers
                ).json()

            eventually(
                version,
                lambda value: value.get("parse_status")
                == value.get("index_status")
                == "SUCCEEDED",
            )
            first_elapsed = time.monotonic() - started
            heartbeat = next(storage.glob(".runtime/*/heartbeat.json"))
            first_pid = json.loads(heartbeat.read_text())["pid"]
            duplicate = subprocess.run(
                [sys.executable, "-m", "app.workers.materials"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                timeout=10,
            )
            assert duplicate.returncode == 73
            job = client.get(f"/api/v1/jobs/{first['id']}", headers=headers).json()
            assert job["attempt_count"] == 1
            # A crashed process releases its OS lock; no manual job reset/reupload.
            os.kill(first_pid, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)
            new_pid = eventually(
                lambda: json.loads(heartbeat.read_text())["pid"],
                lambda value: value != first_pid,
            )
            assert new_pid > 0
            eventually(status, lambda value: value.get("state") == "ready")
            second = client.post(
                f"/api/v1/courses/{course}/documents",
                headers=headers,
                files={
                    "file": (
                        "after-restart.md",
                        b"# Source\nContinue after supervised worker restart.",
                        "text/markdown",
                    )
                },
            )
            assert second.status_code == 202
            next_version = second.json()["resource_id"]
            eventually(
                lambda: client.get(
                    f"/api/v1/versions/{next_version}", headers=headers
                ).json(),
                lambda value: value.get("index_status") == "SUCCEEDED",
            )
            print(
                f"isolated small-PPT upload+parse+index {first_elapsed:.2f}s; crash recovery and subsequent upload verified"
            )
        finally:
            api.terminate()
            try:
                api.wait(timeout=12)
            except subprocess.TimeoutExpired:
                api.kill()
                api.wait(timeout=5)
        folder = next(storage.glob(".runtime/*"))
        monkeypatch.setattr(worker_runtime, "runtime_directory", lambda: folder)
        eventually(
            worker_runtime.processing_status,
            lambda value: value == "unavailable",
            timeout=10,
        )
