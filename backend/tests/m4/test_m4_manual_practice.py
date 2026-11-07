from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import ExamPaper
import json
from tests.m1.test_materialhub import context
from tests.m4.test_question_bank import seed_bank, start


def test_manual_search_selection_order_permissions_and_idempotency():
    with TestClient(app) as client:
        headers, course = context(client)
        source, topic = seed_bank(client, headers, course, "1. SQL 查询。\n知识标签：综合\n2. SQL 查询。\n知识标签：综合\n3. 事务恢复。\n知识标签：其他\n")
        base = f"/api/v1/courses/{course}/question-bank"
        result = client.get(base + "/practice-questions", headers=headers, params={"query": "SQL"}).json()
        assert result["total"] == 2
        filtered = client.get(base + "/practice-questions", headers=headers, params={"topic_id": topic}).json()
        assert filtered["total"] > 0
        ids = [row["id"] for row in result["items"]][::-1]
        url = base + "/manual-practice"
        payload = {"request_id": str(uuid4()), "question_ids": ids, "title": "自选练习"}
        response = client.post(url, headers=headers, json=payload)
        assert response.status_code == 201, response.text
        paper = response.json()
        with SessionLocal() as db:
            snapshot = json.loads(db.get(ExamPaper, paper["id"]).questions_json)
        assert [q["source_question_id"] for q in snapshot] == ids
        assert all("answer" not in q for q in paper["questions"])
        assert client.post(url, headers=headers, json=payload).json()["id"] == paper["id"]
        assert client.post(url, headers=headers, json=payload | {"question_ids": ids[::-1]}).status_code == 409
        assert client.post(url, headers=headers, json=payload | {"request_id": str(uuid4()), "question_ids": [ids[0], ids[0]]}).status_code == 422
        assert client.post(url, headers=headers, json=payload | {"request_id": str(uuid4()), "question_ids": [str(uuid4())]}).status_code == 422
        other, _ = context(client)
        assert client.get(base + "/practice-questions", headers=other).status_code == 404
        attempt = start(client, headers, paper)
        assert attempt["status"] == "IN_PROGRESS"
        assert client.post(url, headers=headers, json=payload).json()["id"] == paper["id"]
