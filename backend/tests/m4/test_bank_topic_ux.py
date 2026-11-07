from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import Mistake
from tests.m1.test_materialhub import context
from tests.m4.test_question_bank import seed_choice, draw, start


def test_batch_confirm_atomic_revision_and_filtered_list():
    with TestClient(app) as c:
        h, course = context(c)
        p = c.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "核验",
                "content": "1. 解释缓存。\n知识标签：缓存\n2. 选一个。\nA.甲 B.乙 C.丙 D.丙\n知识标签：缓存",
            },
        ).json()
        ids = [q["id"] for q in p["questions"]]
        revisions = {q["id"]: q["revision"] for q in p["questions"]}
        url = f"/api/v1/courses/{course}/question-bank/batch"
        payload = {"question_ids": ids, "revisions": revisions, "action": "confirm"}
        assert c.post(url, headers=h, json=payload).status_code == 422
        listed = c.get(f"/api/v1/courses/{course}/question-bank", headers=h).json()
        assert all(q["status"] == "DRAFT" for q in listed["items"])
        payload["question_ids"] = [ids[0]]
        assert c.post(url, headers=h, json=payload).status_code == 200
        assert c.post(url, headers=h, json=payload).status_code == 409
        q = p["questions"][1]
        edit = {
            "revision": q["revision"],
            "stem": q["stem"],
            "question_type": "single_choice",
            "options": ["甲", "乙", "丙", "丁"],
            "answer": "A",
            "topic_ids": q["bank_data"]["topic_ids"],
        }
        saved = c.patch(
            f"/api/v1/past-questions/{q['id']}", headers=h, json=edit
        ).json()
        payload["question_ids"] = [q["id"]]
        payload["revisions"] = {q["id"]: saved["revision"]}
        assert c.post(url, headers=h, json=payload).status_code == 200
        topic = q["bank_data"]["topic_ids"][0]
        result = c.get(
            f"/api/v1/courses/{course}/question-bank?topic_id={topic}&limit=1&offset=1",
            headers=h,
        ).json()
        assert result["total"] == 2 and len(result["items"]) == 1
        assert (
            c.get(
                f"/api/v1/courses/{course}/question-bank/statistics", headers=h
            ).json()["eligible_questions"]
            == 2
        )
        other, _ = context(c)
        assert c.post(url, headers=other, json=payload).status_code == 404


def test_mistake_labels_resolve_rename_merge_and_owner_without_snapshot_write():
    with TestClient(app) as c:
        h, course = context(c)
        _, tid = seed_choice(c, h, course)
        paper = draw(c, h, course, tid, count=1)
        attempt = start(c, h, paper)
        assert (
            c.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=h).status_code
            == 200
        )
        with SessionLocal() as db:
            before = (
                db.query(Mistake)
                .filter(Mistake.attempt_id == attempt["id"])
                .one()
                .detail_json
            )
        topics = c.get(f"/api/v1/courses/{course}/topics", headers=h).json()
        source = next(t for t in topics if t["id"] == tid)
        target = c.post(
            f"/api/v1/courses/{course}/topics",
            headers=h,
            json={"name": "传输层", "aliases": ["TCP"]},
        ).json()
        assert (
            c.post(
                f"/api/v1/topics/{tid}/merge",
                headers=h,
                json={
                    "revision": source["revision"],
                    "target_id": target["id"],
                    "target_revision": target["revision"],
                },
            ).status_code
            == 200
        )
        result = c.get(f"/api/v1/mistakes?topic_id={target['id']}", headers=h).json()
        assert len(result) == 1 and result[0]["topics"][0]["name"] == "传输层"
        assert result[0]["question"]["topic_ids"] == [tid]
        assert c.get(f"/api/v1/mistakes?topic_id={tid}", headers=h).json() == []
        other, _ = context(c)
        assert c.get("/api/v1/mistakes", headers=other).json() == []
        with SessionLocal() as db:
            assert (
                db.query(Mistake)
                .filter(Mistake.attempt_id == attempt["id"])
                .one()
                .detail_json
                == before
            )


def test_draw_optional_topics_union_many_and_course_isolation():
    from uuid import uuid4

    with TestClient(app) as c:
        h, course = context(c)
        p = c.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "范围",
                "content": "1. 解释缓存。\n知识标签：缓存\n2. 解释总线。\n知识标签：总线",
            },
        ).json()
        assert (
            c.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h).status_code
            == 200
        )
        tids = [q["bank_data"]["topic_ids"][0] for q in p["questions"]]

        def call(topics=None, count=2):
            data = {"request_id": str(uuid4()), "count": count}
            if topics is not None:
                data["topic_ids"] = topics
            return c.post(
                f"/api/v1/courses/{course}/question-bank/draw", headers=h, json=data
            )

        for selected in (None, [], tids):
            response = call(selected)
            assert response.status_code == 201, response.text
            assert len(response.json()["questions"]) == 2
        result = call([tids[0]], 1)
        assert result.status_code == 201
        assert result.json()["questions"][0]["topic_ids"] == [tids[0]]
        assert call([tids[0]], 2).status_code == 422
        for i in range(13):
            t = c.post(
                f"/api/v1/courses/{course}/topics", headers=h, json={"name": f"额外{i}"}
            ).json()
            tids.append(t["id"])
        assert call(tids).status_code == 201
        other = c.post("/api/v1/courses", headers=h, json={"name": "另一门课"}).json()[
            "id"
        ]
        foreign = c.post(
            f"/api/v1/courses/{other}/topics", headers=h, json={"name": "隔离标签"}
        ).json()["id"]
        assert call([foreign], 1).status_code == 404
        assert len(call([]).json()["questions"]) == 2
