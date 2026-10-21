import json
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import Mistake, ExamAttempt
from test_materialhub import context
from test_question_bank import draw, start


def seed_mistakes(c, h, course, count):
    text = "\n".join(
        f"{i + 1}. 选择第{i + 1}题。\nA.甲 B.乙 C.丙 D.丁\n答案：A\n知识标签：测试"
        for i in range(count)
    )
    p = c.post(
        f"/api/v1/courses/{course}/question-bank/import",
        headers=h,
        json={"title": "错题样本", "content": text},
    ).json()
    c.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h)
    paper = draw(c, h, course, p["questions"][0]["topic_id"], count=count)
    a = start(c, h, paper)
    c.post(f"/api/v1/attempts/{a['id']}/submit", headers=h)
    return c.get("/api/v1/mistakes", headers=h).json(), a


def test_daily_count_can_exceed_goal_without_duplicate_or_wrong_credit():
    with TestClient(app) as c:
        h, course = context(c)
        mistakes, _ = seed_mistakes(c, h, course, 3)

        def redo(mid, correct=True):
            path = f"/api/v1/mistakes/{mid}/redoes"
            record = c.post(path, headers=h, json={"request_id": str(uuid4())}).json()
            answer = "ABCD"[record["question"]["options"].index("甲" if correct else "乙")]
            assert c.post(f"{path}/{record['id']}/submit", headers=h, json={"answer": answer}).status_code == 200

        redo(mistakes[0]["id"])
        first = c.get("/api/v1/mistakes/daily-progress?goal=1", headers=h).json()
        assert first["done"] is True and first["completed"] == first["goal"] == 1
        redo(mistakes[1]["id"])
        redo(mistakes[1]["id"])
        extra = c.get("/api/v1/mistakes/daily-progress?goal=1", headers=h).json()
        assert extra["completed"] == 2 and extra["target"] == 1 and extra["done"] is True
        assert len(extra["remaining_ids"]) == 1
        redo(mistakes[1]["id"], False)
        assert c.get("/api/v1/mistakes/daily-progress?goal=1", headers=h).json()["completed"] == 1
        assert c.get("/api/v1/mistakes/daily-progress?goal=0", headers=h).json()["completed"] == 1


def test_daily_redo_shuffle_judgment_idempotency_remove_and_history():
    with TestClient(app) as c:
        h, course = context(c)
        other, _ = context(c)
        mistakes, a = seed_mistakes(c, h, course, 4)
        with SessionLocal() as db:
            original = db.get(ExamAttempt, a["id"]).snapshot_json
        assert c.get("/api/v1/mistakes/daily-progress", headers=h).json()["target"] == 3
        for i, m in enumerate(mistakes[:3]):
            mid = m["id"]
            path = f"/api/v1/mistakes/{mid}/redoes"
            req = {"request_id": str(uuid4())}
            assert c.post(path, headers=other, json=req).status_code == 404
            r = c.post(path, headers=h, json=req).json()
            assert "answer" not in r["question"]
            assert c.post(path, headers=h, json=req).json() == r
            assert c.delete(f"/api/v1/mistakes/{mid}", headers=h).status_code == 409
            url = path + "/" + r["id"] + "/submit"
            assert c.post(url, headers=h, json={"answer": ""}).status_code == 422
            # Select the original correct option after reshuffling by its content.
            correct = "ABCD"[r["question"]["options"].index("甲")]
            result = c.post(url, headers=h, json={"answer": correct})
            assert result.status_code == 200, result.text
            assert result.json()["correct"] is True
            assert c.post(url, headers=h, json={"answer": correct}).status_code == 200
            assert (
                c.post(
                    url,
                    headers=h,
                    json={"answer": "ABCD"[("ABCD".index(correct) + 1) % 4]},
                ).status_code
                == 409
            )
            if i == 0:
                again = c.post(
                    path, headers=h, json={"request_id": str(uuid4())}
                ).json()
                c.post(
                    path + "/" + again["id"] + "/submit",
                    headers=h,
                    json={"answer": "ABCD"[again["question"]["options"].index("甲")]},
                )
                assert (
                    c.get("/api/v1/mistakes/daily-progress", headers=h).json()[
                        "completed"
                    ]
                    == 1
                )
                assert c.delete(f"/api/v1/mistakes/{mid}", headers=h).status_code == 200
        daily = c.get("/api/v1/mistakes/daily-progress", headers=h).json()
        assert (
            daily["done"] is True and daily["completed"] == 3 and daily["target"] == 3
        )
        assert len(c.get("/api/v1/mistakes", headers=h).json()) == 3
        with SessionLocal() as db:
            assert db.get(ExamAttempt, a["id"]).snapshot_json == original


