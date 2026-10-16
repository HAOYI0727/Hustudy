"""FR-09 discovery: all hits, immutable identity, bounded plain excerpts and scope."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.search_excerpt import excerpt
from app.workers.materials import drain_jobs
from test_materialhub import context, upload


def test_paged_search_beyond_50_and_filtered_version_identity():
    with TestClient(app) as client:
        headers, course = context(client)
        other, _ = context(client)
        result = upload(
            client,
            headers,
            course,
            "\n\n".join(
                f"# 段落{i}\n{'背景说明。' * 100}星际协议 共同命中 {i}。"
                for i in range(67)
            ),
        )
        drain_jobs()
        version = client.get(
            f"/api/v1/versions/{result['resource_id']}", headers=headers
        ).json()
        doc = version["document_id"]
        client.patch(
            f"/api/v1/documents/{doc}",
            headers=headers,
            json={"category": "协议", "tags": ["重点"]},
        )
        path = f"/api/v1/courses/{course}/search/page"
        params = {
            "q": "星际协议",
            "limit": 12,
            "category": "协议",
            "tag": "重点",
            "latest_only": True,
        }
        first = client.get(path, headers=headers, params=params).json()
        assert first["total"] == 67 and len(first["items"]) == 12
        assert (
            len(
                client.get(
                    path.removesuffix("/page"),
                    headers=headers,
                    params={"q": "星际协议"},
                ).json()
            )
            == 50
        )
        ids = []
        for offset in range(0, 72, 12):
            page = client.get(
                path, headers=headers, params={**params, "offset": offset}
            ).json()
            assert page["total"] == 67
            for hit in page["items"]:
                ids.append(hit["chunk_id"])
                assert hit["version_id"] == version["id"] and hit["document_id"] == doc
                assert "text" not in hit and len(hit["excerpt"]["text"]) <= 260
                assert hit["excerpt"]["start_offset"] > 0
                body = hit["excerpt"]["text"]
                assert any(
                    body[s["start"] : s["end"]] == "星际协议"
                    for s in hit["excerpt"]["highlights"]
                )
        assert len(ids) == len(set(ids)) == 67
        assert client.get(path, headers=headers, params=params).json() == first
        empty = client.get(
            path, headers=headers, params={**params, "offset": 1000}
        ).json()
        assert empty["items"] == [] and empty["total"] == 67
        assert (
            client.get(path, headers=headers, params={**params, "tag": "重"}).json()[
                "total"
            ]
            == 0
        )
        assert client.get(path, headers=other, params=params).status_code == 404
        for invalid in ({"limit": 101}, {"limit": 0}, {"offset": -1}, {"q": "a" * 201}):
            assert (
                client.get(
                    path, headers=headers, params={**params, **invalid}
                ).status_code
                == 422
            )
        assert (
            client.get(path, headers=headers, params={"q": " ! 😀 "}).json()["total"]
            == 0
        )
        assert (
            client.get(
                path,
                headers=headers,
                params={"q": " ".join(str(i) for i in range(101))},
            ).status_code
            == 422
        )
        # A queued new version must not silently substitute old content.
        newer = client.post(
            f"/api/v1/documents/{doc}/versions",
            headers=headers,
            files={"file": ("new.md", "# 新版\n星际协议", "text/markdown")},
        )
        assert newer.status_code == 202
        assert client.get(path, headers=headers, params=params).json()["total"] == 0
        historical = client.get(
            path, headers=headers, params={**params, "latest_only": False}
        ).json()
        assert historical["total"] == 67
        assert historical["items"][0]["version_id"] == version["id"]
        client.delete(f"/api/v1/documents/{doc}", headers=headers)
        assert (
            client.get(path, headers=headers, params={"q": "星际协议"}).json()["total"]
            == 0
        )


def test_note_read_adapter_pagination_literal_query_deleted_and_scope():
    with TestClient(app) as client:
        headers, course = context(client)
        foreign, foreign_course = context(client)
        path = f"/api/v1/courses/{course}/note-search"
        for index in range(17):
            response = client.post(
                "/api/v1/notes",
                headers=headers,
                json={
                    "course_id": course,
                    "title": f"笔记{index:02}",
                    "content": "前言😀。" * 100
                    + "中文100%_协议 <script>alert(1)</script>",
                },
            )
            assert response.status_code == 201
        client.post(
            "/api/v1/notes",
            headers=foreign,
            json={
                "course_id": foreign_course,
                "title": "不能泄露",
                "content": "中文100%_协议",
            },
        )
        client.post(
            "/api/v1/notes",
            headers=headers,
            json={"title": "全局不混入", "content": "中文100%_协议"},
        )
        params = {"q": "100%_协议", "limit": 10}
        first = client.get(path, headers=headers, params=params).json()
        second = client.get(
            path, headers=headers, params={**params, "offset": 10}
        ).json()
        assert first["total"] == second["total"] == 17
        assert len(first["items"]) == 10 and len(second["items"]) == 7
        assert len({r["id"] for r in first["items"] + second["items"]}) == 17
        assert first == client.get(path, headers=headers, params=params).json()
        for hit in first["items"]:
            assert "content" not in hit and len(hit["excerpt"]["text"]) <= 260
            assert "100%_协议" in hit["excerpt"]["text"]
        assert (
            client.get(path, headers=headers, params={"q": "%_"}).json()["total"] == 17
        )
        assert (
            client.get(path, headers=headers, params={"q": "%missing_"}).json()["total"]
            == 0
        )
        assert (
            client.get(path, headers=headers, params={"q": "   "}).json()["total"] == 0
        )
        assert client.get(path, headers=foreign, params=params).status_code == 404
        for invalid in ({"limit": 101}, {"offset": -1}):
            assert (
                client.get(
                    path, headers=headers, params={**params, **invalid}
                ).status_code
                == 422
            )
        client.delete("/api/v1/notes/" + first["items"][0]["id"], headers=headers)
        assert client.get(path, headers=headers, params=params).json()["total"] == 16
        revision = next(
            c
            for c in client.get("/api/v1/courses", headers=headers).json()
            if c["id"] == course
        )["revision"]
        client.delete(
            f"/api/v1/courses/{course}", headers=headers, params={"revision": revision}
        )
        assert client.get(path, headers=headers, params=params).status_code == 404


def test_excerpt_unicode_offsets_literal_regex_and_case():
    body = "😀𠀀" * 100 + " TCP <img src=x onerror=alert(1)> " + str(uuid4())
    result = excerpt(body, "tcp")
    assert result["start_offset"] == 141
    assert result["text"] == body[141:401]
    span = result["highlights"][0]
    assert result["text"][span["start"] : span["end"]] == "TCP"
    assert excerpt("abc.*def", ".*")["highlights"] == []
    assert excerpt("a_1 aX1", "a_1")["highlights"] == [{"start": 0, "end": 3}]


def test_note_search_count_and_page_share_snapshot_during_concurrent_deletion():
    from sqlalchemy import event, update
    from app.core.database import SessionLocal, engine
    from app.models import Note

    with TestClient(app) as client:
        headers, course = context(client)
        note = client.post(
            "/api/v1/notes",
            headers=headers,
            json={
                "course_id": course,
                "title": "快照笔记",
                "content": "并发快照关键字",
            },
        ).json()
        triggered = []

        def remove_after_count(
            connection, cursor, statement, parameters, context, many
        ):
            if not triggered and "count(*)" in statement and "FROM notes" in statement:
                triggered.append(True)
                with SessionLocal() as writer:
                    writer.execute(
                        update(Note).where(Note.id == note["id"]).values(deleted=True)
                    )
                    writer.commit()

        event.listen(engine, "after_cursor_execute", remove_after_count)
        try:
            result = client.get(
                f"/api/v1/courses/{course}/note-search",
                headers=headers,
                params={"q": "快照关键字"},
            ).json()
        finally:
            event.remove(engine, "after_cursor_execute", remove_after_count)
        assert triggered and result["total"] == 1 and len(result["items"]) == 1
        assert (
            client.get(
                f"/api/v1/courses/{course}/note-search",
                headers=headers,
                params={"q": "快照关键字"},
            ).json()["total"]
            == 0
        )
