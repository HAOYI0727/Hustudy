"""Review schedule visibility, timezone, paging and CAS preserve grading."""

from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import User, ReviewTask, Mistake
from test_material_organization import setup_course, import_document
from test_learning_workspace import snapshot


def test_review_calendar_paging_timezone_owner_and_reschedule_conflict():
    with TestClient(app) as client:
        owner, _ = setup_course(client)
        foreign, _ = setup_course(client)
        user_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        with SessionLocal() as db:
            db.get(User, user_id).timezone = "Pacific/Honolulu"
            for i in range(25):
                db.add(
                    ReviewTask(user_id=user_id, title=f"计划{i}", due_date="2026-11-10")
                )
            db.commit()
        response = client.get("/api/v1/review-tasks", headers=owner)
        assert response.status_code == 200, response.text
        page = response.json()
        assert page["total"] == 25 and len(page["items"]) == 20
        assert (
            page["today"]
            == datetime.now(ZoneInfo("Pacific/Honolulu")).date().isoformat()
        )
        assert page["timezone"] == "Pacific/Honolulu"
        assert (
            len(
                client.get("/api/v1/review-tasks?offset=20", headers=owner).json()[
                    "items"
                ]
            )
            == 5
        )
        assert (
            client.get("/api/v1/review-tasks?limit=101", headers=owner).status_code
            == 422
        )
        assert client.get("/api/v1/review-tasks", headers=foreign).json()["total"] == 0
        task = page["items"][0]
        path = f"/api/v1/review-tasks/{task['id']}"
        payload = {"due_date": "2026-12-01", "expected_due_date": task["due_date"]}
        assert client.patch(path, headers=foreign, json=payload).status_code == 404
        assert client.patch(path, headers=owner, json=payload).status_code == 200
        assert (
            client.patch(
                path, headers=owner, json=payload | {"due_date": "2026-12-02"}
            ).status_code
            == 409
        )
        assert client.post(path + "/complete", headers=owner).status_code == 200
        assert client.get("/api/v1/review-tasks", headers=owner).json()["total"] == 24
        assert (
            client.get("/api/v1/review-tasks?state=all", headers=owner).json()["total"]
            == 25
        )
        assert (
            client.get("/api/v1/review-tasks?state=invalid", headers=owner).status_code
            == 422
        )


def test_schedule_is_idempotent_independent_of_mastery_and_hides_removed_sources():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        user_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        _, version = import_document(client, owner, course, "# 复习\n可核对原文。")
        chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[
            0
        ]
        _, mistake_id = snapshot(user_id, course, version, chunk)
        payload = {
            "mistake_id": mistake_id,
            "title": "未来回顾",
            "due_date": "2026-12-10",
        }
        first = client.post("/api/v1/review-tasks", headers=owner, json=payload).json()
        second = client.post("/api/v1/review-tasks", headers=owner, json=payload).json()
        assert first["id"] == second["id"]
        assert client.get("/api/v1/review-tasks", headers=owner).json()["total"] == 1
        with SessionLocal() as db:
            before = db.get(Mistake, mistake_id).detail_json
        assert (
            client.post(
                f"/api/v1/review-tasks/{first['id']}/complete", headers=owner
            ).status_code
            == 200
        )
        with SessionLocal() as db:
            assert db.get(Mistake, mistake_id).detail_json == before
            db.get(Mistake, mistake_id).detail_json = '{"removed_from_bank":true}'
            db.commit()
        assert (
            client.get("/api/v1/review-tasks?state=all", headers=owner).json()["total"]
            == 0
        )
