"""Deletion uses temporary accounts and leaves unrelated attempts untouched."""

import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import ExamAttempt, ExamPaper, Mistake, ReviewTask
from test_materialhub import context
from test_question_bank import seed_choice, draw, start


def test_delete_attempt_permission_consent_dependencies_and_relapses():
    with TestClient(app) as c:
        h, course = context(c)
        stranger, _ = context(c)
        _, topic = seed_choice(c, h, course)
        paper = draw(c, h, course, topic, count=1)
        first = start(c, h, paper)
        path = f"/api/v1/attempts/{first['id']}"
        assert c.post(path + "/submit", headers=h).status_code == 200
        mistake = c.get("/api/v1/mistakes", headers=h).json()[0]
        plan = c.post(
            "/api/v1/review-tasks",
            headers=h,
            json={"title": "关联计划", "mistake_id": mistake["id"]},
        ).json()
        second = c.post(f"/api/v1/exam-papers/{paper['id']}/attempts", headers=h).json()
        second_path = f"/api/v1/attempts/{second['id']}"
        assert c.post(second_path + "/submit", headers=h).status_code == 200
        with SessionLocal() as db:
            detail = json.loads(db.get(Mistake, mistake["id"]).detail_json)
            assert len(detail["relapses"]) == 1
        assert c.delete(path, headers=h).status_code == 422
        assert (
            c.delete(path + "?confirm_delete=true", headers=stranger).status_code == 404
        )
        deleted = c.delete(second_path + "?confirm_delete=true", headers=h)
        assert deleted.json() == {
            "deleted": True,
            "mistakes_deleted": 0,
            "review_tasks_deleted": 0,
        }
        with SessionLocal() as db:
            assert (
                json.loads(db.get(Mistake, mistake["id"]).detail_json)["relapses"] == {}
            )
            assert db.get(ExamAttempt, first["id"]) is not None
            assert db.get(ReviewTask, plan["id"]) is not None
        third = c.post(f"/api/v1/exam-papers/{paper['id']}/attempts", headers=h).json()
        deleted = c.delete(path + "?confirm_delete=true", headers=h)
        assert deleted.json() == {
            "deleted": True,
            "mistakes_deleted": 1,
            "review_tasks_deleted": 1,
        }
        assert c.get(path, headers=h).status_code == 404
        assert c.get(path + "/result", headers=h).status_code == 404
        assert c.delete(path + "?confirm_delete=true", headers=h).status_code == 404
        with SessionLocal() as db:
            assert db.get(ExamAttempt, third["id"]) is not None
            assert db.get(ExamPaper, paper["id"]) is not None
            assert db.get(Mistake, mistake["id"]) is None
            assert db.get(ReviewTask, plan["id"]) is None


def test_delete_active_attempt_releases_protection_and_removes_saved_answer():
    with TestClient(app) as c:
        h, course = context(c)
        _, topic = seed_choice(c, h, course)
        paper = draw(c, h, course, topic, count=1)
        attempt = start(c, h, paper)
        path = f"/api/v1/attempts/{attempt['id']}"
        assert (
            c.put(
                path + f"/answers/{paper['questions'][0]['id']}",
                headers=h,
                json={"answer": "A"},
            ).status_code
            == 200
        )
        assert c.delete(path + "?confirm_delete=true", headers=h).status_code == 200
        assert (
            c.put(
                path + f"/answers/{paper['questions'][0]['id']}",
                headers=h,
                json={"answer": "B"},
            ).status_code
            == 404
        )
        with SessionLocal() as db:
            assert db.get(ExamAttempt, attempt["id"]) is None
        assert (
            c.get(f"/api/v1/courses/{course}/past-papers", headers=h).status_code == 200
        )