def test_fewer_than_three_manual_redo_and_next_day(monkeypatch):
    from app.services import question_bank as bank

    with TestClient(app) as c:
        h, course = context(c)
        mistakes, _ = seed_mistakes(c, h, course, 1)
        mid = mistakes[0]["id"]
        with SessionLocal() as db:
            m = db.get(Mistake, mid)
            data = json.loads(m.detail_json)
            data["question"].update(type="solution", answer=None)
            m.detail_json = json.dumps(data)
            db.commit()
        fixed = datetime(2026, 10, 21, 15, 59, tzinfo=timezone.utc)
        monkeypatch.setattr(bank, "utc_now", lambda: fixed)
        r = c.post(
            f"/api/v1/mistakes/{mid}/redoes",
            headers=h,
            json={"request_id": str(uuid4())},
        ).json()
        url = f"/api/v1/mistakes/{mid}/redoes/{r['id']}"
        c.post(url + "/submit", headers=h, json={"answer": "自己的解答"})
        assert (
            c.get("/api/v1/mistakes/daily-progress", headers=h).json()["completed"] == 0
        )
        assert (
            c.post(url + "/judge", headers=h, json={"correct": False}).status_code
            == 200
        )
        assert (
            c.get("/api/v1/mistakes/daily-progress", headers=h).json()["done"] is False
        )
        assert c.delete(f"/api/v1/mistakes/{mid}", headers=h).status_code == 409
        monkeypatch.setattr(bank, "utc_now", lambda: fixed + timedelta(minutes=2))
        assert (
            c.get("/api/v1/mistakes/daily-progress", headers=h).json()["completed"] == 0
        )
        assert c.get("/api/v1/mistakes/daily-progress", headers=h).json()["target"] == 1
        retry = c.post(
            f"/api/v1/mistakes/{mid}/redoes", headers=h,
            json={"request_id": str(uuid4())},
        ).json()
        retry_url = f"/api/v1/mistakes/{mid}/redoes/{retry['id']}"
        c.post(retry_url + "/submit", headers=h, json={"answer": "修正解答"})
        c.post(retry_url + "/judge", headers=h, json={"correct": True})
        progress = c.get("/api/v1/mistakes/daily-progress", headers=h).json()
        assert progress["completed"] == 1 and progress["done"] is True
        monkeypatch.setattr(bank, "utc_now", lambda: fixed + timedelta(days=1, minutes=2))
        progress = c.get("/api/v1/mistakes/daily-progress", headers=h).json()
        assert progress["completed"] == progress["target"] == progress["available"] == 0
        assert progress["done"] is True


def test_wrong_not_counted_mastered_excluded_and_unmastered_sorted_first(monkeypatch):
    from app.services import question_bank as bank

    fixed = datetime(2026, 10, 20, 15, 59, tzinfo=timezone.utc)
    monkeypatch.setattr(bank, "utc_now", lambda: fixed)
    with TestClient(app) as c:
        h, course = context(c)
        mistakes, _ = seed_mistakes(c, h, course, 3)

        def redo(mid, correct):
            record = c.post(f"/api/v1/mistakes/{mid}/redoes", headers=h,
                            json={"request_id": str(uuid4())}).json()
            option = "甲" if correct else "乙"
            answer = "ABCD"[record["question"]["options"].index(option)]
            return c.post(f"/api/v1/mistakes/{mid}/redoes/{record['id']}/submit",
                          headers=h, json={"answer": answer})

        mastered, pending, untouched = [m["id"] for m in mistakes]
        assert redo(mastered, True).json()["correct"] is True
        # Next local day: retained mastery must not count or contribute to target.
        monkeypatch.setattr(bank, "utc_now", lambda: fixed + timedelta(minutes=2))
        progress = c.get("/api/v1/mistakes/daily-progress", headers=h).json()
        assert progress["target"] == progress["available"] == 2
        assert progress["completed"] == 0 and mastered not in progress["remaining_ids"]
        assert redo(mastered, True).status_code == 200
        assert redo(pending, False).json()["correct"] is False
        progress = c.get("/api/v1/mistakes/daily-progress", headers=h).json()
        assert progress["completed"] == 0 and progress["done"] is False
        assert set(progress["remaining_ids"]) == {pending, untouched}
        assert redo(pending, True).status_code == 200
        assert redo(pending, True).status_code == 200
        progress = c.get("/api/v1/mistakes/daily-progress", headers=h).json()
        assert progress["completed"] == 1 and progress["target"] == 2
        assert progress["available"] == 1 and progress["remaining_ids"] == [untouched]
        rows = c.get("/api/v1/mistakes", headers=h).json()
        assert rows[0]["id"] == untouched and rows[0]["mastered"] is False
        assert all(m["mastered"] and m["mastered_at"] for m in rows[1:])
        assert all("redoes" not in m for m in rows)


