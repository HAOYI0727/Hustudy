"""Real isolated API evidence for a read-only cross-module learning hub."""

import json
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import event
from app.main import app
from app.core.database import SessionLocal, engine
from app.models import (
    Course,
    Topic,
    PastPaper,
    PastQuestion,
    ExamBlueprint,
    ExamPaper,
    ExamAttempt,
    Mistake,
    ReviewTask,
)
from app.models.base import utc_now
from test_material_organization import setup_course, import_document


def topic(client, headers, course, name="进程", parent=None):
    r = client.post(
        f"/api/v1/courses/{course}/topics",
        headers=headers,
        json=dict(name=name, parent_id=parent),
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_evidence_notes_candidates_revocation_ownership_and_no_get_writes():
    with TestClient(app) as client:
        h, c = setup_course(client)
        foreign, other = setup_course(client)
        doc, version = import_document(
            client, h, c, "# 进程\n\n进程包含代码与地址空间。"
        )
        t = topic(client, h, c)
        chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=h).json()[0]
        cited = dict(
            version_id=version, chunk_id=chunk["id"], quote="进程包含代码与地址空间。"
        )
        assert (
            client.put(
                f"/api/v1/topics/{t['id']}/sources",
                headers=h,
                json=dict(revision=t["revision"], **cited),
            ).status_code
            == 200
        )
        shared = client.post(
            "/api/v1/notes",
            headers=h,
            json=dict(
                course_id=c,
                title="同源笔记",
                content="不可读取的完整正文",
                citations=[cited],
            ),
        ).json()
        candidate = client.post(
            "/api/v1/notes",
            headers=h,
            json=dict(
                course_id=c, title="标签笔记", content="另一个私有正文", tags=["进程"]
            ),
        ).json()
        client.post(
            "/api/v1/notes",
            headers=foreign,
            json=dict(course_id=other, title="不应出现", content="进程", tags=["进程"]),
        )
        statements = []

        def capture(_c, _cursor, statement, _p, _ctx, _many):
            statements.append(statement.lower())

        event.listen(engine, "before_cursor_execute", capture)
        try:
            path = f"/api/v1/courses/{c}/learning-topics/{t['id']}"
            result = client.get(path, headers=h)
            assert result.status_code == 200, result.text
            data = result.json()
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert data["sources"][0]["title"] == "source"
        assert data["sources"][0]["availability"] == "active"
        assert {(n["id"], n["relation"]) for n in data["notes"]} == {
            (shared["id"], "shared_source"),
            (candidate["id"], "same_tag_candidate"),
        }
        assert (
            "不可读取的完整正文" not in result.text
            and "另一个私有正文" not in result.text
        )
        assert not any(
            s.lstrip().startswith(("update ", "insert ", "delete ")) for s in statements
        )
        assert not any("notes.content" in s for s in statements)
        assert client.get(path, headers=foreign).status_code == 404
        assert (
            client.get(
                f"/api/v1/courses/{other}/learning-topics/{t['id']}", headers=foreign
            ).status_code
            == 404
        )
        assert client.delete(f"/api/v1/documents/{doc}", headers=h).status_code == 204
        data = client.get(path, headers=h).json()
        assert data["sources"][0]["availability"] == "unavailable"
        assert "quote" not in data["sources"][0] and "title" not in data["sources"][0]
        assert all(n["relation"] != "shared_source" for n in data["notes"])


