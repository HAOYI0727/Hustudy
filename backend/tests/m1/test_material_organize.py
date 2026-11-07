from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import event, select

from app.core.database import SessionLocal, engine
from app.main import app
from app.models import Document, DocumentVersion, DocumentChunk, ProcessingJob
from app.workers.materials import drain_jobs
from tests.m1.test_materialhub import context, upload

BASE = "/api/v1"


def documents(client, headers, course, count=2):
    for index in range(count):
        upload(client, headers, course, f"# 课程{index}\n\n批量整理不改变原文{index}。")
    drain_jobs()
    return client.get(f"{BASE}/courses/{course}/documents", headers=headers).json()


def payload(rows, **changes):
    return {
        "items": [
            {"id": row["id"], "expected_updated_at": row["updated_at"]} for row in rows
        ],
        **changes,
    }


def metadata(client, headers, id):
    return client.get(f"{BASE}/documents/{id}", headers=headers).json()


def test_atomic_organize_preserves_versions_quotes_and_jobs():
    with TestClient(app) as client:
        headers, course = context(client)
        rows = documents(client, headers, course)
        version = rows[0]["latest_version_id"]
        chunk = client.get(f"{BASE}/versions/{version}/chunks", headers=headers).json()[
            0
        ]
        note = client.post(
            f"{BASE}/notes",
            headers=headers,
            json={
                "course_id": course,
                "title": "核对来源",
                "citations": [
                    {
                        "version_id": version,
                        "chunk_id": chunk["id"],
                        "quote": chunk["text"],
                    }
                ],
            },
        ).json()
        before_sources = client.get(
            f"{BASE}/notes/{note['id']}/citations", headers=headers
        ).json()
        with SessionLocal() as db:
            versions = [
                (v.id, v.sha256, v.version_no)
                for v in db.scalars(
                    select(DocumentVersion).where(
                        DocumentVersion.document_id.in_([r["id"] for r in rows])
                    )
                )
            ]
            chunk_ids = db.scalars(
                select(DocumentChunk.id).where(DocumentChunk.version_id == version)
            ).all()
            jobs = db.scalars(
                select(ProcessingJob.id).where(ProcessingJob.resource_id == version)
            ).all()
        result = client.post(
            f"{BASE}/courses/{course}/documents/organize",
            headers=headers,
            json=payload(
                rows, category="期末", tags_mode="add", tags=["重点", " 重点 ", "复习"]
            ),
        )
        assert result.status_code == 200, result.text
        assert result.json()["changed"] == 2
        assert [r["id"] for r in result.json()["items"]] == [r["id"] for r in rows]
        for row in result.json()["items"]:
            assert row["category"] == "期末" and row["tags"] == ["重点", "复习"]
            assert set(row) == {
                "id",
                "course_id",
                "name",
                "category",
                "tags",
                "updated_at",
            }
        assert (
            client.get(f"{BASE}/notes/{note['id']}/citations", headers=headers).json()
            == before_sources
        )
        with SessionLocal() as db:
            assert [
                (v.id, v.sha256, v.version_no)
                for v in db.scalars(
                    select(DocumentVersion).where(
                        DocumentVersion.document_id.in_([r["id"] for r in rows])
                    )
                )
            ] == versions
            assert (
                db.scalars(
                    select(DocumentChunk.id).where(DocumentChunk.version_id == version)
                ).all()
                == chunk_ids
            )
            assert (
                db.scalars(
                    select(ProcessingJob.id).where(ProcessingJob.resource_id == version)
                ).all()
                == jobs
            )


def test_stale_selection_rolls_back_whole_batch_and_single_patch_is_guarded():
    with TestClient(app) as client:
        headers, course = context(client)
        rows = documents(client, headers, course)
        stale = deepcopy(rows)
        current = client.patch(
            f"{BASE}/documents/{rows[1]['id']}",
            headers=headers,
            json={"expected_updated_at": rows[1]["updated_at"], "name": "其他窗口改名"},
        ).json()
        response = client.post(
            f"{BASE}/courses/{course}/documents/organize",
            headers=headers,
            json=payload(stale, category="不能部分写入"),
        )
        assert response.status_code == 409
        assert (
            response.json()["error"]["details"]["conflicts"][0]["name"]
            == "其他窗口改名"
        )
        assert metadata(client, headers, rows[0]["id"]) == rows[0]
        assert metadata(client, headers, rows[1]["id"]) == current
        response = client.patch(
            f"{BASE}/documents/{rows[1]['id']}",
            headers=headers,
            json={"expected_updated_at": rows[1]["updated_at"], "category": "过期输入"},
        )
        assert response.status_code == 409
        assert (
            response.json()["error"]["details"]["server_document"]["updated_at"]
            == current["updated_at"]
        )
        assert (
            client.patch(
                f"{BASE}/documents/{rows[1]['id']}",
                headers=headers,
                json={"name": "兼容旧调用"},
            ).status_code
            == 200
        )


