from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import PastQuestion
from app.services.question_display import display_group
from test_materialhub import context
from test_question_bank import seed_bank, start
from uuid import uuid4


def test_explicit_chinese_and_numeric_group_numbers_and_unknowns():
    assert display_group("第十二大题（3）", "paper")["order"] == [12, 3]
    assert display_group("一.10", "paper")["order"] == [1, 10]
    assert display_group("１－２", "paper")["order"] == [1, 2]
    assert display_group("1.2", "paper")["key"] != display_group("1.2", "other")["key"]
    assert display_group("unknown", "paper") is None


def test_display_order_and_snapshot_preserve_individual_types_and_answer_boundary():
    with TestClient(app) as c:
        h, course = context(c)
        paper, _ = seed_bank(c, h, course)
        with SessionLocal() as db:
            for q, number in zip(paper["questions"], ["二.2", "一.10", "一.2", "二.1"]):
                db.get(PastQuestion, q["id"]).number = number
            db.commit()
        rows = c.get(f"/api/v1/courses/{course}/question-bank", headers=h).json()[
            "items"
        ]
        assert [q["number"] for q in rows] == ["一.2", "一.10", "二.1", "二.2"]
        assert rows[0]["display_group"]["key"] == rows[1]["display_group"]["key"]
        assert rows[2]["display_group"]["key"] != rows[0]["display_group"]["key"]
        assert len({q["id"] for q in rows}) == 4
        drawn = c.post(
            f"/api/v1/courses/{course}/question-bank/draw",
            headers=h,
            json={"request_id": str(uuid4()), "topic_ids": [], "count": 4},
        ).json()
        assert len(drawn["questions"]) == 4
        assert {q["type"] for q in drawn["questions"]} == {
            "single_choice",
            "solution",
        }
        assert all(
            q["display_group"] and "answer" not in q and "explanation" not in q
            for q in drawn["questions"]
        )
        attempt = start(c, h, drawn)
        c.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=h)
        result = c.get(f"/api/v1/attempts/{attempt['id']}/result", headers=h).json()
        assert all("answer" in q and "explanation" in q for q in result["questions"])
