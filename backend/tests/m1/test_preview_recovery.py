"""Preview recovery must not reset task budgets, source identities or ownership."""

import io
from pathlib import Path
import subprocess
from uuid import uuid4

from fastapi.testclient import TestClient
from pptx import Presentation
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.models import DocumentVersion, ProcessingJob
from app.services import preview_runtime
from app.workers import materials
from tests.m1.test_materialhub import context, upload
from tests.m1.test_preview_assets import blank_pdf


def pptx():
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    from pptx.util import Inches

    slide.shapes.add_textbox(
        Inches(1), Inches(1), Inches(4), Inches(1)
    ).text = "Preview source"
    data = io.BytesIO()
    deck.save(data)
    return data.getvalue()


def test_capability_is_authenticated_and_never_exposes_configured_path(
    monkeypatch, tmp_path
):
    with TestClient(app) as client:
        headers, _ = context(client)
        path = "/api/v1/material-capabilities"
        assert client.get(path).status_code == 401
        data = client.get(path, headers=headers).json()
        assert data["native_pdf"] and not data["office_available"]
        assert data["office_status"] == "configured_unavailable"
        assert "/nonexistent" not in str(data)
        executable = tmp_path / "office with spaces"
        executable.write_text("fixture")
        executable.chmod(0o700)
        monkeypatch.setattr(get_settings(), "libreoffice_path", str(executable))
        assert preview_runtime.office_executable() == str(executable)
        data = client.get(path, headers=headers).json()
        assert data["office_available"] and str(executable) not in str(data)
        executable.chmod(0o600)
        assert not client.get(path, headers=headers).json()["office_available"]


def test_disabled_production_compatibility_keeps_native_formats_available(monkeypatch):
    from app.core import config

    settings = config.Settings(_env_file=None, env="production")
    assert settings.office_compatibility_enabled is False
    from app.services import preview_runtime
    monkeypatch.setattr(preview_runtime, "get_settings", lambda: settings)
    data = preview_runtime.preview_capabilities()
    assert data["native_pdf"] is True
    assert data["office_available"] is False
    assert data["office_status"] == "disabled_by_config"


def test_native_formats_do_not_enqueue_compatibility_preview_by_default(monkeypatch):
    with TestClient(app) as client:
        headers, course = context(client)
        office = upload(client, headers, course, pptx(), "native-default.pptx")
        materials.drain_jobs()
        office_version = client.get(
            f"/api/v1/versions/{office['resource_id']}", headers=headers
        ).json()
        assert office_version["parse_status"] == office_version["index_status"] == "SUCCEEDED"
        assert office_version["preview_status"] == "TEXT_ONLY"
        with SessionLocal() as db:
            assert not db.scalar(
                select(ProcessingJob.id).where(
                    ProcessingJob.resource_id == office["resource_id"],
                    ProcessingJob.type == "PREVIEW",
                )
            )
        monkeypatch.setattr(preview_runtime, "office_executable", lambda: "/fake/office")
        requested = client.post(
            f"/api/v1/versions/{office['resource_id']}/preview-jobs", headers=headers
        )
        assert requested.status_code == 202

        pdf = upload(client, headers, course, blank_pdf(), "native-default.pdf")
        pdf_version = client.get(
            f"/api/v1/versions/{pdf['resource_id']}", headers=headers
        ).json()
        assert pdf_version["preview_status"] == "SUCCEEDED"
        assert client.get(
            f"/api/v1/versions/{pdf['resource_id']}/preview", headers=headers
        ).status_code == 200


def test_missing_converter_recovery_retains_job_budget_and_citations(monkeypatch):
    with TestClient(app) as client:
        headers, course = context(client)
        stranger, _ = context(client)
        original = upload(client, headers, course, pptx(), "slides.pptx")
        materials.drain_jobs()
        version_id = original["resource_id"]
        path = f"/api/v1/versions/{version_id}/preview-jobs"
        before = client.get(
            f"/api/v1/versions/{version_id}/chunks", headers=headers
        ).json()
        assert before
        assert client.post(path, headers=stranger).status_code == 404
        assert client.post(path, headers=headers).status_code == 409
        monkeypatch.setattr(
            preview_runtime, "office_executable", lambda: "/fake/office"
        )
        first = client.post(path, headers=headers)
        assert first.status_code == 202
        job_id = first.json()["id"]
        duplicate = client.post(path, headers=headers)
        assert duplicate.status_code == 202 and duplicate.json()["id"] == job_id

        def valid_preview(source):
            target = source.with_name(source.stem + ".preview-" + uuid4().hex + ".pdf")
            target.write_bytes(blank_pdf(1))
            return str(target)

        monkeypatch.setattr(materials, "preview_file", valid_preview)
        materials.drain_jobs()
        # Task bookkeeping verified independently from real conversion tests.
        assert client.post(path, headers=headers).status_code == 409
        assert (
            client.get(f"/api/v1/versions/{version_id}/chunks", headers=headers).json()
            == before
        )
        with SessionLocal() as db:
            preview = db.get(ProcessingJob, job_id)
            preview.status = "FAILED"
            preview.attempt_count = preview.max_attempts
            db.get(DocumentVersion, version_id).preview_status = "FAILED"
            db.commit()
        assert client.post(path, headers=headers).status_code == 409
        client.delete(
            f"/api/v1/documents/{client.get(f'/api/v1/versions/{version_id}', headers=headers).json()['document_id']}",
            headers=headers,
        )
        assert client.post(path, headers=headers).status_code == 404


