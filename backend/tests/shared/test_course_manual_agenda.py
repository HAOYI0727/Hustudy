from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from tests.m1.test_materialhub import context


def test_manual_agenda_course_scope_status_and_delete():
    with TestClient(app) as client:
        headers, course = context(client)
        payload = {"course_id": course, "title": "复习事务与锁", "due_date": date.today().isoformat()}
        response = client.post("/api/v1/review-tasks", headers=headers, json=payload)
        assert response.status_code == 201, response.text
        identity = response.json()["id"]
        route = "/api/v1/review-tasks"
        page = client.get(route, headers=headers, params={"course_id": course}).json()
        assert page["total"] == 1 and page["counts"]["pending"] == 1
        status = route + f"/{identity}/status"
        assert client.patch(status, headers=headers, json={"status": "COMPLETED", "expected_status": "PENDING"}).status_code == 200
        page = client.get(route, headers=headers, params={"course_id": course, "state": "completed"}).json()
        assert page["total"] == 1 and page["counts"]["pending"] == 0
        assert client.patch(status, headers=headers, json={"status": "PENDING", "expected_status": "COMPLETED"}).status_code == 200
        other, other_course = context(client)
        assert client.get(route, headers=other, params={"course_id": other_course}).json()["total"] == 0
        assert client.delete(route + f"/{identity}", headers=other).status_code == 404
        assert client.post(route, headers=other, json=payload).status_code == 404
        assert client.delete(route + f"/{identity}", headers=headers).status_code == 204
        assert client.get(route, headers=headers, params={"course_id": course}).json()["total"] == 0
