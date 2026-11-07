import io
from datetime import timedelta
from uuid import uuid4
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from app.main import app
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.models import NoteCapture, ProcessingJob
from app.models.base import utc_now
from app.services.note_recognition import recognize
from app.workers import note_capture as worker
from tests.m1.test_materialhub import context


def docx():
    document = Document()
    document.add_heading("测试笔记", 1)
    document.add_paragraph("知识点：事务具有原子性。")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text, table.cell(0, 1).text = "概念", "定义"
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def upload(client, headers, course, content=None, request_id=None, name="课堂.docx"):
    return client.post(
        "/api/v1/note-captures",
        headers=headers,
        data={"course_id": course, "request_id": request_id or str(uuid4())},
        files={"file": (name, docx() if content is None else content)},
    )


def test_capture_real_docx_isolated_text_without_new_note():
    with TestClient(app) as client:
        headers, course = context(client)
        row = upload(client, headers, course).json()
        assert row["status"] == "QUEUED"
        assert worker.run_capture_once()
        result = client.get(
            "/api/v1/note-captures/" + row["id"], headers=headers
        ).json()
        assert result["status"] == "SUCCEEDED", result
        assert "事务具有原子性" in result["result"]["text"]
        assert "概念 | 定义" in result["result"]["text"]
        assert client.get("/api/v1/notes", headers=headers).json() == []
        assert result["result"]["text"] == "\n\n".join(
            part["text"] for part in result["result"]["parts"] if part["text"].strip()
        )
        assert not result["result"]["text"].startswith("### ")


def test_capture_ownership_idempotency_cancel_and_source():
    with TestClient(app) as client:
        headers, course = context(client)
        stranger, _ = context(client)
        data, identity = docx(), str(uuid4())
        row = upload(client, headers, course, data, identity).json()
        assert upload(client, headers, course, data, identity).json()["id"] == row["id"]
        assert upload(client, headers, course, b"changed", identity).status_code == 409
        for route in ["", "/file"]:
            assert (
                client.get(
                    "/api/v1/note-captures/" + row["id"] + route, headers=stranger
                ).status_code
                == 404
            )
        assert (
            client.delete(
                "/api/v1/note-captures/" + row["id"], headers=stranger
            ).status_code
            == 404
        )
        assert (
            client.get(
                "/api/v1/note-captures/" + row["id"] + "/file", headers=headers
            ).content
            == data
        )
        assert (
            client.delete(
                "/api/v1/note-captures/" + row["id"], headers=headers
            ).status_code
            == 204
        )
        assert (
            client.get(
                "/api/v1/note-captures/" + row["id"], headers=headers
            ).status_code
            == 404
        )


def test_capture_format_size_and_parser_errors():
    with TestClient(app) as client:
        headers, course = context(client)
        assert upload(client, headers, course, b"x", name="old.doc").status_code == 422
        assert upload(client, headers, course, b"").status_code == 413
        row = upload(client, headers, course, b"broken").json()
        assert worker.run_capture_once()
        result = client.get(
            "/api/v1/note-captures/" + row["id"], headers=headers
        ).json()
        assert result["status"] == "FAILED"
        assert not result["result"]


