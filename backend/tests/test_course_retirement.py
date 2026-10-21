"""Integration risks: deletion, cross-module authorization, rollback, late workers."""

from datetime import datetime, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from app.main import app
from app.core.database import SessionLocal
from app.models import (
    Course,
    Document,
    DocumentVersion,
    Note,
    Citation,
    ProcessingJob,
    ReviewTask,
)
from app.workers.materials import drain_jobs
from test_material_organization import setup_course, import_document
from test_question_bank import seed_choice
from test_preview_assets import png


def fixture(client):
    owner, course = setup_course(client)
    foreign, _ = setup_course(client)
    doc, version = import_document(
        client, owner, course, "# Hustudy\n\n课程来源必须保持可追溯。"
    )
    chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[0]
    note = client.post(
        "/api/v1/notes",
        headers=owner,
        json={"course_id": course, "title": "课程笔记", "content": "自制笔记"},
    ).json()
    outer = client.post(
        "/api/v1/notes",
        headers=owner,
        json={
            "title": "独立笔记",
            "content": f"[[note:{note['id']}|课程笔记]]",
            "citations": [
                {
                    "version_id": version,
                    "chunk_id": chunk["id"],
                    "quote": "课程来源必须保持可追溯。",
                }
            ],
        },
    ).json()
    asset = client.post(
        f"/api/v1/courses/{course}/assets",
        headers=owner,
        files={"file": ("figure.png", png(), "image/png")},
    ).json()
    ai = client.post(
        f"/api/v1/courses/{course}/ai-queries",
        headers=owner,
        json={"query": "课程", "mode": "demo"},
    ).json()
    past = client.post(
        f"/api/v1/courses/{course}/past-papers",
        headers=owner,
        json={"title": "自制真题", "content": "1. 简述条件。"},
    ).json()
    seed_choice(client, owner, course)
    bp = client.post(
        f"/api/v1/exam-blueprints?course_id={course}",
        headers=owner,
        json={
            "name": "自制蓝图",
            "total_points": 5,
            "duration_minutes": 5,
            "question_types": [{"type": "single_choice", "count": 1, "points": 5}],
            "topics": [{"name": "综合", "count": 1}],
        },
    ).json()
    paper = client.post(
        f"/api/v1/exam-blueprints/{bp['id']}/generate", headers=owner
    ).json()
    correct = client.get(f"/api/v1/exam-papers/{paper['id']}?include_answers=true", headers=owner).json()["questions"][0]["answer"]
    wrong = next(c for c in "ABCD" if c != correct)
    client.post(f"/api/v1/exam-papers/{paper['id']}/review", headers=owner)
    attempt = client.post(
        f"/api/v1/exam-papers/{paper['id']}/attempts", headers=owner
    ).json()
    question = paper["questions"][0]["id"]
    client.put(
        f"/api/v1/attempts/{attempt['id']}/answers/{question}",
        headers=owner,
        json={"answer": wrong},
    )
    client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=owner)
    mistake = client.get("/api/v1/mistakes", headers=owner).json()[0]
    today = datetime.now(timezone.utc).date().isoformat()
    reviews = []
    for completed in (True, False):
        task = client.post(
            "/api/v1/review-tasks",
            headers=owner,
            json={"mistake_id": mistake["id"], "title": "课程复习", "due_date": today},
        ).json()
        if completed:
            client.post(f"/api/v1/review-tasks/{task['id']}/complete", headers=owner)
        reviews.append(task["id"])
    standalone = client.post(
        "/api/v1/review-tasks",
        headers=owner,
        json={"title": "独立复习", "due_date": today},
    ).json()
    export = client.post(
        f"/api/v1/courses/{course}/material-exports",
        headers=owner,
        json={"request_id": str(uuid4())},
    ).json()
    pending = client.post(
        f"/api/v1/courses/{course}/documents",
        headers=owner,
        files={"file": ("later.md", b"# later", "text/markdown")},
    ).json()
    return locals()


