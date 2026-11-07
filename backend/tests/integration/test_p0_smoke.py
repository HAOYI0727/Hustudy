from tests.m4.test_question_bank import seed_choice
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.workers.materials import drain_jobs


def test_p0_course_material_ai_and_exam_flow():
    with TestClient(app) as client:
        username = "test_" + uuid4().hex[:10]
        registered = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "password123"},
        )
        assert registered.status_code == 201
        headers = {"Authorization": "Bearer " + registered.json()["access_token"]}
        course = client.post(
            "/api/v1/courses", headers=headers, json={"name": "测试课程"}
        )
        assert course.status_code == 201
        course_id = course.json()["id"]
        upload = client.post(
            f"/api/v1/courses/{course_id}/documents",
            headers=headers,
            files={
                "file": (
                    "lesson.md",
                    "# 拥塞控制\n\n窗口机制调节发送速率。",
                    "text/markdown",
                )
            },
        )
        assert upload.status_code == 202
        drain_jobs()
        document = client.get(
            f"/api/v1/courses/{course_id}/documents", headers=headers
        ).json()[0]
        assert document["parse_status"] == "SUCCEEDED"
        version_id = document["latest_version_id"]
        chunks = client.get(
            f"/api/v1/versions/{version_id}/chunks", headers=headers
        ).json()
        assert chunks and "窗口机制" in chunks[0]["text"]
        search = client.get(
            f"/api/v1/courses/{course_id}/search",
            headers=headers,
            params={"q": "拥塞控制"},
        )
        assert search.status_code == 200 and search.json()
        ai = client.post(
            f"/api/v1/courses/{course_id}/ai-queries",
            headers=headers,
            json={"query": "什么是拥塞控制？"},
        )
        assert ai.status_code == 201 and ai.json()["status"] == "grounded"
        seed_choice(client, headers, course_id)
        blueprint = client.post(
            "/api/v1/exam-blueprints",
            headers=headers,
            params={"course_id": course_id},
            json={
                "name": "测试蓝图",
                "total_points": 5,
                "duration_minutes": 20,
                "question_types": [{"type": "single_choice", "count": 1, "points": 5}],
            },
        )
        assert blueprint.status_code == 201
        generated = client.post(
            f"/api/v1/exam-blueprints/{blueprint.json()['id']}/generate",
            headers=headers,
        )
        assert generated.status_code == 201
        paper_id = generated.json()["id"]
        public_paper = client.get(f"/api/v1/exam-papers/{paper_id}", headers=headers)
        assert public_paper.status_code == 200
        assert "answer" not in public_paper.json()["questions"][0]
