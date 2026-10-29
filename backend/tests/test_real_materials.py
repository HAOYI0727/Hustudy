"""Functional-programming material shapes, durable steps and no live model calls."""

import json
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import AIResult, RemoteQuery, ProcessingJob
from app.core.database import SessionLocal
from app.ai.providers import checked_evidence
from app.schemas.remote_ai import Evidence
from app.ai.question_drafts import normalized_option, normalized_stem
from app.workers.ai_queries import run_ai_once
from app.services.ai_material_scope import report_batches
from app.services.report_batches import CHECKPOINT_VERSION
from test_remote_ai import adapter, envelope, configured as configured  # noqa: F401
from test_material_organization import setup_course, import_document
from test_study_reports import model_report


def long_report(client):
    owner, course = setup_course(client)
    body = "\n\n".join(
        f"# Slide {i}\n\n"
        + ("fun pair f (x,y) = (f x, f y);\n函数可以作为参数。\n" * 20)
        for i in range(18)
    )
    _, version = import_document(client, owner, course, body)
    response = client.post(
        f"/api/v1/courses/{course}/study-reports/preview",
        headers=owner,
        json={"version_ids": [version]},
    )
    assert response.status_code == 201, response.text
    return owner, course, version, body, response.json()


@pytest.mark.usefixtures("configured")
def test_complete_scope_steps_failure_resume_and_backup_safe_checkpoints(monkeypatch):
    with TestClient(app) as client:
        owner, course, version, body, pending = long_report(client)
        chunks = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()
        assert len(pending["sources"]) > 6
        assert sum(len(s["text"]) for s in pending["sources"]) == sum(
            len(c["text"]) for c in chunks
        )
        assert pending["report_scope"]["coverage"]["truncated"] is False
        batches = report_batches(pending["sources"])
        assert len(batches) > 1 and all(
            sum(len(s["text"]) for s in b) <= 8000 for b in batches
        )
        base = f"/api/v1/remote-queries/{pending['id']}"
        calls, fail = [], [True]

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            calls.append(sent)
            if len(calls) == 2 and fail[0]:
                return httpx.Response(429, json={"error": {"code": "1305"}})
            report = model_report(sent["sources"][0])
            # All sections choose server excerpts instead of copying any text.
            evidence = [{"excerpt_id": sent["sources"][0]["excerpts"][0]["excerpt_id"]}]
            report["report"]["evidence"] = evidence
            for item in (
                report["report"]["topics"]
                + report["report"]["examples"]
                + report["report"]["self_checks"]
            ):
                item["evidence"] = evidence
            return httpx.Response(200, json=envelope(json.dumps(report)))

        adapter(monkeypatch, handler)
        assert not calls
        assert (
            client.post(
                base + "/confirm", headers=owner, json={"confirm_remote_send": True}
            ).status_code
            == 202
        )
        assert run_ai_once()
        first = client.get(base, headers=owner).json()
        assert first["result"]["result"]["partial"]
        assert len(first["result"]["result"]["study_report_sections"]) == 1
        assert (
            first["batch_progress"]["completed"] == 1
            and first["job"]["status"] == "QUEUED"
        )
        assert run_ai_once()
        failed = client.get(base, headers=owner).json()
        assert failed["job"]["status"] == "FAILED"
        assert failed["batch_progress"]["completed"] == 1
        assert failed["result"]["result"]["partial"]
        assert len(failed["result"]["result"]["study_report_sections"]) == 1
        assert not run_ai_once()  # no automatic retry of failed request
        assert (
            client.post(
                base + "/resume", headers=owner, json={"confirm_remote_send": False}
            ).status_code
            == 422
        )
        fail[0] = False
        assert (
            client.post(
                base + "/resume", headers=owner, json={"confirm_remote_send": True}
            ).status_code
            == 202
        )
        for _ in range(len(batches)):
            if not run_ai_once():
                break
        completed = client.get(base, headers=owner).json()
        assert completed["job"]["status"] == "SUCCEEDED"
        assert completed["batch_progress"]["completed"] == len(batches)
        assert len(calls) == len(batches) + 1
        assert calls[0]["sources"] != calls[1]["sources"]
        assert calls[1]["sources"] == calls[2]["sources"]
        result = completed["result"]
        assert len(result["result"]["study_report_sections"]) == len(batches)
        assert all(
            r["result"].get("result_kind") != "report_checkpoint"
            for r in client.get(
                f"/api/v1/courses/{course}/study-reports", headers=owner
            ).json()
        )
        history = client.get(
            f"/api/v1/courses/{course}/study-reports", headers=owner
        ).json()
        assert len(history) == 2  # failure snapshot and final result, no internal steps
        with SessionLocal() as db:
            assert len(
                list(
                    db.scalars(
                        select(AIResult).where(
                            AIResult.course_id == course,
                            AIResult.prompt_version == CHECKPOINT_VERSION,
                        )
                    )
                )
            ) == len(batches)
        assert (
            client.post(
                base + "/resume", headers=owner, json={"confirm_remote_send": True}
            ).status_code
            == 409
        )


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("action", ["cancel", "delete", "expired"])
def test_running_step_cannot_save_after_cancel_source_loss_or_lease_expiry(
    monkeypatch, action
):
    from datetime import timedelta
    from app.models.base import utc_now

    with TestClient(app) as client:
        owner, course, version, body, pending = long_report(client)
        base = f"/api/v1/remote-queries/{pending['id']}"

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            if action == "cancel":
                client.post(base + "/cancel", headers=owner)
            elif action == "delete":
                document = pending["sources"][0]["document_id"]
                client.delete(f"/api/v1/documents/{document}", headers=owner)
            else:
                with SessionLocal() as db:
                    row = db.get(RemoteQuery, pending["id"])
                    db.get(ProcessingJob, row.job_id).lease_until = (
                        utc_now() - timedelta(seconds=1)
                    )
                    db.commit()
            return httpx.Response(
                200, json=envelope(json.dumps(model_report(sent["sources"][0])))
            )

        adapter(monkeypatch, handler)
        client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        )
        assert run_ai_once()
        value = client.get(base, headers=owner).json()
        assert value["result"] is None
        assert value["batch_progress"]["completed"] == 0