def test_course_removal_revokes_resources_preserves_outside_notes_and_foreign_data():
    with TestClient(app) as client:
        data = fixture(client)
        owner, foreign, course = data["owner"], data["foreign"], data["course"]
        base = f"/api/v1/courses/{course}"
        foreign_before = client.get("/api/v1/courses", headers=foreign).json()
        other = client.post(
            "/api/v1/courses", headers=owner, json={"name": "另一课程"}
        ).json()
        for method, path, payload in [
            ("get", base + "/deletion-preview", None),
            ("delete", base + "?revision=1", None),
        ]:
            response = getattr(client, method)(path, headers=foreign)
            assert response.status_code == 404
        preview = client.get(base + "/deletion-preview", headers=owner).json()
        assert preview["course"]["revision"] == 1
        assert preview["counts"] == {
            "documents": 2,
            "versions": 2,
            "assets": 1,
            "material_exports": 1,
            "notes": 1,
            "ai_results": 1,
            "past_papers": 2,
            "exam_papers": 1,
            "attempts": 1,
            "review_tasks": 2,
            "remote_queries": 0,
        }
        assert client.delete(base, headers=owner).status_code == 422
        assert client.delete(base + "?revision=2", headers=owner).status_code == 409
        assert client.delete(base + "?revision=1", headers=owner).status_code == 204
        assert client.delete(base + "?revision=1", headers=owner).status_code == 404
        assert [
            c["id"] for c in client.get("/api/v1/courses", headers=owner).json()
        ] == [other["id"]]
        assert client.get("/api/v1/courses", headers=foreign).json() == foreign_before
        paths = [
            base + suffix
            for suffix in (
                "/deletion-preview",
                "/documents",
                "/assets",
                "/assets/page",
                "/jobs",
                "/topics",
                "/past-papers",
                "/search?q=Hustudy",
                "/material-exports",
            )
        ]
        paths += [
            f"/api/v1/documents/{data['doc']}",
            f"/api/v1/documents/{data['doc']}/versions",
        ]
        paths += [
            f"/api/v1/versions/{data['version']}" + suffix
            for suffix in (
                "",
                "/chunks",
                "/original",
                "/preview",
                "/references",
                "/transcripts",
            )
        ]
        paths += [
            f"/api/v1/notes/{data['note']['id']}" + suffix
            for suffix in ("", "/citations", "/backlinks", "/export")
        ]
        paths += [
            f"/api/v1/assets/{data['asset']['id']}",
            f"/api/v1/ai-results/{data['ai']['id']}",
            f"/api/v1/exam-papers/{data['paper']['id']}",
            f"/api/v1/attempts/{data['attempt']['id']}/result",
        ]
        paths += [
            f"/api/v1/jobs/{data['pending']['id']}",
            f"/api/v1/jobs/{data['export']['job']['id']}",
        ]
        paths += [
            f"/api/v1/material-exports/{data['export']['id']}" + suffix
            for suffix in ("", "/download")
        ]
        for path in paths:
            for who in (owner, foreign):
                response = client.get(path, headers=who)
                assert response.status_code == 404, (path, response.text)
        assert (
            client.get(f"/api/v1/notes?course_id={course}", headers=owner).status_code
            == 404
        )
        outer = client.get(f"/api/v1/notes/{data['outer']['id']}", headers=owner).json()
        assert outer["content"] == data["outer"]["content"]
        citations = client.get(
            f"/api/v1/notes/{outer['id']}/citations", headers=owner
        ).json()
        assert (
            citations[0]["version_id"] == data["version"]
            and citations[0]["availability"] == "unavailable"
        )
        assert client.get("/api/v1/mistakes", headers=owner).json() == []
        tasks = client.get("/api/v1/review-tasks/today", headers=owner).json()
        assert [t["id"] for t in tasks] == [data["standalone"]["id"]]
        for task in data["reviews"]:
            assert (
                client.post(
                    f"/api/v1/review-tasks/{task}/complete", headers=owner
                ).status_code
                == 404
            )
        for path, payload in [
            (base + "/ai-queries", {"query": "Hustudy", "mode": "demo"}),
            (
                f"/api/v1/versions/{data['version']}/reindex",
                {"request_id": str(uuid4())},
            ),
            (f"/api/v1/exam-blueprints/{data['bp']['id']}/generate", {}),
            (f"/api/v1/attempts/{data['attempt']['id']}/submit", {}),
            (f"/api/v1/past-papers/{data['past']['id']}/extract", {}),
        ]:
            assert client.post(path, headers=owner, json=payload).status_code == 404
        assert (
            client.post(
                base + "/documents",
                headers=owner,
                files={"file": ("new.md", b"x", "text/markdown")},
            ).status_code
            == 404
        )
        assert (
            client.patch(
                base, headers=owner, json={"revision": 1, "name": "复活"}
            ).status_code
            == 404
        )
        with SessionLocal() as db:
            assert db.get(Course, course).deleted_at is not None
            assert db.get(Note, data["note"]["id"]).deleted
            assert db.get(Document, data["doc"]).deleted_at is not None
            assert db.get(DocumentVersion, data["version"]) is not None
            for job in (data["pending"]["id"], data["export"]["job"]["id"]):
                row = db.get(ProcessingJob, job)
                assert row.status == "CANCELLED" and row.lease_token is None
            assert not db.scalars(
                select(ReviewTask).where(ReviewTask.id.in_(data["reviews"]))
            ).all()
            assert db.execute(text("PRAGMA foreign_key_check")).all() == []
        drain_jobs()


