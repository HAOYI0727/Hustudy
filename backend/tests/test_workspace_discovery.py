"""Navigation must resolve a search hit by identity, with course/user isolation."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.workers.materials import drain_jobs


def test_search_identity_course_scope_and_deleted_results():
    with TestClient(app) as client:

        def register():
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "find_" + uuid4().hex[:10],
                    "password": "test-password-123",
                },
            )
            assert response.status_code == 201
            return {"Authorization": "Bearer " + response.json()["access_token"]}

        owner, stranger = register(), register()
        courses = [
            client.post("/api/v1/courses", headers=owner, json={"name": name}).json()[
                "id"
            ]
            for name in ["网络", "操作系统"]
        ]
        for course_id in courses:
            uploaded = client.post(
                f"/api/v1/courses/{course_id}/documents",
                headers=owner,
                files={
                    "file": (
                        "lesson.md",
                        "# 共同术语\n\n课程内查找验证。",
                        "text/markdown",
                    )
                },
            )
            assert uploaded.status_code == 202
        drain_jobs()
        path = f"/api/v1/courses/{courses[0]}/search"
        hits = client.get(path, headers=owner, params={"q": "共同术语"}).json()
        assert len(hits) == 1
        hit = hits[0]
        document = client.get(
            f"/api/v1/documents/{hit['document_id']}", headers=owner
        ).json()
        assert document["course_id"] == courses[0]
        chunks_path = f"/api/v1/versions/{hit['version_id']}/chunks"
        chunks = client.get(chunks_path, headers=owner).json()
        chunk = next(row for row in chunks if row["id"] == hit["chunk_id"])
        assert chunk["text"] == hit["text"]
        assert chunk["locator_value"] == hit["locator_value"]
        assert (
            client.get(path, headers=stranger, params={"q": "共同术语"}).status_code
            == 404
        )
        assert client.get(chunks_path, headers=stranger).status_code == 404
        client.delete(f"/api/v1/documents/{hit['document_id']}", headers=owner)
        assert client.get(path, headers=owner, params={"q": "共同术语"}).json() == []