def test_operators_case_and_indentation_not_collapsed_and_long_slice_offsets():
    assert normalized_option("x+1") != normalized_option("x-1")
    assert normalized_option("f(x)") != normalized_option("f[x]")
    assert normalized_option("True") != normalized_option("true")
    assert normalized_option("  a\n b") != normalized_option("  a\nb")
    assert normalized_stem("计算x+1") != normalized_stem("计算x-1")
    from test_remote_ai import source

    item = source()
    first = {**item, "text": "前段", "chunk_start": 0}
    second = {**item, "text": "后段", "chunk_start": 2000}
    (citation,) = checked_evidence(
        [Evidence(source_id=item["source_id"], quote="后段")], [first, second]
    )
    assert citation["start_offset"] == 2000 and citation["end_offset"] == 2002




@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("format", ["pdf", "pptx"])
def test_pdf_pptx_functional_code_is_parsed_and_all_pages_reach_preview(format):
    from io import BytesIO
    from app.workers.materials import drain_jobs

    stream = BytesIO()
    if format == "pptx":
        from pptx import Presentation

        document = Presentation()
        for i in range(9):
            slide = document.slides.add_slide(document.slide_layouts[1])
            slide.shapes.title.text = f"Higher order functions {i}"
            slide.placeholders[
                1
            ].text = "fun pair f (x,y) = (f x, f y)\nx+1\nx-1\nfn: int -> int"
        document.save(stream)
        mime = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    else:
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

        document = PdfWriter()
        font = document._add_object(
            DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }
            )
        )
        for i in range(9):
            page = document.add_blank_page(width=600, height=800)
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
            )
            content = DecodedStreamObject()
            content.set_data(
                f"BT /F1 14 Tf 30 700 Td (Higher order functions {i}) Tj 0 -24 Td (x+1 and x-1) Tj ET".encode()
            )
            page[NameObject("/Contents")] = document._add_object(content)
        document.write(stream)
        mime = "application/pdf"
    with TestClient(app) as client:
        owner, course = setup_course(client)
        response = client.post(
            f"/api/v1/courses/{course}/documents",
            headers=owner,
            files={"file": (f"functional.{format}", stream.getvalue(), mime)},
        )
        assert response.status_code == 202, response.text
        drain_jobs()
        version = response.json()["resource_id"]
        chunks = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()
        assert len(chunks) == 9
        preview = client.post(
            f"/api/v1/courses/{course}/study-reports/preview",
            headers=owner,
            json={"version_ids": [version]},
        )
        assert preview.status_code == 201, preview.text
        body = preview.json()
        assert (
            len(body["sources"]) == 9
            and not body["report_scope"]["coverage"]["truncated"]
        )
        assert all("x+1" in s["text"] and "x-1" in s["text"] for s in body["sources"])


@pytest.mark.usefixtures("configured")
def test_resume_rejects_other_account_config_change_and_removed_source(monkeypatch):

    with TestClient(app) as client:
        owner, course, version, body, pending = long_report(client)
        adapter(
            monkeypatch, lambda _: httpx.Response(429, json={"error": {"code": "1305"}})
        )
        base = f"/api/v1/remote-queries/{pending['id']}"
        consent = {"confirm_remote_send": True}
        client.post(base + "/confirm", headers=owner, json=consent)
        assert run_ai_once()
        other, _ = setup_course(client)
        assert (
            client.post(base + "/resume", headers=other, json=consent).status_code
            == 404
        )
        from ai_account_test_support import change_model

        change_model(client, owner, "glm-4.7-flash")
        assert (
            client.post(base + "/resume", headers=owner, json=consent).status_code
            == 409
        )
        change_model(client, owner, "glm-5.3-flash")
        client.delete(
            f"/api/v1/documents/{pending['sources'][0]['document_id']}", headers=owner
        )
        assert (
            client.post(base + "/resume", headers=owner, json=consent).status_code
            == 404
        )


@pytest.mark.usefixtures("configured")
def test_older_prompt_results_remain_visible_after_upgrade():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        user_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        with SessionLocal() as db:
            for version in [
                "zhipu-study-report-v1",
                "zhipu-study-report-v3",
                "zhipu-question-drafts-v3",
                "zhipu-grounded-qa-v1",
            ]:
                db.add(
                    AIResult(
                        user_id=user_id,
                        course_id=course,
                        query="历史结果",
                        status="insufficient_evidence",
                        model_mode="real",
                        prompt_version=version,
                        result_json=json.dumps(
                            {"message": "旧记录仍可读", "citations": []}
                        ),
                    )
                )
            db.commit()
        assert (
            len(
                client.get(
                    f"/api/v1/courses/{course}/study-reports", headers=owner
                ).json()
            )
            == 2
        )
        assert (
            len(
                client.get(
                    f"/api/v1/courses/{course}/question-drafts", headers=owner
                ).json()
            )
            == 1
        )
        assert (
            len(
                client.get(f"/api/v1/courses/{course}/ai-results", headers=owner).json()
            )
            == 1
        )
