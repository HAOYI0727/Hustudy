from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app
from app.core.database import SessionLocal
from app.models import Asset, PastQuestion, User
from app.services import bank_pdf
from app.workers.bank_ocr import run_bank_ocr_once
from app.workers.materials import drain_jobs
from test_materialhub import context, upload

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def setup(client, name="question_bank_mixed_demo.pdf"):
    h, c = context(client)
    version = upload(client, h, c, (FIXTURES / name).read_bytes(), name="scan.pdf")[
        "resource_id"
    ]
    drain_jobs()
    return h, c, version


def enqueue(client, h, c, version, request_id=None, **kwargs):
    return client.post(
        f"/api/v1/courses/{c}/question-bank/pdf/{version}/ocr",
        headers=h,
        json={
            "request_id": request_id or str(uuid4()),
            "title": "PDF扫描识别",
            **kwargs,
        },
    )


def simple_recognize(items, layout):
    return [
        {
            "asset_id": i["asset_id"],
            "left": 0,
            "width": 1,
            "lines": [
                {
                    "text": "1. Explain transport protocols?",
                    "x": 0.1,
                    "y": 0.1,
                    "bottom": 0.2,
                    "low": False,
                }
            ],
        }
        for i in items
    ]


def test_detection_finds_scans_and_mixed_pages_without_starting_ocr():
    pure = bank_pdf.examine(FIXTURES / "question_bank_scan_demo.pdf")
    mixed = bank_pdf.examine(FIXTURES / "question_bank_mixed_demo.pdf")
    assert [p["needs_ocr"] for p in pure] == [True]
    assert [p["needs_ocr"] for p in mixed] == [True, False]
    assert "reliable transport" in mixed[1]["text"]
    with TestClient(app) as client:
        h, c, version = setup(client)
        r = client.get(f"/api/v1/courses/{c}/question-bank/pdf/{version}", headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["ocr_pages"] == [1]
        assert not run_bank_ocr_once()
        assert (
            client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()["total"]
            == 0
        )


def test_actual_pdf_renderer_and_ocr_complete_mixed_pages_without_duplicates():
    pytest.importorskip("pypdfium2")
    pytest.importorskip("rapidocr_onnxruntime")
    with TestClient(app) as client:
        h, c, version = setup(client)
        before = client.get(f"/api/v1/versions/{version}", headers=h).json()[
            "parse_status"
        ]
        r = enqueue(client, h, c, version)
        assert r.status_code == 202, r.text
        pid = r.json()["paper_id"]
        assert run_bank_ocr_once()
        jobs = client.get(
            f"/api/v1/courses/{c}/question-bank/image-jobs", headers=h
        ).json()
        assert jobs[0]["status"] == "SUCCEEDED", jobs
        rows = client.get(
            f"/api/v1/courses/{c}/question-bank?paper_id={pid}", headers=h
        ).json()["items"]
        assert len(rows) == 3, rows
        assert rows[0]["question_type"] == "single_choice" and rows[0]["answer"] == "B"
        assert rows[0]["bank_data"]["options"] == ["IP", "TCP", "ARP", "ICMP"]
        assert rows[2]["stem"] == "Explain reliable transport protocols."
        assert all(q["bank_data"]["source_version_id"] == version for q in rows)
        assert not rows[0]["bank_data"].get("illustrations")
        with SessionLocal() as db:
            images = db.query(Asset).filter_by(source_version_id=version).all()
            assert sorted(a.source_page for a in images) == [1, 2]
        assert (
            client.get(f"/api/v1/versions/{version}", headers=h).json()["parse_status"]
            == before
        )


def test_idempotency_no_duplicate_task_and_other_account_cannot_access(monkeypatch):
    monkeypatch.setattr("app.workers.bank_ocr.recognize", simple_recognize)
    with TestClient(app) as client:
        h, c, version = setup(client)
        rid = str(uuid4())
        first, second = (
            enqueue(client, h, c, version, rid),
            enqueue(client, h, c, version, rid),
        )
        assert first.status_code == 202 and first.json()["id"] == second.json()["id"]
        assert enqueue(client, h, c, version, rid, force_ocr=True).status_code == 409
        h2, c2 = context(client)
        assert (
            client.get(
                f"/api/v1/courses/{c2}/question-bank/pdf/{version}", headers=h2
            ).status_code
            == 404
        )
        assert enqueue(client, h2, c2, version).status_code == 404
        assert run_bank_ocr_once() and not run_bank_ocr_once()


def test_force_ocr_includes_text_layer_pages(monkeypatch):
    captured = []

    def recognize(items, layout):
        captured.extend(items)
        return simple_recognize(items, layout)

    monkeypatch.setattr("app.workers.bank_ocr.recognize", recognize)
    with TestClient(app) as client:
        h, c, version = setup(client)
        assert enqueue(client, h, c, version, force_ocr=True).status_code == 202
        assert run_bank_ocr_once() and len(captured) == 2


def test_source_deleted_during_recognition_blocks_late_result(monkeypatch):
    with TestClient(app) as client:
        h, c, version = setup(client)
        doc = client.get(f"/api/v1/versions/{version}", headers=h).json()["document_id"]
        r = enqueue(client, h, c, version)

        def revoke(items, layout):
            assert client.delete(f"/api/v1/documents/{doc}", headers=h).is_success
            return simple_recognize(items, layout)

        monkeypatch.setattr("app.workers.bank_ocr.recognize", revoke)
        assert run_bank_ocr_once()
        jobs = client.get(
            f"/api/v1/courses/{c}/question-bank/image-jobs", headers=h
        ).json()
        assert jobs[0]["status"] == "FAILED"
        with SessionLocal() as db:
            assert (
                not db.query(PastQuestion)
                .filter_by(paper_id=r.json()["paper_id"])
                .first()
            )


def test_pdf_budget_encryption_and_blank_detection(tmp_path):
    for mode in ["pages", "encrypted"]:
        writer = PdfWriter()
        for _ in range(21 if mode == "pages" else 1):
            writer.add_blank_page(100, 100)
        if mode == "encrypted":
            writer.encrypt("test-password")
        path = tmp_path / (mode + ".pdf")
        writer.write(path)
        with pytest.raises(ValueError):
            bank_pdf.examine(path)


def test_blank_ocr_fails_visibly_without_fake_questions(monkeypatch):
    monkeypatch.setattr(
        "app.workers.bank_ocr.recognize",
        lambda items, layout: [
            {"asset_id": i["asset_id"], "left": 0, "width": 1, "lines": []}
            for i in items
        ],
    )
    with TestClient(app) as client:
        h, c, version = setup(client, "question_bank_scan_demo.pdf")
        assert enqueue(client, h, c, version).status_code == 202
        assert run_bank_ocr_once()
        jobs = client.get(
            f"/api/v1/courses/{c}/question-bank/image-jobs", headers=h
        ).json()
        assert jobs[0]["status"] == "FAILED"


def test_pdf_jobs_and_source_page_assets_restore(monkeypatch):
    from test_account_backups import exported, restored, empty_account

    monkeypatch.setattr("app.workers.bank_ocr.recognize", simple_recognize)
    with TestClient(app) as client:
        h, c, version = setup(client)
        assert enqueue(client, h, c, version).status_code == 202
        assert run_bank_ocr_once()
        body, _ = exported(client, h)
        owner = client.get("/api/v1/auth/me", headers=h).json()["id"]
        with SessionLocal() as db:
            db.delete(db.get(User, owner))
            db.commit()
        target, _ = empty_account(client)
        result = restored(client, target, body)
        assert result["job"]["status"] == "SUCCEEDED", result
        rows = client.get(f"/api/v1/courses/{c}/question-bank", headers=target).json()[
            "items"
        ]
        assert rows and rows[0]["bank_data"]["source_version_id"] == version


def test_pdf_source_withdrawal_blocks_sampling_and_new_attempt(monkeypatch):
    monkeypatch.setattr("app.workers.bank_ocr.recognize", simple_recognize)
    with TestClient(app) as client:
        h, c, version = setup(client)
        tag = client.post(
            f"/api/v1/courses/{c}/topics",
            headers=h,
            json={"name": "网络", "aliases": []},
        ).json()["id"]
        result = enqueue(client, h, c, version, default_topic_ids=[tag])
        assert run_bank_ocr_once()
        pid = result.json()["paper_id"]
        assert (
            client.post(f"/api/v1/past-papers/{pid}/confirm", headers=h).status_code
            == 200
        )
        draw = client.post(
            f"/api/v1/courses/{c}/question-bank/draw",
            headers=h,
            json={"request_id": str(uuid4()), "topic_ids": [tag], "count": 1},
        )
        assert draw.status_code == 201, draw.text
        exam_id = draw.json()["id"]
        assert (
            client.post(f"/api/v1/exam-papers/{exam_id}/review", headers=h).status_code
            == 200
        )
        doc = client.get(f"/api/v1/versions/{version}", headers=h).json()["document_id"]
        assert client.delete(f"/api/v1/documents/{doc}", headers=h).is_success
        stats = client.get(
            f"/api/v1/courses/{c}/question-bank/statistics", headers=h
        ).json()
        assert stats["eligible_questions"] == 0
        assert (
            client.post(
                f"/api/v1/exam-papers/{exam_id}/attempts", headers=h
            ).status_code
            != 201
        )
