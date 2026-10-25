import io
from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.main import app
from app.core.database import SessionLocal
from app.models import DocumentVersion, ProcessingJob
from app.models.base import utc_now
from app.services.materials import parse_document
from app.workers.materials import drain_jobs, recover_jobs


def context(client):
    result = client.post(
        "/api/v1/auth/register",
        json={"username": "m1_" + uuid4().hex[:10], "password": "test-password-123"},
    )
    headers = {"Authorization": "Bearer " + result.json()["access_token"]}
    from ai_account_test_support import maybe_seed_account

    maybe_seed_account(client, headers)
    course = client.post(
        "/api/v1/courses", headers=headers, json={"name": "资料测试"}
    ).json()["id"]
    return headers, course


def upload(client, headers, course, content, name="lesson.md"):
    response = client.post(
        f"/api/v1/courses/{course}/documents",
        headers=headers,
        files={"file": (name, content, "application/octet-stream")},
    )
    assert response.status_code == 202, response.text
    return response.json()


def test_immutable_versions_citations_deletion_and_scope():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, _ = context(client)
        job = upload(client, owner, course, "# 窗口机制\n\n窗口机制调节发送速率。")
        assert job["status"] == "QUEUED"
        drain_jobs()
        doc = client.get(f"/api/v1/courses/{course}/documents", headers=owner).json()[0]
        v1 = doc["latest_version_id"]
        chunk = client.get(f"/api/v1/versions/{v1}/chunks", headers=owner).json()[0]
        note = client.post(
            "/api/v1/notes",
            headers=owner,
            json={
                "title": "来源",
                "course_id": course,
                "citations": [
                    {"version_id": v1, "chunk_id": chunk["id"], "quote": "窗口机制"}
                ],
            },
        ).json()
        citation = client.get(
            f"/api/v1/notes/{note['id']}/citations", headers=owner
        ).json()[0]
        assert citation["availability"] == "active"
        newer = client.post(
            f"/api/v1/documents/{doc['id']}/versions",
            headers=owner,
            files={"file": ("new.md", "# 拥塞控制\n\n新版本知识。", "text/markdown")},
        )
        assert newer.status_code == 202
        drain_jobs()
        versions = client.get(
            f"/api/v1/documents/{doc['id']}/versions", headers=owner
        ).json()
        assert [row["version_no"] for row in versions] == [2, 1]
        assert (
            client.get(f"/api/v1/versions/{v1}/chunks", headers=owner).json()[0]["id"]
            == chunk["id"]
        )
        assert (
            "窗口机制"
            in client.get(f"/api/v1/versions/{v1}/original", headers=owner).text
        )
        assert versions[0]["sha256"] != versions[1]["sha256"]
        hit = client.get(
            f"/api/v1/courses/{course}/search", headers=owner, params={"q": "窗口 机制"}
        ).json()[0]
        assert hit["version_id"] == v1 and hit["chunk_id"] == chunk["id"]
        assert (
            client.post(f"/api/v1/jobs/{job['id']}/retry", headers=owner).status_code
            == 409
        )
        for path in [
            f"/api/v1/versions/{v1}",
            f"/api/v1/versions/{v1}/chunks",
            f"/api/v1/versions/{v1}/original",
            f"/api/v1/versions/{v1}/preview",
            f"/api/v1/jobs/{job['id']}",
        ]:
            assert client.get(path, headers=stranger).status_code == 404
        assert (
            client.delete(f"/api/v1/documents/{doc['id']}", headers=owner).status_code
            == 204
        )
        for suffix in ["", "/chunks", "/original", "/preview"]:
            assert (
                client.get(f"/api/v1/versions/{v1}" + suffix, headers=owner).status_code
                == 404
            )
        assert (
            client.get(f"/api/v1/notes/{note['id']}/citations", headers=owner).json()[
                0
            ]["availability"]
            == "unavailable"
        )
        assert (
            client.post(
                f"/api/v1/notes/{note['id']}/citations",
                headers=owner,
                json={"version_id": v1, "chunk_id": chunk["id"], "quote": "窗口机制"},
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/v1/versions/{v1}/study-reports", headers=owner, json={}
            ).status_code
            == 404
        )


