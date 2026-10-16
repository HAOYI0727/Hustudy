import io
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import Asset
from app.workers.materials import drain_jobs


def account(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "preview_" + uuid4().hex[:10],
            "password": "test-password-123",
        },
    )
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    course = client.post(
        "/api/v1/courses", headers=headers, json={"name": "页级资料"}
    ).json()["id"]
    return headers, course


def blank_pdf(pages=2):
    pdf = PdfWriter()
    for _ in range(pages):
        pdf.add_blank_page(width=300, height=400)
    buffer = io.BytesIO()
    pdf.write(buffer)
    return buffer.getvalue()


def import_pdf(client, owner, course, data=None, document=None):
    response = client.post(
        f"/api/v1/documents/{document}/versions"
        if document
        else f"/api/v1/courses/{course}/documents",
        headers=owner,
        files={"file": ("scan.pdf", data or blank_pdf(), "application/pdf")},
    )
    assert response.status_code == 202, response.text
    drain_jobs()
    return client.get(
        f"/api/v1/versions/{response.json()['resource_id']}", headers=owner
    ).json()


def png():
    buffer = io.BytesIO()
    Image.new("RGB", (20, 30), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def capture(client, owner, course, version, page=2):
    return client.post(
        f"/api/v1/courses/{course}/assets",
        headers=owner,
        params={"source_version_id": version, "source_page": page, "alt": "页图"},
        files={"file": ("page.png", png(), "image/png")},
    )


def test_scanned_preview_capture_source_validation_and_owner_isolation():
    with TestClient(app) as client:
        owner, course = account(client)
        stranger, other_course = account(client)
        second_course = client.post(
            "/api/v1/courses", headers=owner, json={"name": "另一个课程"}
        ).json()["id"]
        version = import_pdf(client, owner, course)
        assert (
            version["parse_status"] == "FAILED"
        )  # Capturing does not pretend OCR succeeded.
        assert version["preview_status"] == "SUCCEEDED"
        response = capture(client, owner, course, version["id"])
        assert response.status_code == 201, response.text
        asset = response.json()
        assert asset["source_page"] == 2 and asset["source_locator_type"] == "page"
        assert (
            client.get(f"/api/v1/assets/{asset['id']}", headers=owner).content == png()
        )
        info = client.get(
            f"/api/v1/assets/{asset['id']}/metadata", headers=owner
        ).json()
        assert (
            info["source_version_no"] == 1
            and info["source_document_id"] == version["document_id"]
        )
        assert info["source_availability"] == "active" and len(info["sha256"]) == 64
        assert info["created_at"].endswith(("Z", "+00:00"))
        for suffix in ("", "/metadata", "/references"):
            assert (
                client.get(
                    f"/api/v1/assets/{asset['id']}" + suffix, headers=stranger
                ).status_code
                == 404
            )
        assert capture(client, stranger, other_course, version["id"]).status_code == 404
        assert capture(client, owner, second_course, version["id"]).status_code == 404
        for page in (0, 3):
            assert (
                capture(client, owner, course, version["id"], page).status_code == 422
            )
        base = f"/api/v1/courses/{course}/assets"
        for params in (
            {"source_version_id": version["id"]},
            {"source_page": 1},
            {"alt": "x" * 501},
        ):
            assert (
                client.post(
                    base,
                    headers=owner,
                    params=params,
                    files={"file": ("page.png", png(), "image/png")},
                ).status_code
                == 422
            )
        with SessionLocal() as db:
            assert (
                len(db.scalars(select(Asset).where(Asset.course_id == course)).all())
                == 1
            )


def test_capture_keeps_old_version_and_source_deletion_revokes_image():
    with TestClient(app) as client:
        owner, course = account(client)
        version = import_pdf(client, owner, course)
        asset = capture(client, owner, course, version["id"]).json()
        note = client.post(
            "/api/v1/notes",
            headers=owner,
            json={
                "title": "页图笔记",
                "course_id": course,
                "content": f"![[asset:{asset['id']}|第二页]]",
            },
        ).json()
        assert (
            client.get(
                f"/api/v1/assets/{asset['id']}/references", headers=owner
            ).json()[0]["id"]
            == note["id"]
        )
        newer = import_pdf(client, owner, course, blank_pdf(3), version["document_id"])
        assert newer["version_no"] == 2
        client.patch(
            f"/api/v1/documents/{version['document_id']}",
            headers=owner,
            json={"name": "改名后的资料"},
        )
        info = client.get(
            f"/api/v1/assets/{asset['id']}/metadata", headers=owner
        ).json()
        assert info["source_document_name"] == "改名后的资料"
        assert (
            info["source_version_id"] == version["id"]
            and info["source_version_no"] == 1
        )
        assert info["source_page"] == 2
        assert (
            client.delete(
                f"/api/v1/documents/{version['document_id']}", headers=owner
            ).status_code
            == 204
        )
        assert (
            client.get(f"/api/v1/assets/{asset['id']}", headers=owner).status_code
            == 404
        )
        assert (
            client.get(f"/api/v1/assets/{asset['id']}/metadata", headers=owner).json()[
                "source_availability"
            ]
            == "unavailable"
        )
        assert (
            client.get(f"/api/v1/courses/{course}/assets", headers=owner).json() == []
        )
        assert (
            "asset:"
            in client.get(f"/api/v1/notes/{note['id']}", headers=owner).json()[
                "content"
            ]
        )
        assert capture(client, owner, course, version["id"]).status_code == 404


def test_external_images_stay_unlinked_and_course_delete_revokes_all_images():
    with TestClient(app) as client:
        owner, course = account(client)
        version = import_pdf(client, owner, course)
        captured = capture(client, owner, course, version["id"]).json()
        ordinary = client.post(
            f"/api/v1/courses/{course}/assets",
            headers=owner,
            files={"file": ("outside.bin", png(), "application/octet-stream")},
        ).json()
        assert (
            ordinary["mime_type"] == "image/png"
            and ordinary["source_version_id"] is None
        )
        info = client.get(
            f"/api/v1/assets/{ordinary['id']}/metadata", headers=owner
        ).json()
        assert (
            info["source_document_id"] is None
            and info["source_availability"] == "active"
        )
        assert (
            client.delete(
                f"/api/v1/courses/{course}?revision=1", headers=owner
            ).status_code
            == 204
        )
        for asset in (captured, ordinary):
            assert (
                client.get(f"/api/v1/assets/{asset['id']}", headers=owner).status_code
                == 404
            )
            assert (
                client.get(
                    f"/api/v1/assets/{asset['id']}/metadata", headers=owner
                ).json()["source_availability"]
                == "unavailable"
            )