def test_parent_merge_current_mistakes_mastery_relapse_and_no_answer_leak():
    with TestClient(app) as client:
        h, c = setup_course(client)
        uid = client.get("/api/v1/auth/me", headers=h).json()["id"]
        root = topic(client, h, c, "系统")
        child = topic(client, h, c, "进程", root["id"])
        old = topic(client, h, c, "旧名")
        with SessionLocal() as db:
            db.get(Topic, old["id"]).merged_into_id = child["id"]
            bank = PastPaper(
                user_id=uid, course_id=c, title="元数据测试", content_hash=uuid4().hex
            )
            bp = ExamBlueprint(user_id=uid, course_id=c, name="练习", config_json="{}")
            db.add_all([bank, bp])
            db.flush()
            db.add(
                PastQuestion(
                    user_id=uid,
                    paper_id=bank.id,
                    number="1",
                    stem="秘密题干",
                    answer="秘密答案",
                    status="CONFIRMED",
                    bank_data_json=json.dumps({"topic_ids": [root["id"], old["id"]]}),
                )
            )
            paper = ExamPaper(
                user_id=uid,
                course_id=c,
                blueprint_id=bp.id,
                title="练习",
                questions_json="[]",
            )
            db.add(paper)
            db.flush()
            attempt = ExamAttempt(user_id=uid, paper_id=paper.id, status="SCORED")
            db.add(attempt)
            db.flush()
            ids = []
            for kind in ["pending", "mastered", "relapse", "removed"]:
                detail = {
                    "question": {
                        "topic_ids": [root["id"], old["id"]],
                        "stem": "秘密题干",
                        "answer": "秘密答案",
                    }
                }
                if kind in {"mastered", "relapse"}:
                    detail["redoes"] = {
                        "x": {
                            "status": "COMPLETED",
                            "completed_at": "2026-01-01T00:00:00+00:00",
                            "sequence": 1,
                            "correct": True,
                        }
                    }
                if kind == "relapse":
                    detail["relapses"] = {
                        "y": {
                            "completed_at": "2026-01-02T00:00:00+00:00",
                            "sequence": 2,
                        }
                    }
                if kind == "removed":
                    detail["removed_from_bank"] = True
                m = Mistake(
                    user_id=uid,
                    attempt_id=attempt.id,
                    question_id=str(uuid4()),
                    detail_json=json.dumps(detail),
                )
                db.add(m)
                db.flush()
                ids.append(m.id)
            db.add(
                ReviewTask(
                    user_id=uid,
                    mistake_id=ids[0],
                    title="安排复习",
                    due_date="2026-01-01",
                )
            )
            db.add(
                ReviewTask(
                    user_id=uid,
                    mistake_id=ids[1],
                    title="已掌握仍保留的复习计划",
                    due_date="2026-01-03",
                )
            )
            db.commit()
        path = f"/api/v1/courses/{c}/learning-topics"
        result = client.get(path, headers=h)
        assert "秘密题干" not in result.text and "秘密答案" not in result.text
        rows = {r["id"]: r for r in result.json()["items"]}
        assert old["id"] not in rows
        assert rows[root["id"]]["confirmed"] == rows[child["id"]]["confirmed"] == 1
        assert (
            rows[root["id"]]["needs_review"] == rows[child["id"]]["needs_review"] == 2
        )
        result = client.get(path + "/" + child["id"], headers=h)
        assert "秘密题干" not in result.text and "秘密答案" not in result.text
        assert {m["id"] for m in result.json()["mistakes"]} == {ids[0], ids[2]}
        assert result.json()["review_total"] == 2
        merged = client.get(path + "/" + old["id"], headers=h)
        assert (
            merged.status_code == 409
            and merged.json()["error"]["details"]["target_id"] == child["id"]
        )
        with SessionLocal() as db:
            db.get(Course, c).deleted_at = utc_now()
            db.commit()
        assert client.get(path, headers=h).status_code == 404
        assert client.get(path + "/" + child["id"], headers=h).status_code == 404


def test_directory_pagination_alias_literal_search_and_limits():
    with TestClient(app) as client:
        h, c = setup_course(client)
        for i in range(13):
            topic(client, h, c, f"标签{i:02d}")
        path = f"/api/v1/courses/{c}/learning-topics"
        first = client.get(path, headers=h).json()
        second = client.get(path + "?offset=12", headers=h).json()
        assert len(first["items"]) == 12 and len(second["items"]) == 1
        assert first["total"] == 13 and second["total"] == 13
        assert client.get(path + "?state=needs_review", headers=h).json()["total"] == 0
        assert (
            client.get(path + "?state=without_questions", headers=h).json()["total"]
            == 13
        )
        assert client.get(path + "?q=%25", headers=h).json()["total"] == 0
        t = first["items"][0]
        client.patch(
            f"/api/v1/topics/{t['id']}",
            headers=h,
            json=dict(revision=t["revision"], name=t["name"], aliases=["别称"]),
        )
        assert (
            client.get(path + "?q=别称", headers=h).json()["items"][0]["id"] == t["id"]
        )
        assert client.get(path + "?limit=51", headers=h).status_code == 422
        assert client.get(path + "?offset=-1", headers=h).status_code == 422
        uid = client.get("/api/v1/auth/me", headers=h).json()["id"]
        with SessionLocal() as db:
            db.add_all(
                Topic(user_id=uid, course_id=c, name=f"边界{i}") for i in range(1988)
            )
            db.commit()
        response = client.get(path, headers=h)
        assert response.status_code == 422 and "2000" in response.text