def test_invalid_files_scan_pdf_preview_and_retry_budget():
    from pypdf import PdfWriter

    with TestClient(app) as client:
        owner, course = context(client)
        for name, content in [
            ("fake.pdf", b"hello"),
            ("fake.docx", b"hello"),
            ("bad.md", b"\xff"),
            ("empty.md", b""),
        ]:
            assert (
                client.post(
                    f"/api/v1/courses/{course}/documents",
                    headers=owner,
                    files={"file": (name, content)},
                ).status_code
                == 422
            )
        pdf = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.write(pdf)
        job = upload(client, owner, course, pdf.getvalue(), "scan.pdf")
        drain_jobs()
        jobs = client.get(f"/api/v1/courses/{course}/jobs", headers=owner).json()
        parsed = next(row for row in jobs if row["id"] == job["id"])
        assert parsed["status"] == "FAILED" and parsed["attempt_count"] == 1
        v = client.get(f"/api/v1/courses/{course}/documents", headers=owner).json()[0][
            "latest_version_id"
        ]
        assert client.get(
            f"/api/v1/versions/{v}/preview", headers=owner
        ).content.startswith(b"%PDF")
        for attempt in [2, 3]:
            assert (
                client.post(
                    f"/api/v1/jobs/{job['id']}/retry", headers=owner
                ).status_code
                == 202
            )
            drain_jobs()
            assert (
                client.get(f"/api/v1/jobs/{job['id']}", headers=owner).json()[
                    "attempt_count"
                ]
                == attempt
            )
        assert (
            client.post(f"/api/v1/jobs/{job['id']}/retry", headers=owner).status_code
            == 409
        )


def test_expired_lease_recovery_and_idempotent_upload():
    with TestClient(app) as client:
        owner, course = context(client)
        first = upload(client, owner, course, "# 概念\n\n租约验证")
        duplicate = upload(client, owner, course, "# 概念\n\n租约验证")
        assert first["id"] == duplicate["id"]
        with SessionLocal() as db:
            job = db.get(ProcessingJob, first["id"])
            job.status = "RUNNING"
            job.attempt_count = 1
            job.lease_until = utc_now() - timedelta(seconds=1)
            job.lease_token = str(uuid4())
            db.commit()
            recover_jobs(db)
            assert db.get(ProcessingJob, first["id"]).status == "QUEUED"
        drain_jobs()
        assert (
            client.get(f"/api/v1/jobs/{first['id']}", headers=owner).json()["status"]
            == "SUCCEEDED"
        )
        with SessionLocal() as db:
            version = db.scalar(
                select(DocumentVersion).where(
                    DocumentVersion.id == first["resource_id"]
                )
            )
            assert version.parse_status == version.index_status == "SUCCEEDED"


def test_parser_offsets_docx_block_order_pptx_table(tmp_path):
    from docx import Document
    from pptx import Presentation
    from pptx.util import Inches

    raw = "# 标题\r\n\r\n  中文😀正文  \r\n\r\n## 下节\r\n末尾\n"
    source = tmp_path / "note.md"
    source.write_bytes(raw.encode())
    chunks = parse_document(source, ".md")
    normalized = raw
    assert all(
        normalized[c["start_offset"] : c["end_offset"]] == c["text"] for c in chunks
    )
    word = Document()
    word.add_paragraph("第一段")
    word.add_paragraph("")
    table = word.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "表格一"
    table.cell(0, 1).text = "表格二"
    word.add_paragraph("最后一段")
    word.save(tmp_path / "word.docx")
    blocks = parse_document(tmp_path / "word.docx", ".docx")
    assert [c["locator_value"] for c in blocks] == ["1", "3", "4"]
    assert [c["text"] for c in blocks] == ["第一段", "表格一 | 表格二", "最后一段"]
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    slide.shapes.add_textbox(
        Inches(1), Inches(1), Inches(4), Inches(1)
    ).text = "幻灯片正文"
    slide.shapes.add_table(1, 1, Inches(1), Inches(2), Inches(4), Inches(1)).table.cell(
        0, 0
    ).text = "课件表格"
    deck.save(tmp_path / "deck.pptx")
    slides = parse_document(tmp_path / "deck.pptx", ".pptx")
    assert slides[0]["locator_value"] == "1" and "课件表格" in slides[0]["text"]


def test_image_decoding_references_and_deletion():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, _ = context(client)
        url = f"/api/v1/courses/{course}/assets"
        assert (
            client.post(
                url,
                headers=owner,
                files={"file": ("fake.png", b"not an image", "image/png")},
            ).status_code
            == 422
        )
        data = io.BytesIO()
        Image.new("RGB", (10, 10)).save(data, format="PNG")
        asset = client.post(
            url,
            headers=owner,
            files={"file": ("photo.bin", data.getvalue(), "text/plain")},
        ).json()
        assert asset["mime_type"] == "image/png"
        note = client.post(
            "/api/v1/notes",
            headers=owner,
            json={
                "title": "图片",
                "course_id": course,
                "content": f"![[asset:{asset['id']}|图示]]",
            },
        ).json()
        path = f"/api/v1/assets/{asset['id']}"
        assert (
            client.get(path + "/references", headers=owner).json()[0]["id"]
            == note["id"]
        )
        assert client.get(path, headers=stranger).status_code == 404
        assert client.delete(path, headers=stranger).status_code == 404
        assert client.delete(path, headers=owner).status_code == 204
        assert client.get(path, headers=owner).status_code == 404
        assert (
            "asset:"
            in client.get(f"/api/v1/notes/{note['id']}", headers=owner).json()[
                "content"
            ]
        )
