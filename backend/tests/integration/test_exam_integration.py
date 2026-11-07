from tests.m4.test_question_bank import seed_choice
from datetime import timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import ExamAttempt
from app.models.base import utc_now
from tests.m1.test_materialhub import context


def test_blueprint_answer_gates_deadline_and_idempotent_submit():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, _ = context(client)
        seed_choice(client, owner, course)
        base = {
            "name": "集成蓝图",
            "total_points": 5,
            "duration_minutes": 1,
            "question_types": [{"type": "single_choice", "count": 1, "points": 5}],
            "topics": [{"name": "综合", "count": 1}],
        }
        url = f"/api/v1/exam-blueprints?course_id={course}"
        for mutation in [
            {"question_types": [{"type": "single_choice", "count": -1, "points": -5}]},
            {"question_types": [{"type": "unknown", "count": 1, "points": 5}]},
            {"topics": [{"name": "综合", "count": 2}]},
        ]:
            assert (
                client.post(url, headers=owner, json={**base, **mutation}).status_code
                == 422
            )
        blueprint = client.post(url, headers=owner, json=base).json()
        paper = client.post(
            f"/api/v1/exam-blueprints/{blueprint['id']}/generate", headers=owner
        ).json()
        qid = paper["questions"][0]["id"]
        correct = client.get(f"/api/v1/exam-papers/{paper['id']}?include_answers=true", headers=owner).json()["questions"][0]["answer"]
        wrong = next(c for c in "ABCD" if c != correct)
        client.post(f"/api/v1/exam-papers/{paper['id']}/review", headers=owner)
        attempt = client.post(
            f"/api/v1/exam-papers/{paper['id']}/attempts", headers=owner
        ).json()
        result_url = f"/api/v1/attempts/{attempt['id']}/result"
        assert client.get(result_url, headers=owner).status_code == 409
        assert (
            client.get(
                f"/api/v1/exam-papers/{paper['id']}?include_answers=true", headers=owner
            ).status_code
            == 409
        )
        path = f"/api/v1/attempts/{attempt['id']}/answers/"
        assert (
            client.put(
                path + "unknown", headers=owner, json={"answer": "A"}
            ).status_code
            == 404
        )
        assert (
            client.put(path + qid, headers=stranger, json={"answer": "A"}).status_code
            == 404
        )
        assert (
            client.put(path + qid, headers=owner, json={"answer": "Z"}).status_code
            == 422
        )
        assert (
            client.put(path + qid, headers=owner, json={"answer": wrong}).status_code
            == 200
        )
        with SessionLocal() as db:
            row = db.get(ExamAttempt, attempt["id"])
            row.created_at = utc_now() - timedelta(minutes=2)
            db.commit()
        assert (
            client.put(path + qid, headers=owner, json={"answer": "A"}).status_code
            == 409
        )
        submit = f"/api/v1/attempts/{attempt['id']}/submit"
        first = client.post(submit, headers=owner).json()
        assert first == client.post(submit, headers=owner).json()
        assert len(client.get("/api/v1/mistakes", headers=owner).json()) == 1
        assert (
            client.get(result_url, headers=owner).json()["questions"][0]["answer"]
            == correct
        )
        assert client.get(result_url, headers=stranger).status_code == 404
