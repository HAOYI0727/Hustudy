from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from test_materialhub import context


def test_batch_save_rolls_back_conflict_scope_images_and_preserves_unselected():
    with TestClient(app) as c:
        h, course = context(c)
        p = c.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "批量校正",
                "content": "1. 第一题。\n2. 第二题。\n3. 不改第三题。",
            },
        ).json()
        qs = p["questions"]

        def item(i):
            return {
                "question_id": qs[i]["id"],
                "revision": qs[i]["revision"],
                "stem": f"校正第{i + 1}题。",
                "question_type": "solution",
                "topic_ids": [],
            }

        a, b = item(0), item(1)
        url = f"/api/v1/courses/{course}/question-bank/save"

        def current():
            return c.get(f"/api/v1/courses/{course}/question-bank", headers=h).json()[
                "items"
            ]

        before = current()
        assert (
            c.post(
                url, headers=h, json={"items": [a, b | {"revision": 99}]}
            ).status_code
            == 409
        )
        assert current() == before
        assert c.post(
            url,
            headers=h,
            json={"items": [a, b | {"illustrations": [{"asset_id": str(uuid4())}]}]},
        ).status_code in (404, 422)
        assert current() == before
        assert c.post(url, headers=h, json={"items": [a, a]}).status_code == 422
        other, other_course = context(c)
        assert c.post(url, headers=other, json={"items": [a]}).status_code == 404
        assert (
            c.post(
                f"/api/v1/courses/{other_course}/question-bank/save",
                headers=h,
                json={"items": [a]},
            ).status_code
            == 404
        )
        another = c.post(
            "/api/v1/courses", headers=h, json={"name": "另一课程"}
        ).json()["id"]
        foreign = c.post(
            f"/api/v1/courses/{another}/question-bank/import",
            headers=h,
            json={"title": "跨课程", "content": "1. 不应被改。"},
        ).json()["questions"][0]
        cross = b | {"question_id": foreign["id"], "revision": foreign["revision"]}
        assert c.post(url, headers=h, json={"items": [a, cross]}).status_code == 404
        assert current() == before
        result = c.post(url, headers=h, json={"items": [a, b]})
        assert result.status_code == 200, result.text
        assert result.json()["changed"] == 2
        rows = {q["id"]: q for q in current()}
        for i in (0, 1):
            assert rows[qs[i]["id"]]["stem"] == f"校正第{i + 1}题。"
            assert rows[qs[i]["id"]]["revision"] == qs[i]["revision"] + 1
            assert rows[qs[i]["id"]]["status"] == "DRAFT"
        assert rows[qs[2]["id"]] == next(q for q in before if q["id"] == qs[2]["id"])
        assert c.post(url, headers=h, json={"items": [a, b]}).status_code == 409