def test_redo_and_removal_roundtrip_backup():
    from test_account_backups import exported, restored, empty_account
    from app.models import User

    with TestClient(app) as c:
        h, course = context(c)
        mistakes, _ = seed_mistakes(c, h, course, 1)
        mid = mistakes[0]["id"]
        r = c.post(
            f"/api/v1/mistakes/{mid}/redoes",
            headers=h,
            json={"request_id": str(uuid4())},
        ).json()
        correct = "ABCD"[r["question"]["options"].index("甲")]
        c.post(
            f"/api/v1/mistakes/{mid}/redoes/{r['id']}/submit",
            headers=h,
            json={"answer": correct},
        )
        c.delete(f"/api/v1/mistakes/{mid}", headers=h)
        uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        raw, _ = exported(c, h)
        with SessionLocal() as db:
            db.delete(db.get(User, uid))
            db.commit()
        destination, _ = empty_account(c)
        result = restored(c, destination, raw)
        assert result["job"]["status"] == "SUCCEEDED", result
        assert c.get("/api/v1/mistakes", headers=destination).json() == []
        assert (
            c.get("/api/v1/mistakes/daily-progress", headers=destination).json()[
                "completed"
            ]
            == 1
        )


def test_custom_goal_and_wrong_again_reopens_removed_mistake(monkeypatch):
    from app.services import question_bank as bank

    # Identical timestamps still preserve the actual sequence of judgments.
    fixed = datetime(2026, 10, 21, 6, tzinfo=timezone.utc)
    monkeypatch.setattr(bank, "utc_now", lambda: fixed)
    with TestClient(app) as c:
        h, course = context(c)
        mistakes, _ = seed_mistakes(c, h, course, 1)
        mid = mistakes[0]["id"]

        def redo(correct):
            path = f"/api/v1/mistakes/{mid}/redoes"
            record = c.post(path, headers=h, json={"request_id": str(uuid4())}).json()
            answer = "ABCD"[record["question"]["options"].index("甲" if correct else "乙")]
            return c.post(f"{path}/{record['id']}/submit", headers=h, json={"answer": answer})

        assert c.get("/api/v1/mistakes/daily-progress?goal=-1", headers=h).status_code == 422
        assert c.get("/api/v1/mistakes/daily-progress?goal=1001", headers=h).status_code == 422
        paused = c.get("/api/v1/mistakes/daily-progress?goal=0", headers=h).json()
        assert paused["target"] == 0 and paused["done"] is True
        assert redo(True).json()["correct"] is True
        assert c.delete(f"/api/v1/mistakes/{mid}", headers=h).status_code == 200
        paper = c.post(f"/api/v1/courses/{course}/question-bank/draw", headers=h,
                       json={"request_id": str(uuid4()), "topic_ids": [], "count": 1}).json()
        attempt = start(c, h, paper)
        path = f"/api/v1/attempts/{attempt['id']}/submit"
        assert c.post(path, headers=h).status_code == 200
        assert c.post(path, headers=h).status_code == 200
        rows = c.get("/api/v1/mistakes", headers=h).json()
        assert len(rows) == 1 and rows[0]["id"] == mid and rows[0]["mastered"] is False
        progress = c.get("/api/v1/mistakes/daily-progress?goal=7", headers=h).json()
        assert progress["goal"] == 7 and progress["target"] == 1 and progress["completed"] == 0
        with SessionLocal() as db:
            data = json.loads(db.get(Mistake, mid).detail_json)
            assert data["removed_from_bank"] is False and len(data["relapses"]) == 1
        assert redo(True).json()["correct"] is True
        assert c.get("/api/v1/mistakes/daily-progress", headers=h).json()["completed"] == 1
        assert redo(False).json()["correct"] is False
        progress = c.get("/api/v1/mistakes/daily-progress", headers=h).json()
        assert progress["completed"] == 0 and progress["remaining_ids"] == [mid]
        assert c.delete(f"/api/v1/mistakes/{mid}", headers=h).status_code == 409
        assert redo(True).json()["correct"] is True
        assert c.get("/api/v1/mistakes/daily-progress", headers=h).json()["completed"] == 1

        from test_account_backups import exported, restored, empty_account
        from app.models import User

        uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        raw, _ = exported(c, h)
        with SessionLocal() as db:
            db.delete(db.get(User, uid))
            db.commit()
        destination, _ = empty_account(c)
        result = restored(c, destination, raw)
        assert result["job"]["status"] == "SUCCEEDED", result
        rows = c.get("/api/v1/mistakes", headers=destination).json()
        assert len(rows) == 1 and rows[0]["mastered"] is True
