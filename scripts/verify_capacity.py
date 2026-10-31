"""Isolated, reproducible NFR-01/02/03 probe. Never opens the user database.

Run: .venv/bin/python scripts/verify_capacity.py --output /tmp/hustudy-capacity.json
Uses self-authored inputs, real uploads/parsing/indexing and loopback HTTP reads.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import logging
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "backend"))
    with tempfile.TemporaryDirectory(prefix="hustudy-capacity-") as scratch:
        os.environ.update(
            {
                "HUSTUDY_DATABASE_URL": f"sqlite:///{scratch}/capacity.db",
                "HUSTUDY_STORAGE_ROOT": f"{scratch}/storage",
                "HUSTUDY_JWT_SECRET": "isolated-capacity-test-secret-never-for-real-use",
                "HUSTUDY_LLM_PROVIDER": "mock",
                "HUSTUDY_ZHIPU_API_KEY": "",
                "HUSTUDY_LIBREOFFICE_PATH": "/nonexistent/capacity-no-office",
                "PYTHONPATH": str(root / "backend"),
            }
        )
        import httpx
        from fastapi.testclient import TestClient
        from sqlalchemy import select, func, text
        from app.main import app
        from app.models import Course, Document, DocumentVersion, DocumentChunk, Note
        from app.core.database import SessionLocal
        from app.workers.materials import drain_jobs, run_once

        for name in ("httpx", "hustudy"):
            logging.getLogger(name).setLevel(logging.WARNING)
        with TestClient(app) as client:
            auth = client.post(
                "/api/v1/auth/register",
                json={"username": "capacity_probe", "password": "Synthetic-only-2026"},
            ).json()
            headers = {"Authorization": "Bearer " + auth["access_token"]}
            courses = []
            print(
                "Seeding isolated 10 courses / 200 uploads / 1000 notes...", flush=True
            )
            for ci in range(10):
                course = client.post(
                    "/api/v1/courses", headers=headers, json={"name": f"容量课程{ci}"}
                ).json()["id"]
                courses.append(course)
                for di in range(20):
                    body = "\n\n".join(
                        f"# 第{pi}节\n课程{ci}资料{di}片段{pi}。"
                        + ("滑动窗口协议控制传输速率，确认机制避免重复交付。" * 25)
                        for pi in range(25)
                    )
                    response = client.post(
                        f"/api/v1/courses/{course}/documents",
                        headers=headers,
                        files={"file": (f"lesson{di}.md", body, "text/markdown")},
                    )
                    assert response.status_code == 202, response.text
            with SessionLocal() as db:
                db.add_all(
                    [
                        Note(
                            user_id=auth["user"]["id"],
                            course_id=courses[i // 100],
                            title=f"笔记{i:04}",
                            content=f"容量笔记{i}。"
                            + ("滑动窗口协议与确认机制。" * 80),
                        )
                        for i in range(1000)
                    ]
                )
                db.commit()
            # The managed worker may still be committing the final index batch when
            # the synchronous drain returns. Wait for the explicit terminal state
            # instead of turning scheduler timing into a flaky capacity failure.
            deadline = time.monotonic() + 30
            while True:
                with SessionLocal() as db:
                    pending_versions = db.scalar(
                        select(func.count())
                        .select_from(DocumentVersion)
                        .where(DocumentVersion.index_status != "SUCCEEDED")
                    )
                if pending_versions == 0:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"capacity seed did not finish indexing ({pending_versions} versions pending)"
                    )
                drain_jobs(limit=1000)
                time.sleep(0.05)
            with SessionLocal() as db:
                counts = {
                    name: db.scalar(select(func.count()).select_from(model))
                    for name, model in [
                        ("courses", Course),
                        ("documents", Document),
                        ("notes", Note),
                        ("chunks", DocumentChunk),
                    ]
                }
                assert counts == {
                    "courses": 10,
                    "documents": 200,
                    "notes": 1000,
                    "chunks": 5000,
                }, counts
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(DocumentVersion)
                        .where(DocumentVersion.index_status != "SUCCEEDED")
                    )
                    == 0
                )
                assert db.scalar(text("PRAGMA foreign_key_check")) is None
        # A separate API process prevents seeding in-memory objects from warming API state.
        with (
            socket.socket() as listener,
            open(Path(scratch) / "server.log", "w") as log,
        ):
            listener.bind(("127.0.0.1", 0))
            listener.listen(128)
            port = listener.getsockname()[1]
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--fd",
                    str(listener.fileno()),
                    "--log-level",
                    "warning",
                ],
                cwd=root,
                env=dict(os.environ),
                pass_fds=(listener.fileno(),),
                stdout=log,
                stderr=log,
            )
            try:
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{port}",
                    headers=headers,
                    timeout=10,
                    limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
                    trust_env=False,
                ) as http:
                    for _ in range(100):
                        try:
                            if http.get("/health").status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        if server.poll() is not None:
                            raise RuntimeError("isolated API exited")
                        time.sleep(0.05)
                    else:
                        raise RuntimeError("isolated API did not become ready")
                    c = courses[0]
                    endpoints = {
                        "courses": ("/api/v1/courses", lambda r: len(r) == 10),
                        "notes": ("/api/v1/notes", lambda r: len(r) == 1000),
                        "material_search": (
                            f"/api/v1/courses/{c}/search/page?q=滑动窗口&latest_only=true",
                            lambda r: r["total"] == 500 and len(r["items"]) == 12,
                        ),
                        "note_search": (
                            f"/api/v1/courses/{c}/note-search?q=滑动窗口",
                            lambda r: r["total"] == 100 and len(r["items"]) == 12,
                        ),
                        "document_page": (
                            f"/api/v1/courses/{c}/documents/page",
                            lambda r: r["total"] == 20,
                        ),
                    }
                    results = {}
                    for label, (path, validate) in endpoints.items():

                        def read(_index=0):
                            started = time.perf_counter()
                            response = http.get(path)
                            elapsed = (time.perf_counter() - started) * 1000
                            assert response.status_code == 200, (
                                label,
                                response.status_code,
                            )
                            assert validate(response.json()), label
                            return elapsed

                        first = read()
                        with ThreadPoolExecutor(max_workers=4) as pool:
                            times = list(pool.map(read, range(100)))
                        ordered = sorted(times)
                        results[label] = {
                            "first_request_ms": round(first, 3),
                            "requests": 100,
                            "concurrency": 4,
                            "p50_ms": round(ordered[49], 3),
                            "p95_ms": round(
                                ordered[math.ceil(0.95 * len(ordered)) - 1], 3
                            ),
                            "max_ms": round(max(times), 3),
                            "status_and_shape_ok": 100,
                        }
                        print(label, results[label], flush=True)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
        # Separate processing measurement with exact requested page/slide sample sizes.
        from pptx import Presentation
        from pypdf import PdfReader, PdfWriter

        presentation = Presentation()
        for index in range(20):
            slide = presentation.slides.add_slide(presentation.slide_layouts[1])
            slide.shapes.title.text = f"Synthetic lesson {index + 1}"
            slide.placeholders[
                1
            ].text = "Sliding window protocol confirms data and controls transmission."
        deck = BytesIO()
        presentation.save(deck)
        pdf = PdfWriter()
        sample = PdfReader(root / "fixtures/preview_demo.pdf")
        for _ in range(50):
            pdf.add_page(sample.pages[0])
        pages = BytesIO()
        pdf.write(pages)
        processing = {}
        with TestClient(app) as client:
            for label, data in [
                ("20_slides.pptx", deck.getvalue()),
                ("50_pages.pdf", pages.getvalue()),
            ]:
                started = time.perf_counter()
                response = client.post(
                    f"/api/v1/courses/{courses[0]}/documents",
                    headers=headers,
                    files={"file": (label, data)},
                )
                assert response.status_code == 202, response.text
                version_id = response.json()["resource_id"]
                for _ in range(10):
                    with SessionLocal() as db:
                        state = db.get(DocumentVersion, version_id).index_status
                    if state == "SUCCEEDED":
                        break
                    assert run_once(), "no processing job available"
                else:
                    raise RuntimeError("sample index did not succeed")
                elapsed = time.perf_counter() - started
                with SessionLocal() as db:
                    count = db.scalar(
                        select(func.count())
                        .select_from(DocumentChunk)
                        .where(DocumentChunk.version_id == version_id)
                    )
                assert count == (20 if label.endswith("pptx") else 50), count
                processing[label] = {
                    "parse_index_seconds": round(elapsed, 4),
                    "chunks": count,
                    "bytes": len(data),
                    "under_60_seconds": elapsed <= 60,
                }
                print(label, processing[label], flush=True)
        report = {
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "machine": platform.machine(),
                "logical_cpus": os.cpu_count(),
            },
            "baseline": counts,
            "cache": "First API request after separate API process startup; OS filesystem cache NOT cleared. Then 100 warm requests per endpoint with max 4 concurrent reads. HTTP loopback incl auth/response, elapsed excludes client JSON validation.",
            "percentile": "nearest-rank ceil(0.95*n), milliseconds",
            "reads": results,
            "processing": processing,
            "passed": all(r["p95_ms"] <= 1000 for r in results.values())
            and all(p["under_60_seconds"] for p in processing.values()),
            "limits": "Synthetic contents; not production capacity, browser latency, manual retrieval relevance, Office conversion, external models or clean-machine proof.",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(
            "Report:", args.output, "PASS" if report["passed"] else "FAIL", flush=True
        )
        return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