def test_native_pdf_recovery_works_without_office_and_text_format_is_rejected():
    with TestClient(app) as client:
        headers, course = context(client)
        pdf = upload(client, headers, course, blank_pdf(), "scan.pdf")
        # PDF is already a directly readable page source; no conversion task is needed.
        path = f"/api/v1/versions/{pdf['resource_id']}/preview-jobs"
        first = client.post(path, headers=headers)
        assert first.status_code == 409
        assert (
            client.get(
                f"/api/v1/versions/{pdf['resource_id']}/preview", headers=headers
            ).content
            == blank_pdf()
        )
        markdown = upload(client, headers, course, "# Text")
        assert (
            client.post(
                f"/api/v1/versions/{markdown['resource_id']}/preview-jobs",
                headers=headers,
            ).status_code
            == 422
        )


@pytest.mark.parametrize("failure", ["timeout", "exit", "empty", "invalid"])
def test_conversion_errors_are_safe_and_do_not_publish_output(monkeypatch, failure):
    root = Path(get_settings().storage_root) / uuid4().hex
    root.mkdir()
    source = root / "source.pptx"
    source.write_bytes(b"self-authored test")
    monkeypatch.setattr(preview_runtime, "office_executable", lambda: "/fake/office")

    def convert(args, **kwargs):
        assert kwargs["timeout"] == 600 and kwargs["check"]
        assert Path(kwargs["cwd"]) == Path(args[args.index("--outdir") + 1])
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert Path(args[-1]).is_absolute()
        assert "--headless" in args and "--norestore" in args
        assert any(value.startswith("-env:UserInstallation=file:") for value in args)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 60, stderr=b"private-local-path")
        if failure == "exit":
            raise subprocess.CalledProcessError(1, args, stderr=b"private-local-path")
        folder = Path(args[args.index("--outdir") + 1])
        (folder / "source.pdf").write_bytes(b"" if failure == "empty" else b"not a pdf")

    monkeypatch.setattr(materials.subprocess, "run", convert)
    with pytest.raises(ValueError) as error:
        materials.preview_file(source)
    assert "private-local-path" not in str(error.value)
    assert (
        not list(root.glob("*.preview-*.pdf"))
        and source.read_bytes() == b"self-authored test"
    )


def test_valid_converted_pdf_is_published_atomically(monkeypatch):
    root = Path(get_settings().storage_root) / uuid4().hex
    root.mkdir()
    source = root / "source.docx"
    source.write_bytes(b"source")
    monkeypatch.setattr(preview_runtime, "office_executable", lambda: "/fake/office")

    def convert(args, **kwargs):
        (Path(args[args.index("--outdir") + 1]) / "source.pdf").write_bytes(blank_pdf())

    monkeypatch.setattr(materials.subprocess, "run", convert)
    output = Path(materials.preview_file(source))
    assert output.parent == root and output.read_bytes() == blank_pdf()
    assert source.read_bytes() == b"source"


def test_pptx_hidden_slide_mapping_rejects_old_cache_and_preserves_existing_images(
    monkeypatch,
):
    from app.models import Asset

    with TestClient(app) as client:
        headers, course = context(client)
        uploaded = upload(client, headers, course, pptx(), "source.pptx")
        materials.drain_jobs()
        version_id = uploaded["resource_id"]
        monkeypatch.setattr(
            preview_runtime, "office_executable", lambda: "/fake/office"
        )
        with SessionLocal() as db:
            version = db.get(DocumentVersion, version_id)
            bad = Path(version.source_path).with_suffix(".bad-preview.pdf")
            bad.write_bytes(
                blank_pdf(2)
            )  # One original slide versus two preview pages.
            version.preview_status = "SUCCEEDED"
            version.preview_path = str(bad)
            db.commit()
        assert (
            client.get(
                f"/api/v1/versions/{version_id}/preview", headers=headers
            ).status_code
            == 409
        )
        response = client.post(
            f"/api/v1/courses/{course}/assets",
            headers=headers,
            params={"source_version_id": version_id, "source_page": 1},
            files={"file": ("image.png", b"invalid")},
        )
        assert response.status_code == 409
        response = client.post(
            f"/api/v1/versions/{version_id}/preview-jobs", headers=headers
        )
        assert response.status_code == 202
        job_id = response.json()["id"]
        client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
        with SessionLocal() as db:
            version = db.get(DocumentVersion, version_id)
            version.preview_status = "SUCCEEDED"
            db.add(
                Asset(
                    user_id=version.user_id,
                    course_id=course,
                    source_version_id=version_id,
                    source_page=1,
                    source_locator_type="slide",
                    original_filename="old.png",
                    mime_type="image/png",
                    size_bytes=1,
                    sha256="0" * 64,
                    storage_path="unused",
                    alt="old page",
                )
            )
            db.commit()
        assert (
            client.post(
                f"/api/v1/versions/{version_id}/preview-jobs", headers=headers
            ).status_code
            == 409
        )
