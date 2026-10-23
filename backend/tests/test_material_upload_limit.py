from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def test_30_mib_original_and_new_version_boundary_and_rejection_has_no_partial_job():
    with TestClient(create_app()) as client:
        auth = client.post(
            "/api/v1/auth/register",
            json={
                "username": "limit_" + uuid4().hex,
                "password": "isolated-password-2026",
            },
        ).json()
        headers = {"Authorization": "Bearer " + auth["access_token"]}
        course = client.post(
            "/api/v1/courses", headers=headers, json={"name": "30MiB boundary"}
        ).json()["id"]
        body = b"# Source\n" + b"x" * (30 * 1024 * 1024 - 9)
        assert len(body) == 31457280
        path = f"/api/v1/courses/{course}/documents"
        document_id = None
        try:
            for number in (1, 2):
                if number == 2:
                    body = body[:-1] + b"y"
                    path = f"/api/v1/documents/{document_id}/versions"
                accepted = client.post(
                    path,
                    headers=headers,
                    files={"file": ("boundary.md", body, "text/markdown")},
                )
                assert accepted.status_code == 202
                version = client.get(
                    f"/api/v1/versions/{accepted.json()['resource_id']}",
                    headers=headers,
                ).json()
                document_id = version["document_id"]
                assert version["version_no"] == number
                rejected = client.post(
                    path,
                    headers=headers,
                    files={"file": ("too-large.md", body + b"z", "text/markdown")},
                )
                assert (
                    rejected.status_code == 422
                    and "30 MiB" in rejected.json()["error"]["message"]
                )
                jobs = client.get(
                    f"/api/v1/courses/{course}/jobs/page", headers=headers
                ).json()
                assert jobs["total"] == number
            versions = client.get(
                f"/api/v1/documents/{document_id}/versions", headers=headers
            ).json()
            assert [v["version_no"] for v in versions] == [2, 1]
            documents = client.get(
                f"/api/v1/courses/{course}/documents", headers=headers
            ).json()
            assert len(documents) == 1 and documents[0]["size_bytes"] == 31457280
        finally:
            # Leave no giant pending parser task for unrelated tests in this temporary DB.
            if document_id:
                assert (
                    client.delete(
                        f"/api/v1/documents/{document_id}", headers=headers
                    ).status_code
                    == 204
                )
