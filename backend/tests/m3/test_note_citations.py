"""Citation edits use isolated sources; no real user files or model requests."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.workers.materials import drain_jobs
from tests.m1.test_materialhub import context, upload
from tests.m3.test_note_tags import create as note
from tests.m3.test_note_exports import create, done


def source(client, owner, course):
    job = upload(
        client, owner, course, "# 引用来源\n\n" + "内容片段" * 80, "来源资料.md"
    )
    drain_jobs()
    version = client.get(f"/api/v1/versions/{job['resource_id']}", headers=owner).json()
    chunk = client.get(
        f"/api/v1/versions/{version['id']}/chunks", headers=owner
    ).json()[0]
    return version, {
        "version_id": version["id"],
        "chunk_id": chunk["id"],
        "quote": chunk["text"][-240:],
    }


def test_create_and_append_deduplicate_with_metadata_and_preserve_revision():
    with TestClient(app) as client:
        owner, course = context(client)
        version, citation = source(client, owner, course)
        request_id = str(uuid4())
        current = note(
            client, owner, course, request_id=request_id, citations=[citation, citation]
        )
        assert (
            note(
                client,
                owner,
                course,
                request_id=request_id,
                citations=[citation, citation],
            )["id"]
            == current["id"]
        )
        path = f"/api/v1/notes/{current['id']}/citations"
        rows = client.get(path, headers=owner).json()
        assert len(rows) == 1
        assert rows[0]["document_name"] == "来源资料"
        assert rows[0]["document_id"] == version["document_id"]
        assert rows[0]["version_no"] == 1
        added = client.post(path, headers=owner, json=citation)
        assert added.status_code == 201 and added.json()["id"] == rows[0]["id"]
        assert len(client.get(path, headers=owner).json()) == 1
        saved = client.get(f"/api/v1/notes/{current['id']}", headers=owner).json()
        assert saved["revision"] == 1 and saved["content"] == current["content"]
        references = client.get(
            f"/api/v1/versions/{version['id']}/references", headers=owner
        )
        assert references.status_code == 200 and len(references.json()) == 1


def test_remove_is_owned_and_scoped_keeps_source_body_and_revokes_old_export():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, _ = context(client)
        version, citation = source(client, owner, course)
        first = note(client, owner, course, citations=[citation])
        second = note(client, owner, course, title="第二篇", citations=[citation])
        path = f"/api/v1/notes/{first['id']}/citations"
        citation_id = client.get(path, headers=owner).json()[0]["id"]
        row = done(client, owner, create(client, owner, note_ids=[first["id"]]))
        assert row["job"]["status"] == "SUCCEEDED"
        assert (
            client.delete(path + "/" + citation_id, headers=stranger).status_code == 404
        )
        assert (
            client.delete(
                f"/api/v1/notes/{second['id']}/citations/{citation_id}", headers=owner
            ).status_code
            == 404
        )
        assert client.delete(path + "/" + citation_id, headers=owner).status_code == 204
        assert client.get(path, headers=owner).json() == []
        assert client.get(f"/api/v1/notes/{first['id']}", headers=owner).json() == first
        assert (
            len(
                client.get(
                    f"/api/v1/notes/{second['id']}/citations", headers=owner
                ).json()
            )
            == 1
        )
        assert (
            client.get(
                f"/api/v1/versions/{version['id']}/original", headers=owner
            ).status_code
            == 200
        )
        references = client.get(
            f"/api/v1/versions/{version['id']}/references", headers=owner
        ).json()
        assert {entry["note_id"] for entry in references} == {second["id"]}
        assert (
            client.get(
                f"/api/v1/note-exports/{row['id']}/download", headers=owner
            ).status_code
            == 404
        )
        # Citation edits do not invalidate a concurrently edited body revision.
        assert (
            client.patch(
                f"/api/v1/notes/{first['id']}",
                headers=owner,
                json={"revision": 1, "content": "继续编辑"},
            ).status_code
            == 200
        )


def test_unavailable_citation_has_no_live_metadata_and_can_be_removed():
    with TestClient(app) as client:
        owner, course = context(client)
        version, citation = source(client, owner, course)
        current = note(client, owner, course, citations=[citation])
        path = f"/api/v1/notes/{current['id']}/citations"
        assert (
            client.delete(
                f"/api/v1/documents/{version['document_id']}", headers=owner
            ).status_code
            == 204
        )
        row = client.get(path, headers=owner).json()[0]
        assert row["availability"] == "unavailable"
        assert row["document_name"] is None and row["version_no"] is None
        assert row["quote"] == citation["quote"]
        assert client.delete(path + "/" + row["id"], headers=owner).status_code == 204


def test_append_limit_and_parallel_duplicate_requests_are_atomic():
    with TestClient(app) as client:
        owner, course = context(client)
        _, citation = source(client, owner, course)
        initial = [citation | {"quote": "内容片段" * i} for i in range(1, 50)]
        current = note(client, owner, course, citations=initial)
        path = f"/api/v1/notes/{current['id']}/citations"
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda _: client.post(path, headers=owner, json=citation), range(2)
                )
            )
        assert [result.status_code for result in results] == [201, 201]
        assert results[0].json()["id"] == results[1].json()["id"]
        assert len(client.get(path, headers=owner).json()) == 50
        blocked = client.post(
            path, headers=owner, json=citation | {"quote": "内容片段" * 50}
        )
        assert blocked.status_code == 422 and "50" in blocked.text
        assert (
            client.delete(
                path + "/" + results[0].json()["id"], headers=owner
            ).status_code
            == 204
        )
        assert (
            client.post(
                path, headers=owner, json=citation | {"quote": "内容片段" * 50}
            ).status_code
            == 201
        )


def test_invalid_foreign_or_deleted_sources_cannot_be_added():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, other_course = context(client)
        version, citation = source(client, owner, course)
        current = note(client, owner, course)
        foreign = note(client, stranger, other_course)
        path = f"/api/v1/notes/{current['id']}/citations"
        assert (
            client.post(
                path, headers=owner, json=citation | {"quote": "凭空编写"}
            ).status_code
            == 422
        )
        assert client.post(path, headers=stranger, json=citation).status_code == 404
        assert (
            client.post(
                f"/api/v1/notes/{foreign['id']}/citations",
                headers=stranger,
                json=citation,
            ).status_code
            == 404
        )
        assert (
            client.delete(
                f"/api/v1/documents/{version['document_id']}", headers=owner
            ).status_code
            == 204
        )
        assert client.post(path, headers=owner, json=citation).status_code == 404
        assert client.get(path, headers=owner).json() == []