def test_ai_disabled_with_credentials_and_no_dispatch(monkeypatch):
    from app.ai.providers import ZhipuProvider

    calls = []
    monkeypatch.setattr(ZhipuProvider, "structured", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(get_settings(), "llm_provider", "zhipu")
    with TestClient(app) as client:
        owner, course = context(client)
        other, _ = context(client)
        row = upload(client, owner, course).json()
        endpoint = "/api/v1/note-captures/" + row["id"] + "/organize"
        payload = {
            "request_id": str(uuid4()),
            "text": "核对文本",
            "mode": "format",
            "model": get_settings().llm_model,
            "confirmed": True,
        }
        assert client.post(endpoint, json=payload).status_code == 401
        assert client.post(endpoint, headers=other, json=payload).status_code == 404
        result = client.post(endpoint, headers=owner, json=payload)
        assert result.status_code == 410 and "停用" in result.text
        caps = client.get("/api/v1/note-captures/capabilities", headers=owner).json()
        assert caps["ai"] is False
        assert (
            client.get("/api/v1/note-captures/" + row["id"], headers=owner).json()[
                "kind"
            ]
            == "NOTE_CAPTURE"
        )
        client.delete("/api/v1/note-captures/" + row["id"], headers=owner)
        assert not worker.run_capture_once()
        assert calls == []


def test_legacy_ai_jobs_cancel_leases_and_preserve_results(monkeypatch):
    from app.ai.providers import ZhipuProvider
    from sqlalchemy import update

    calls = []
    monkeypatch.setattr(ZhipuProvider, "structured", lambda *a, **k: calls.append(a))
    with TestClient(app) as client:
        owner, course = context(client)
        ids = []
        for state in ["QUEUED", "RUNNING", "SUCCEEDED"]:
            row = upload(client, owner, course).json()
            ids.append((row["id"], state))
            with SessionLocal() as db:
                capture = db.get(NoteCapture, row["id"])
                capture.result = {"text": "旧识别文本"}
                capture.ai_result = {"markdown": "历史结果"}
                job = db.get(ProcessingJob, capture.job_id)
                job.type, job.status = "NOTE_ORGANIZE", state
                job.lease_token = "old-lease"
                job.lease_until = utc_now() + timedelta(minutes=5)
                db.commit()
        assert not worker.run_capture_once()
        assert calls == []
        for capture_id, state in ids:
            result = client.get(
                "/api/v1/note-captures/" + capture_id, headers=owner
            ).json()
            assert result["status"] == (
                "SUCCEEDED" if state == "SUCCEEDED" else "CANCELLED"
            )
            assert result["result"]["text"] == "旧识别文本"
            assert result["ai_result"]["markdown"] == "历史结果"
            if state != "SUCCEEDED":
                with SessionLocal() as db:
                    capture = db.get(NoteCapture, capture_id)
                    job = db.get(ProcessingJob, capture.job_id)
                    assert job.lease_token is None and job.lease_until is None
                    late = db.execute(
                        update(ProcessingJob)
                        .where(
                            ProcessingJob.id == job.id,
                            ProcessingJob.lease_token == "old-lease",
                            ProcessingJob.status == "RUNNING",
                        )
                        .values(status="SUCCEEDED")
                    )
                    assert late.rowcount == 0
        assert client.get("/api/v1/notes", headers=owner).json() == []


def test_expired_lease_not_replayed_and_deleted_result_discarded(monkeypatch):
    with TestClient(app) as client:
        headers, course = context(client)
        row = upload(client, headers, course).json()
        with SessionLocal() as db:
            capture = db.get(NoteCapture, row["id"])
            job = db.get(ProcessingJob, capture.job_id)
            job.status, job.lease_until = "RUNNING", utc_now() - timedelta(minutes=1)
            db.commit()
        assert not worker.run_capture_once()
        assert (
            client.get("/api/v1/note-captures/" + row["id"], headers=headers).json()[
                "status"
            ]
            == "FAILED"
        )
        new = upload(client, headers, course).json()

        def during(_):
            assert (
                client.delete(
                    "/api/v1/note-captures/" + new["id"], headers=headers
                ).status_code
                == 204
            )
            return {"text": "late"}

        monkeypatch.setattr(worker, "recognize_isolated", during)
        assert worker.run_capture_once()
        assert (
            client.get(
                "/api/v1/note-captures/" + new["id"], headers=headers
            ).status_code
            == 404
        )


def test_pdf_page_budget_and_ocr_page_provenance(tmp_path, monkeypatch):
    writer = PdfWriter()
    for _ in range(41):
        writer.add_blank_page(100, 100)
    path = tmp_path / "too-many.pdf"
    writer.write(path)
    import pytest

    with pytest.raises(ValueError, match="40页"):
        recognize(path)


def test_ocr_result_with_local_adapter(tmp_path, monkeypatch):
    from PIL import Image
    import app.services.note_recognition as recognition

    path = tmp_path / "test.png"
    Image.new("RGB", (20, 20), "white").save(path)
    monkeypatch.setattr(recognition, "ocr", lambda _: "识别示例")
    result = recognize(path)
    assert result["parts"] == [
        {"location": "图片", "text": "识别示例", "method": "ocr"}
    ]
    assert result["text"] == "识别示例"
    assert result["warnings"]


def test_scanned_pdf_real_renderer_lifecycle(tmp_path, monkeypatch):
    import pytest

    pytest.importorskip("pypdfium2")
    import app.services.note_recognition as recognition

    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    writer.add_blank_page(100, 100)
    path = tmp_path / "scanned.pdf"
    writer.write(path)
    monkeypatch.setattr(recognition, "ocr", lambda _: "扫描内容")
    result = recognize(path)
    assert [part["location"] for part in result["parts"]] == ["第1页", "第2页"]
    assert all(part["method"] == "ocr" for part in result["parts"])
    assert result["text"] == "扫描内容\n\n扫描内容"
    path.unlink()  # Windows must not retain a PDFium file handle.


def test_ai_unconfigured_reason_and_no_job_submission():
    with TestClient(app) as client:
        headers, course = context(client)
        result = client.get(
            "/api/v1/note-captures/capabilities", headers=headers
        ).json()
        assert result["ai"] is False
        assert "停用" in result["ai_unavailable_reason"]
        assert "deterministic-test-key" not in str(result)
