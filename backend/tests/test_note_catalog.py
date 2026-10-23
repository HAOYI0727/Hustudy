from fastapi.testclient import TestClient
from sqlalchemy import event

from app.core.database import SessionLocal, engine
from app.main import app
from app.models import Note, Course
from app.models.base import utc_now
from test_materialhub import context


def test_catalog_paginates_metadata_without_bodies_and_stable_order():
    with TestClient(app) as client:
        headers, course = context(client)
        owner = client.get("/api/v1/auth/me", headers=headers).json()["id"]
        with SessionLocal() as db:
            for i in range(211):
                db.add(
                    Note(
                        user_id=owner,
                        course_id=course,
                        title=f"目录{i:03}",
                        content="不可发送到目录的长正文" * 1000,
                        tags=["重点"],
                    )
                )
            db.commit()
        statements = []

        def capture(_conn, _cursor, sql, _params, _ctx, _many):
            statements.append(sql)

        event.listen(engine, "before_cursor_execute", capture)
        try:
            first = client.get("/api/v1/notes/catalog", headers=headers).json()
            last = client.get(
                "/api/v1/notes/catalog?offset=200", headers=headers
            ).json()
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert first["total"] == last["total"] == 211
        assert len(first["items"]) == 200 and len(last["items"]) == 11
        assert len({n["id"] for n in first["items"] + last["items"]}) == 211
        assert all("content" not in n and n["revision"] == 1 for n in first["items"])
        assert not any(
            "notes.content" in statement
            or statement.lstrip()
            .upper()
            .startswith(("INSERT", "UPDATE", "DELETE", "REPLACE"))
            for statement in statements
        )
        assert (
            client.get("/api/v1/notes/catalog?limit=201", headers=headers).status_code
            == 422
        )
        assert (
            client.get("/api/v1/notes/catalog?offset=-1", headers=headers).status_code
            == 422
        )


def test_catalog_and_body_match_hide_foreign_trashed_and_revoked_notes():
    with TestClient(app) as client:
        headers, course = context(client)
        foreign, foreign_course = context(client)
        owner = client.get("/api/v1/auth/me", headers=headers).json()["id"]
        other = client.get("/api/v1/auth/me", headers=foreign).json()["id"]
        with SessionLocal() as db:
            live = Note(
                user_id=owner,
                course_id=course,
                title="合法标题",
                content="独特正文关键词",
                tags=["精确"],
            )
            db.add_all(
                [
                    live,
                    Note(
                        user_id=owner,
                        course_id=course,
                        title="回收站",
                        content="独特正文关键词",
                        deleted=True,
                    ),
                    Note(
                        user_id=other,
                        course_id=foreign_course,
                        title="他人笔记",
                        content="独特正文关键词",
                    ),
                    Note(
                        user_id=owner, course_id=None, title="全局笔记", content="全局"
                    ),
                ]
            )
            db.commit()
            live_id = live.id
        result = client.get(
            f"/api/v1/courses/{course}/note-matches?q=独特正文关键词", headers=headers
        )
        assert result.json() == {"ids": [live_id]}
        assert client.get(
            f"/api/v1/courses/{course}/note-matches?q=独特正文关键词&tag=精确",
            headers=headers,
        ).json()["ids"] == [live_id]
        assert (
            client.get(
                f"/api/v1/courses/{course}/note-matches?tag=精", headers=headers
            ).json()["ids"]
            == []
        )
        assert (
            client.get(
                f"/api/v1/courses/{course}/note-matches", headers=foreign
            ).status_code
            == 404
        )
        rows = client.get("/api/v1/notes/catalog", headers=headers).json()["items"]
        assert {row["title"] for row in rows} == {"合法标题", "全局笔记"}
        with SessionLocal() as db:
            db.get(Course, course).deleted_at = utc_now()
            db.commit()
        rows = client.get("/api/v1/notes/catalog", headers=headers).json()["items"]
        assert [row["title"] for row in rows] == ["全局笔记"]
        assert (
            client.get(
                f"/api/v1/courses/{course}/note-matches", headers=headers
            ).status_code
            == 404
        )


def test_backlink_options_check_ownership_and_never_return_bodies():
    with TestClient(app) as client:
        headers, course = context(client)
        foreign, _ = context(client)
        a = client.post(
            "/api/v1/notes",
            headers=headers,
            json={"course_id": course, "title": "原概念", "content": "原正文"},
        ).json()
        b = client.post(
            "/api/v1/notes",
            headers=headers,
            json={
                "course_id": course,
                "title": "关联概念",
                "content": f"[[note:{a['id']}|名称]]",
            },
        ).json()
        endpoint = f"/api/v1/notes/{a['id']}/backlink-options"
        rows = client.get(endpoint, headers=headers).json()
        assert len(rows) == 1 and rows[0]["id"] == b["id"] and "content" not in rows[0]
        assert client.get(endpoint, headers=foreign).status_code == 404
        client.delete(f"/api/v1/notes/{b['id']}", headers=headers)
        assert client.get(endpoint, headers=headers).json() == []
