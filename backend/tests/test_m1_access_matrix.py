"""TC-23: stale M1 identities cannot bypass owner or course retirement checks."""

from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.workers.materials import drain_jobs
from test_materialhub import context
from test_preview_assets import png


def test_material_resource_access_and_mutations_cross_user_then_course_retired():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, foreign_course = context(client)
        source = Path(__file__).resolve().parents[2] / "fixtures" / "preview_demo.pdf"
        queued = client.post(
            f"/api/v1/courses/{course}/documents",
            headers=owner,
            files={"file": ("source.pdf", source.read_bytes(), "application/pdf")},
        ).json()
        drain_jobs()
        version_id = queued["resource_id"]
        version = client.get(f"/api/v1/versions/{version_id}", headers=owner).json()
        doc = version["document_id"]
        original_name = client.get(f"/api/v1/documents/{doc}", headers=owner).json()[
            "name"
        ]
        asset = client.post(
            f"/api/v1/courses/{course}/assets",
            headers=owner,
            params={"source_version_id": version_id, "source_page": 1},
            files={"file": ("source.png", png(), "image/png")},
        ).json()
        transcript = client.post(
            f"/api/v1/versions/{version_id}/transcripts",
            headers=owner,
            json={"page": 1, "text": "自制人工转录。"},
        ).json()
        confirmed = client.post(
            f"/api/v1/transcripts/{transcript['id']}/confirm",
            headers=owner,
            json={"revision": transcript["revision"]},
        )
        assert confirmed.status_code == 200
        archive = client.post(
            f"/api/v1/courses/{course}/material-exports",
            headers=owner,
            json={"request_id": str(uuid4())},
        ).json()
        drain_jobs()
        paths = [
            f"/documents/{doc}",
            f"/documents/{doc}/versions",
            f"/versions/{version_id}",
            f"/versions/{version_id}/chunks",
            f"/versions/{version_id}/original",
            f"/versions/{version_id}/preview",
            f"/versions/{version_id}/references",
            f"/versions/{version_id}/transcripts",
            f"/assets/{asset['id']}",
            f"/assets/{asset['id']}/metadata",
            f"/assets/{asset['id']}/references",
            f"/jobs/{queued['id']}",
            f"/courses/{course}/documents/page",
            f"/courses/{course}/jobs/page",
            f"/courses/{course}/assets/page",
            f"/courses/{course}/search/page?q=Hustudy",
            f"/courses/{course}/note-search?q=Hustudy",
            f"/courses/{course}/material-exports",
            f"/material-exports/{archive['id']}/download",
        ]
        for path in paths:
            response = client.get("/api/v1" + path, headers=stranger)
            assert response.status_code == 404, (path, response.text)
            assert response.json()["error"]["code"] == "NOT_FOUND"
        actions = [
            ("delete", f"/documents/{doc}", {}),
            ("patch", f"/documents/{doc}", {"json": {"name": "不可改名"}}),
            (
                "post",
                f"/versions/{version_id}/reindex",
                {"json": {"request_id": str(uuid4())}},
            ),
            ("post", f"/versions/{version_id}/preview-jobs", {}),
            ("post", f"/jobs/{queued['id']}/cancel", {}),
            ("post", f"/jobs/{queued['id']}/retry", {}),
            ("delete", f"/assets/{asset['id']}", {}),
            (
                "patch",
                f"/transcripts/{transcript['id']}",
                {"json": {"revision": 1, "text": "不可覆盖"}},
            ),
            (
                "post",
                f"/transcripts/{transcript['id']}/withdraw",
                {"json": {"revision": 2}},
            ),
            (
                "post",
                f"/documents/{doc}/versions",
                {"files": {"file": ("new.md", b"# new")}},
            ),
        ]
        for method, path, kwargs in actions:
            response = getattr(client, method)(
                "/api/v1" + path, headers=stranger, **kwargs
            )
            assert response.status_code == 404, (method, path, response.text)
        # No attempted mutation changed original labels, sources or bytes.
        assert (
            client.get(f"/api/v1/documents/{doc}", headers=owner).json()["name"]
            == original_name
        )
        assert (
            client.get(f"/api/v1/versions/{version_id}/original", headers=owner).content
            == source.read_bytes()
        )
        assert (
            client.delete(
                f"/api/v1/courses/{course}?revision=1", headers=owner
            ).status_code
            == 204
        )
        retained_metadata = {
            f"/assets/{asset['id']}/metadata",
            f"/assets/{asset['id']}/references",
        }
        for path in paths:
            if path in retained_metadata:
                continue  # Deliberate unavailable reference metadata, never file bytes.
            response = client.get("/api/v1" + path, headers=owner)
            assert response.status_code == 404, (path, response.text)
        assert (
            client.get(
                f"/api/v1/courses/{foreign_course}/documents/page", headers=stranger
            ).status_code
            == 200
        )