def test_course_removal_rolls_back_all_modules_on_failure(monkeypatch):
    with TestClient(app, raise_server_exceptions=False) as client:
        data = fixture(client)

        def failed(*_args):
            raise RuntimeError("injected module retirement failure")

        with monkeypatch.context() as patch:
            patch.setattr("app.services.course_retirement.retire_course_ai", failed)
            response = client.delete(
                f"/api/v1/courses/{data['course']}?revision=1", headers=data["owner"]
            )
        assert response.status_code == 500
        assert "injected" not in response.text
        assert (
            client.get(
                f"/api/v1/versions/{data['version']}/original", headers=data["owner"]
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/api/v1/notes/{data['note']['id']}", headers=data["owner"]
            ).status_code
            == 200
        )
        with SessionLocal() as db:
            assert db.get(Course, data["course"]).deleted_at is None
            assert db.get(ProcessingJob, data["pending"]["id"]).status == "QUEUED"
            assert db.get(ProcessingJob, data["export"]["job"]["id"]).status == "QUEUED"
            assert (
                db.scalar(
                    select(Citation).where(Citation.note_id == data["outer"]["id"])
                ).availability
                == "active"
            )
            assert (
                db.execute(
                    text("SELECT count(*) FROM chunk_search WHERE chunk_id=:c"),
                    {"c": data["chunk"]["id"]},
                ).scalar()
                == 1
            )


def test_course_removal_during_export_drops_late_file(monkeypatch):
    from app.workers import material_exports as worker

    with TestClient(app) as client:
        owner, course = setup_course(client)
        import_document(client, owner, course, "# source\n\nTest body")
        record = client.post(
            f"/api/v1/courses/{course}/material-exports",
            headers=owner,
            json={"request_id": str(uuid4())},
        ).json()
        original = worker.build_package
        outputs = []

        def delayed(db, row, output):
            result = original(db, row, output)
            outputs.append(output)
            assert (
                client.delete(
                    f"/api/v1/courses/{course}?revision=1", headers=owner
                ).status_code
                == 204
            )
            return result

        monkeypatch.setattr(worker, "build_package", delayed)
        assert worker.run_export_once()
        assert not outputs[0].exists()
        assert (
            client.get(
                f"/api/v1/material-exports/{record['id']}/download", headers=owner
            ).status_code
            == 404
        )
