"""Read-only course records: real pagination, lifecycle, and metadata boundaries."""

import json
from datetime import datetime, timezone
from sqlalchemy import event
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine
from app.models import AIResult, Note, Document, Mistake, ExamAttempt
from test_material_organization import setup_course, import_document
from test_learning_workspace import snapshot


def path(course):
    return f"/api/v1/courses/{course}/learning-records"


def test_records_combine_six_owned_kinds_without_bodies_answers_or_writes():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        other, _ = setup_course(client)
        uid = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        document, version = import_document(client, owner, course, "# 来源\n可核对原文。")
        chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[0]
        attempt, mistake = snapshot(uid, course, version, chunk)
        note = client.post("/api/v1/notes", headers=owner, json={
            "course_id": course, "title": "复盘笔记", "content": "笔记正文不能进入学习列表",
        }).json()
        with SessionLocal() as db:
            for prompt in ("mock-v1", "demo-study-report-v2"):
                db.add(AIResult(user_id=uid, course_id=course, query="理解进程",
                               result_json='{"answer":"模型正文不能进入列表"}',
                               status="grounded", model_mode="demo", prompt_version=prompt))
            db.commit()
        statements = []

        def capture(_conn, _cursor, sql, _params, _context, _many):
            statements.append(sql)

        event.listen(engine, "before_cursor_execute", capture)
        try:
            response = client.get(path(course), headers=owner)
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 6 and set(body["counts"].values()) == {1}
        rows = {row["kind"]: row for row in body["items"]}
        assert rows["material"]["version_id"] == version
        assert rows["material"]["document_id"] == document
        assert rows["note"]["id"] == note["id"] and rows["attempt"]["id"] == attempt
        assert rows["mistake"]["id"] == mistake
        assert rows["report"]["title"] == "学习报告 · 理解进程"
        assert body["checked_at"].endswith(("Z", "+00:00"))
        assert all(row["updated_at"].endswith(("Z", "+00:00")) for row in body["items"])
        assert all(word not in response.text for word in (
            "笔记正文不能", "模型正文不能", "标准答案", "私有题干", "answers_json", "storage_path",
        ))
        assert not {"INSERT", "UPDATE", "DELETE", "REPLACE"}.intersection(
            sql.strip().split()[0].upper() for sql in statements
        )
        assert "notes.content" not in "\n".join(statements)
        assert "exam_attempts.answers_json" not in "\n".join(statements)
        assert client.get(path(course), headers=other).status_code == 404
        assert client.get(path(course)).status_code == 401


def test_records_use_sql_pagination_stable_ties_and_literal_title_search():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        uid = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        same = datetime(2026, 10, 20, tzinfo=timezone.utc)
        with SessionLocal() as db:
            rows = [Note(user_id=uid, course_id=course, title=f"笔记{i:02}",
                         content="不参与标题搜索的私有文本", updated_at=same) for i in range(27)]
            db.add_all(rows)
            db.add(Note(user_id=uid, course_id=course, title="100%_SQL ' 字面", content="正文"))
            db.commit()
            expected = sorted(row.id for row in rows)
        collected = []
        for offset in (0, 10, 20):
            page = client.get(path(course), headers=owner, params={
                "kind": "note", "q": "笔记", "offset": offset, "limit": 10,
            }).json()
            assert page["total"] == 27 and page["counts"]["note"] == 27
            assert len(page["items"]) == min(10, 27 - offset)
            collected.extend(row["id"] for row in page["items"])
        assert collected == expected and len(set(collected)) == 27
        exact = client.get(path(course), headers=owner, params={"q": "%_sql '"}).json()
        assert exact["total"] == 1 and exact["items"][0]["title"].startswith("100%_")
        assert client.get(path(course), headers=owner, params={
            "q": "不参与标题搜索",
        }).json()["total"] == 0
        assert client.get(path(course), headers=owner, params={
            "q": "' OR 1=1 --",
        }).json()["total"] == 0
        assert client.get(path(course), headers=owner, params={"offset": 100}).json()["items"] == []
        for bad in ({"kind": "unknown"}, {"offset": -1}, {"offset": 1000001},
                    {"limit": 0}, {"limit": 51}, {"q": "字" * 201}):
            assert client.get(path(course), headers=owner, params=bad).status_code == 422


def test_lifecycle_scopes_exclude_trash_retired_candidates_and_question_bank_files():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        uid = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        document, version = import_document(client, owner, course, "# 来源\n可核对原文。")
        chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[0]
        _, mistake = snapshot(uid, course, version, chunk)
        note = client.post("/api/v1/notes", headers=owner, json={
            "course_id": course, "title": "待删除", "content": "正文",
        }).json()
        with SessionLocal() as db:
            db.add(AIResult(user_id=uid, course_id=course, query="停用候选",
                           result_json='{"result_kind":"question_drafts"}',
                           status="grounded", model_mode="demo"))
            db.commit()
        assert client.get(path(course), headers=owner).json()["total"] == 4
        assert client.delete(f"/api/v1/notes/{note['id']}", headers=owner).status_code == 204
        with SessionLocal() as db:
            db.get(Document, document).library_scope = "question_bank"
            row = db.get(Mistake, mistake)
            value = json.loads(row.detail_json)
            value["removed_from_bank"] = True
            row.detail_json = json.dumps(value)
            db.commit()
        data = client.get(path(course), headers=owner).json()
        assert data["total"] == 1 and data["items"][0]["kind"] == "attempt"
        with SessionLocal() as db:
            db.get(Document, document).library_scope = "material"
            db.commit()
        assert client.delete(f"/api/v1/documents/{document}", headers=owner).status_code == 204
        assert client.get(path(course), headers=owner).json()["counts"]["material"] == 0
        assert client.delete(f"/api/v1/courses/{course}?revision=1", headers=owner).status_code == 204
        assert client.get(path(course), headers=owner).status_code == 404


def test_foreign_attempt_cannot_link_records_into_another_owners_course():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        other, _ = setup_course(client)
        uid = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        foreign_uid = client.get("/api/v1/auth/me", headers=other).json()["id"]
        _, version = import_document(client, owner, course, "# 来源\n可核对原文。")
        chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[0]
        attempt, _ = snapshot(uid, course, version, chunk)
        with SessionLocal() as db:
            db.get(ExamAttempt, attempt).user_id = foreign_uid
            db.commit()
        page = client.get(path(course), headers=owner).json()
        assert page["counts"]["attempt"] == 0 and page["counts"]["mistake"] == 0
        assert client.get(path(course), headers=other).status_code == 404