def test_tag_budget_and_operation_modes_are_atomic_and_noop_keeps_snapshot():
    with TestClient(app) as client:
        headers, course = context(client)
        rows = documents(client, headers, course)
        second = client.patch(
            f"{BASE}/documents/{rows[1]['id']}",
            headers=headers,
            json={"tags": [str(i) for i in range(12)]},
        ).json()
        rows[1] = second
        response = client.post(
            f"{BASE}/courses/{course}/documents/organize",
            headers=headers,
            json=payload(rows, category="不应保存", tags_mode="add", tags=["第十三个"]),
        )
        assert response.status_code == 422
        assert [metadata(client, headers, row["id"]) for row in rows] == rows
        for mode, tags, expected in [
            ("replace", ["A", "B"], ["A", "B"]),
            ("remove", ["A"], ["B"]),
            ("add", ["B", "C"], ["B", "C"]),
            ("clear", [], []),
        ]:
            result = client.post(
                f"{BASE}/courses/{course}/documents/organize",
                headers=headers,
                json=payload(rows, tags_mode=mode, tags=tags),
            )
            assert result.status_code == 200, result.text
            rows = result.json()["items"]
            assert all(row["tags"] == expected for row in rows)
        result = client.post(
            f"{BASE}/courses/{course}/documents/organize",
            headers=headers,
            json=payload(rows, tags_mode="clear"),
        )
        assert result.json()["changed"] == 0 and result.json()["items"] == rows


def test_all_targets_authorized_before_returning_conflict_information():
    with TestClient(app) as client:
        headers, course = context(client)
        foreign, other_course = context(client)
        own = documents(client, headers, course, 1)[0]
        other = documents(client, foreign, other_course, 1)[0]
        client.patch(
            f"{BASE}/documents/{own['id']}", headers=headers, json={"name": "新名字"}
        )
        endpoint = f"{BASE}/courses/{course}/documents/organize"
        for hidden in [other, {**own, "id": str(uuid4())}]:
            result = client.post(
                endpoint, headers=headers, json=payload([own, hidden], category="拒绝")
            )
            assert result.status_code == 404
            assert "conflicts" not in result.text and other["name"] not in result.text
        assert (
            client.post(
                endpoint, headers=foreign, json=payload([own], category="拒绝")
            ).status_code
            == 404
        )
        with SessionLocal() as db:
            db.get(Document, own["id"]).library_scope = "question_bank"
            db.commit()
        assert (
            client.post(
                endpoint, headers=headers, json=payload([own], category="拒绝")
            ).status_code
            == 404
        )


def test_invalid_and_oversized_batch_rejected_without_changes():
    with TestClient(app) as client:
        headers, course = context(client)
        rows = documents(client, headers, course, 1)
        endpoint = f"{BASE}/courses/{course}/documents/organize"
        cases = [
            payload(rows),
            payload(rows * 2, category="重复"),
            payload(rows * 101, category="超限"),
            payload(rows, category=None),
            payload(rows, category=" "),
            payload(rows, tags_mode="clear", tags=["不可夹带"]),
            payload(rows, tags_mode="replace"),
            payload(rows, tags_mode="add", tags=["x" * 33]),
            payload(rows, name="不能批量改名", category="新分类"),
        ]
        nozone = payload(rows, category="新分类")
        nozone["items"][0]["expected_updated_at"] = "2026-10-22T08:00:00"
        cases.append(nozone)
        for value in cases:
            assert client.post(endpoint, headers=headers, json=value).status_code == 422
        assert metadata(client, headers, rows[0]["id"]) == rows[0]


def test_parallel_batch_writers_have_exactly_one_winner():
    with TestClient(app) as client:
        headers, course = context(client)
        rows = documents(client, headers, course)

        def write(category):
            return client.post(
                f"{BASE}/courses/{course}/documents/organize",
                headers=headers,
                json=payload(rows, category=category),
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, ["窗口A", "窗口B"]))
        assert sorted(result.status_code for result in results) == [200, 409]
        winner = next(result for result in results if result.status_code == 200).json()[
            "items"
        ][0]["category"]
        assert all(
            metadata(client, headers, row["id"])["category"] == winner for row in rows
        )


def test_note_options_are_paginated_private_and_readonly():
    with TestClient(app) as client:
        headers, course = context(client)
        foreign, _ = context(client)
        notes = []
        for index in range(24):
            notes.append(
                client.post(
                    f"{BASE}/notes",
                    headers=headers,
                    json={
                        "course_id": course,
                        "title": f"资料核对{index:02}",
                        "content": "机密正文不得进入引用候选。",
                    },
                ).json()
            )
        client.delete(f"{BASE}/notes/{notes[0]['id']}", headers=headers)
        statements = []

        def capture(_conn, _cursor, statement, _params, _context, _many):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", capture)
        endpoint = f"{BASE}/courses/{course}/note-options"
        try:
            first = client.get(endpoint, headers=headers).json()
            last = client.get(endpoint, headers=headers, params={"offset": 20}).json()
            match = client.get(endpoint, headers=headers, params={"q": "核对23"}).json()
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert first["total"] == last["total"] == 23
        assert len(first["items"]) == 20 and len(last["items"]) == 3
        assert len({row["id"] for row in first["items"] + last["items"]}) == 23
        assert match["total"] == 1
        assert all(set(row) == {"id", "title", "updated_at"} for row in first["items"])
        assert not any(
            "notes.content" in query
            or query.lstrip()
            .upper()
            .startswith(("INSERT", "UPDATE", "DELETE", "REPLACE"))
            for query in statements
        )
        assert client.get(endpoint, headers=foreign).status_code == 404
        assert (
            client.get(endpoint, headers=headers, params={"limit": 101}).status_code
            == 422
        )
        assert (
            client.get(endpoint, headers=headers, params={"offset": -1}).status_code
            == 422
        )
