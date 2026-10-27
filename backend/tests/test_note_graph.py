"""Graph reads use isolated data, never ordinary local notes or model calls."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, update

from app.core.database import SessionLocal, engine
from app.main import app
from app.models import Course, Note, NoteLink
from app.models.base import utc_now
from test_materialhub import context


def seed(client, headers, course, titles):
    owner = client.get("/api/v1/auth/me", headers=headers).json()["id"]
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ids = [str(uuid4()) for _ in titles]
    with SessionLocal() as db:
        db.add_all(
            Note(
                id=note_id,
                user_id=owner,
                course_id=course,
                title=title,
                content="正文不得读取的标记" * 1000,
                tags=["图谱"],
                updated_at=stamp + timedelta(seconds=i),
            )
            for i, (note_id, title) in enumerate(zip(ids, titles))
        )
        db.commit()
    return owner, ids


def link(owner, pairs):
    with SessionLocal() as db:
        db.add_all(
            NoteLink(
                user_id=owner,
                source_note_id=source,
                target_note_id=target,
                label="过时链接名称",
            )
            for source, target in pairs
        )
        db.commit()


def graph(client, headers, course, **params):
    response = client.get(
        f"/api/v1/courses/{course}/note-graph", headers=headers, params=params
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_empty_graph_and_default_limits():
    with TestClient(app) as client:
        headers, course = context(client)
        result = graph(client, headers, course)
        assert result == {
            "course_id": course,
            "focus_note_id": None,
            "nodes": [],
            "edges": [],
            "total_nodes": 0,
            "total_edges": 0,
            "node_limit": 120,
            "edge_limit": 400,
            "nodes_truncated": False,
            "edges_truncated": False,
        }


def test_saved_links_deduplicate_direction_and_use_current_metadata():
    with TestClient(app) as client:
        headers, course = context(client)
        a = client.post(
            "/api/v1/notes",
            headers=headers,
            json={"course_id": course, "title": "初始名称", "content": "正文"},
        ).json()
        b = client.post(
            "/api/v1/notes",
            headers=headers,
            json={
                "course_id": course,
                "title": "关联笔记",
                "content": f"[[note:{a['id']}|旧名]]\n[[note:{a['id']}|第二次]]",
            },
        ).json()
        changed = client.patch(
            f"/api/v1/notes/{a['id']}",
            headers=headers,
            json={
                "revision": a["revision"],
                "title": "最新名称",
                "content": f"[[note:{b['id']}]]",
                "tags": ["重点"],
            },
        )
        assert changed.status_code == 200, changed.text
        result = graph(client, headers, course)
        assert result["total_nodes"] == result["total_edges"] == 2
        assert result["edges"] == sorted(
            [
                {"source_id": a["id"], "target_id": b["id"]},
                {"source_id": b["id"], "target_id": a["id"]},
            ],
            key=lambda row: (row["source_id"], row["target_id"]),
        )
        nodes = {n["id"]: n for n in result["nodes"]}
        assert nodes[a["id"]]["title"] == "最新名称"
        assert nodes[a["id"]]["tags"] == ["重点"]
        assert nodes[a["id"]]["revision"] == 2
        assert all(
            n["incoming_count"] == n["outgoing_count"] == 1 for n in nodes.values()
        )
        assert all("content" not in n and "user_id" not in n for n in nodes.values())


def test_title_literal_filters_and_full_course_degrees():
    with TestClient(app) as client:
        headers, course = context(client)
        owner, (a, b, c, d) = seed(
            client, headers, course, ["A%_数学", "B普通笔记", "孤立%_数学", "A普通笔记"]
        )
        link(owner, [(a, b), (a, b), (b, a)])
        result = graph(client, headers, course, q="%_")
        assert {n["id"] for n in result["nodes"]} == {a, c}
        assert result["total_edges"] == 0
        assert next(n for n in result["nodes"] if n["id"] == a)["incoming_count"] == 1
        isolated = graph(client, headers, course, q="数学", link_state="isolated")
        assert [n["id"] for n in isolated["nodes"]] == [c]
        linked = graph(client, headers, course, q="a", link_state="linked")
        assert [n["id"] for n in linked["nodes"]] == [a]
        assert linked["nodes"][0]["outgoing_count"] == 1
        assert (
            graph(client, headers, course, q="正文不得读取的标记")["total_nodes"] == 0
        )
        assert {
            n["id"]
            for n in graph(client, headers, course, link_state="isolated")["nodes"]
        } == {c, d}


def test_focus_is_one_hop_prioritized_and_counts_before_node_limit():
    with TestClient(app) as client:
        headers, course = context(client)
        owner, (a, b, c, depth_two, isolated) = seed(
            client, headers, course, ["中心", "邻居一", "邻居二", "第二跳", "孤立"]
        )
        link(owner, [(a, b), (c, a), (b, c), (b, depth_two)])
        result = graph(client, headers, course, focus_note_id=a, limit=2)
        assert [n["id"] for n in result["nodes"]] == [a, c]
        assert result["total_nodes"] == result["total_edges"] == 3
        assert result["edges"] == [{"source_id": c, "target_id": a}]
        assert result["nodes_truncated"] and result["edges_truncated"]
        full = graph(client, headers, course, focus_note_id=a)
        assert [n["id"] for n in full["nodes"]] == [a, c, b]
        assert next(n for n in full["nodes"] if n["id"] == b)["outgoing_count"] == 2
        assert len(full["edges"]) == 3
        assert not full["nodes_truncated"] and not full["edges_truncated"]
        single = graph(client, headers, course, focus_note_id=isolated)
        assert [n["id"] for n in single["nodes"]] == [isolated]
        assert single["total_edges"] == 0


def test_node_limit_real_total_stable_order_and_hidden_edges():
    with TestClient(app) as client:
        headers, course = context(client)
        owner, ids = seed(client, headers, course, [f"节点{i}" for i in range(205)])
        link(owner, list(zip(ids, ids[1:])))
        result = graph(client, headers, course)
        assert result["total_nodes"] == 205 and len(result["nodes"]) == 120
        assert result["total_edges"] == 204 and len(result["edges"]) == 119
        assert [n["id"] for n in result["nodes"]] == list(reversed(ids))[:120]
        assert result["nodes_truncated"] and result["edges_truncated"]
        assert graph(client, headers, course) == result
        maximum = graph(client, headers, course, limit=200)
        assert len(maximum["nodes"]) == 200 and len(maximum["edges"]) == 199
        # Equal timestamps still use UUID order, independent of insertion order.
        with SessionLocal() as db:
            db.execute(
                update(Note).where(Note.id.in_(ids)).values(updated_at=utc_now())
            )
            db.commit()
        tied = graph(client, headers, course, limit=200)
        assert [n["id"] for n in tied["nodes"]] == sorted(ids)[:200]


def test_edge_limit_applies_after_dedup_and_preserves_full_degrees():
    with TestClient(app) as client:
        headers, course = context(client)
        owner, ids = seed(client, headers, course, [f"密集节点{i}" for i in range(22)])
        pairs = [(a, b) for a in ids for b in ids if a != b]
        link(owner, pairs + pairs)
        result = graph(client, headers, course)
        assert result["total_nodes"] == 22 and result["total_edges"] == 462
        assert len(result["edges"]) == 400
        assert not result["nodes_truncated"] and result["edges_truncated"]
        assert [(e["source_id"], e["target_id"]) for e in result["edges"]] == sorted(
            pairs
        )[:400]
        assert all(
            n["incoming_count"] == n["outgoing_count"] == 21 for n in result["nodes"]
        )


def test_permissions_recycle_and_malformed_link_ownership_are_excluded():
    with TestClient(app) as client:
        headers, course = context(client)
        foreign, foreign_course = context(client)
        second_course = client.post(
            "/api/v1/courses", headers=headers, json={"name": "其他课程"}
        ).json()["id"]
        owner, (a, b, trash) = seed(client, headers, course, ["A", "B", "回收站"])
        _, (cross_course,) = seed(client, headers, second_course, ["跨课程"])
        other, (foreign_id,) = seed(client, foreign, foreign_course, ["他人笔记"])
        _, (bad_owner_id,) = seed(client, foreign, course, ["错误归属数据"])
        link(
            owner,
            [
                (a, b),
                (a, trash),
                (a, cross_course),
                (foreign_id, a),
                (a, bad_owner_id),
                (a, a),
            ],
        )
        link(other, [(b, a)])
        with SessionLocal() as db:
            db.get(Note, trash).deleted = True
            db.commit()
        result = graph(client, headers, course)
        assert {n["id"] for n in result["nodes"]} == {a, b}
        assert result["total_edges"] == 1
        assert result["edges"] == [{"source_id": a, "target_id": b}]
        endpoint = f"/api/v1/courses/{course}/note-graph"
        assert client.get(endpoint).status_code == 401
        assert client.get(endpoint, headers=foreign).status_code == 404
        for target in (trash, cross_course, foreign_id, bad_owner_id, str(uuid4())):
            assert (
                client.get(
                    endpoint, headers=headers, params={"focus_note_id": target}
                ).status_code
                == 404
            )
        with SessionLocal() as db:
            db.get(Note, trash).deleted = False
            db.commit()
        restored = graph(client, headers, course)
        assert restored["total_nodes"] == 3 and restored["total_edges"] == 2
        with SessionLocal() as db:
            db.get(Course, course).deleted_at = utc_now()
            db.commit()
        assert client.get(endpoint, headers=headers).status_code == 404


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 201},
        {"q": "字" * 201},
        {"link_state": "unknown"},
        {"focus_note_id": "not-a-uuid"},
        {"focus_note_id": str(uuid4()), "q": "不能混用"},
        {"focus_note_id": str(uuid4()), "link_state": "linked"},
    ],
)
def test_query_validation(params):
    with TestClient(app) as client:
        headers, course = context(client)
        assert (
            client.get(
                f"/api/v1/courses/{course}/note-graph", headers=headers, params=params
            ).status_code
            == 422
        )


def test_reads_neither_note_bodies_nor_mutates_rows():
    with TestClient(app) as client:
        headers, course = context(client)
        owner, (a, b) = seed(client, headers, course, ["甲", "乙"])
        link(owner, [(a, b)])
        statements = []

        def capture(_conn, _cursor, sql, _params, _ctx, _many):
            statements.append(sql)

        event.listen(engine, "before_cursor_execute", capture)
        try:
            graph(client, headers, course)
            graph(client, headers, course, focus_note_id=a)
            graph(client, headers, course, q="甲", link_state="linked")
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert statements
        assert not any(
            "notes.content" in sql or "note_links.label" in sql for sql in statements
        )
        assert not any(
            sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "REPLACE"))
            for sql in statements
        )


def test_counts_nodes_and_edges_share_snapshot_during_concurrent_deletion():
    with TestClient(app) as client:
        headers, course = context(client)
        owner, (a, b) = seed(client, headers, course, ["甲", "乙"])
        link(owner, [(a, b)])
        changed = False

        def mutate_after_count(_conn, _cursor, sql, _params, _ctx, _many):
            nonlocal changed
            if not changed and "FROM graph_scope" in sql and "SELECT count(" in sql:
                changed = True
                with SessionLocal() as writer:
                    writer.execute(
                        update(Note).where(Note.id == b).values(deleted=True)
                    )
                    writer.commit()

        event.listen(engine, "after_cursor_execute", mutate_after_count)
        try:
            result = graph(client, headers, course)
        finally:
            event.remove(engine, "after_cursor_execute", mutate_after_count)
        assert changed
        assert result["total_nodes"] == len(result["nodes"]) == 2
        assert result["total_edges"] == len(result["edges"]) == 1
        current = graph(client, headers, course)
        assert current["total_nodes"] == 1 and current["total_edges"] == 0
