from fastapi.testclient import TestClient
from app.main import app
from tests.m1.test_materialhub import context


def test_review_across_pages_and_repeated_save_preserves_confirmed_papers():
    with TestClient(app) as c:
        h, course = context(c)
        base = f"/api/v1/courses/{course}/question-bank"
        papers = [
            c.post(
                base + "/import",
                headers=h,
                json={
                    "title": f"题库{n}",
                    "content": "\n".join(
                        f"{i}. 解释问题{i}。" for i in range(1, size + 1)
                    ),
                },
            ).json()
            for n, size in enumerate((53, 1))
        ]

        def statuses():
            return {
                p["id"]: p["status"]
                for p in c.get(
                    f"/api/v1/courses/{course}/question-bank/papers", headers=h
                ).json()
            }

        def batch(rows, action="confirm", topics=None):
            return c.post(
                base + "/batch",
                headers=h,
                json={
                    "question_ids": [q["id"] for q in rows],
                    "revisions": {q["id"]: q["revision"] for q in rows},
                    "action": action,
                    "topic_ids": topics or [],
                },
            )

        first = papers[0]["questions"]
        assert batch(first[:50]).status_code == 200
        assert statuses()[papers[0]["id"]] == "DRAFT"
        assert batch(first[50:] + papers[1]["questions"]).status_code == 200
        assert set(statuses().values()) == {"CONFIRMED"}
        rows = c.get(base + "?limit=100", headers=h).json()["items"]
        items = [
            {
                "question_id": q["id"],
                "revision": q["revision"],
                "stem": q["stem"],
                "question_type": q["question_type"],
                "topic_ids": q["bank_data"]["topic_ids"],
            }
            for q in rows
        ]
        response = c.post(base + "/save", headers=h, json={"items": items})
        assert response.status_code == 200, response.text
        assert set(statuses().values()) == {"CONFIRMED"}
        rows = c.get(base + "?limit=100", headers=h).json()["items"]
        assert all(q["status"] == "CONFIRMED" for q in rows)
        q = rows[0]
        changed = c.patch(
            f"/api/v1/past-questions/{q['id']}",
            headers=h,
            json={
                "revision": q["revision"],
                "stem": q["stem"] + "补充条件。",
                "question_type": q["question_type"],
                "topic_ids": q["bank_data"]["topic_ids"],
            },
        ).json()
        assert statuses()[q["paper_id"]] == "DRAFT"
        assert batch([changed]).status_code == 200
        assert set(statuses().values()) == {"CONFIRMED"}


def test_batch_tag_add_replace_and_overflow_are_atomic():
    with TestClient(app) as c:
        h, course = context(c)
        base = f"/api/v1/courses/{course}/question-bank"
        topic_ids = [
            c.post(
                f"/api/v1/courses/{course}/topics", headers=h, json={"name": f"标签{i}"}
            ).json()["id"]
            for i in range(6)
        ]
        imported = c.post(
            base + "/import",
            headers=h,
            json={
                "title": "标签动作",
                "content": "1. 问题甲。\n2. 问题乙。",
                "default_topic_ids": topic_ids[:1],
            },
        )
        assert imported.status_code == 201

        def rows():
            return c.get(base, headers=h).json()["items"]

        def change(action, ids, selected=None):
            selected = rows() if selected is None else selected
            return c.post(
                base + "/batch",
                headers=h,
                json={
                    "question_ids": [q["id"] for q in selected],
                    "revisions": {q["id"]: q["revision"] for q in selected},
                    "action": action,
                    "topic_ids": ids,
                },
            )

        assert change("tag_add", topic_ids[1:2]).status_code == 200
        assert all(q["bank_data"]["topic_ids"] == topic_ids[:2] for q in rows())
        assert change("tag_add", topic_ids[1:2]).status_code == 200
        assert all(q["bank_data"]["topic_ids"] == topic_ids[:2] for q in rows())
        assert change("tag", topic_ids[2:3]).status_code == 200
        assert all(q["bank_data"]["topic_ids"] == topic_ids[2:3] for q in rows())
        assert all(q["bank_data"]["topic_index"]["selection_reviewed"] for q in rows())
        assert change("tag", topic_ids[:5], rows()[1:]).status_code == 200
        before = rows()
        response = change("tag_add", topic_ids[5:])
        assert response.status_code == 422
        overflow = response.json()["error"]["details"]["over_limit_questions"]
        assert len(overflow) == 1
        assert overflow[0] == {
            "question_id": before[1]["id"],
            "paper_id": before[1]["paper_id"],
            "paper_title": "标签动作",
            "number": before[1]["number"],
            "tag_count": 6,
            "limit": 5,
        }
        assert rows() == before
        assert change("tag", topic_ids[:5]).status_code == 200
        before = rows()
        response = change("tag_add", topic_ids[5:])
        assert response.status_code == 422
        assert {
            v["question_id"]
            for v in response.json()["error"]["details"]["over_limit_questions"]
        } == {q["id"] for q in before}
        assert rows() == before
        other, _ = context(c)
        response = c.post(
            base + "/batch",
            headers=other,
            json={
                "question_ids": [before[0]["id"]],
                "revisions": {before[0]["id"]: before[0]["revision"]},
                "action": "tag_add",
                "topic_ids": topic_ids[:1],
            },
        )
        assert response.status_code == 404
