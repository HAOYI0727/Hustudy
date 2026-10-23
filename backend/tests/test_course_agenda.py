"""Course agenda: exact SQL paging, safe scope, timezone and zero learning writes."""

from datetime import datetime, timezone
import json
from sqlalchemy import event, select
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine
from app.models import ReviewTask, User, Course, Mistake, ExamAttempt
from app.services import review_schedule
from test_material_organization import setup_course, import_document
from test_learning_workspace import snapshot


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 24, 0, 30, tzinfo=timezone.utc).astimezone(tz)


def seed(client):
    owner, course = setup_course(client)
    uid = client.get("/api/v1/auth/me", headers=owner).json()["id"]
    _, version = import_document(client, owner, course, "# 复习\n可核对原文。")
    chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[0]
    attempt, mistake = snapshot(uid, course, version, chunk)
    return owner, uid, course, version, chunk, attempt, mistake


def test_course_agenda_counts_exact_paging_projection_and_no_writes(monkeypatch):
    monkeypatch.setattr(review_schedule, "datetime", FixedDateTime)
    with TestClient(app) as client:
        owner, uid, course, _, _, attempt, mistake = seed(client)
        with SessionLocal() as db:
            db.get(User, uid).timezone = "Asia/Shanghai"
            for i, (due, status) in enumerate(
                [("2026-10-24", "PENDING")] * 13
                + [("2026-10-23", "PENDING")] * 2
                + [("2026-10-25", "PENDING")] * 4
                + [("2026-10-24", "COMPLETED")] * 3
            ):
                db.add(
                    ReviewTask(
                        user_id=uid,
                        mistake_id=mistake,
                        title=f"日程{i}",
                        due_date=due,
                        status=status,
                    )
                )
            db.add(ReviewTask(user_id=uid, title="旧独立计划", due_date="2026-10-24"))
            db.commit()
            frozen = (
                db.get(Mistake, mistake).detail_json,
                db.get(ExamAttempt, attempt).answers_json,
            )
        statements = []

        def capture(conn, cursor, statement, parameters, context, many):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", capture)
        try:
            response = client.get(
                f"/api/v1/review-tasks?course_id={course}&limit=6", headers=owner
            )
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["counts"] == dict(
            pending=19, due=15, overdue=2, today=13, upcoming=4, completed=3
        )
        assert data["total"] == 19 and len(data["items"]) == 6
        assert data["course_id"] == course and data["timezone"] == "Asia/Shanghai"
        assert data["today"] == "2026-10-24"
        assert set(data["items"][0]) == {
            "id",
            "mistake_id",
            "title",
            "due_date",
            "status",
        }
        assert not any(
            word in response.text for word in ("私有题干", "标准答案", "不能泄露")
        )
        selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
        assert (
            len(selects) <= 5
        )  # auth/course + aggregate/count/page, independent of list length
        assert not any(
            s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
            for s in statements
        )
        rows = []
        for offset in (0, 6, 12, 18):
            rows += client.get(
                f"/api/v1/review-tasks?course_id={course}&limit=6&offset={offset}",
                headers=owner,
            ).json()["items"]
        assert len(rows) == len({x["id"] for x in rows}) == 19
        assert rows == sorted(rows, key=lambda x: (x["due_date"], x["id"]))
        for period, count in (
            ("due", 15),
            ("today", 13),
            ("overdue", 2),
            ("upcoming", 4),
        ):
            page = client.get(
                f"/api/v1/review-tasks?course_id={course}&period={period}",
                headers=owner,
            ).json()
            assert page["total"] == count and page["counts"] == data["counts"]
        assert (
            client.get(
                f"/api/v1/review-tasks?course_id={course}&state=completed",
                headers=owner,
            ).json()["total"]
            == 3
        )
        assert (
            client.get("/api/v1/review-tasks?state=all", headers=owner).json()["total"]
            == 23
        )
        with SessionLocal() as db:
            assert frozen == (
                db.get(Mistake, mistake).detail_json,
                db.get(ExamAttempt, attempt).answers_json,
            )
            assert (
                len(
                    db.scalars(
                        select(ReviewTask).where(
                            ReviewTask.user_id == uid, ReviewTask.status == "PENDING"
                        )
                    ).all()
                )
                == 20
            )


def test_course_agenda_scope_removed_foreign_chain_and_deleted_course():
    with TestClient(app) as client:
        owner, uid, course, version, chunk, _, mistake = seed(client)
        other_course = client.post(
            "/api/v1/courses", headers=owner, json={"name": "其他课程"}
        ).json()["id"]
        _, other_mistake = snapshot(uid, other_course, version, chunk)
        foreign, foreign_uid, foreign_course, _, _, _, foreign_mistake = seed(client)
        with SessionLocal() as db:
            for mid, title in (
                (mistake, "本人日程"),
                (other_mistake, "其他课程日程"),
                (foreign_mistake, "禁止泄漏"),
            ):
                db.add(
                    ReviewTask(
                        user_id=uid, mistake_id=mid, title=title, due_date="2026-10-24"
                    )
                )
            db.add(
                ReviewTask(
                    user_id=foreign_uid,
                    mistake_id=mistake,
                    title="其他账号计划",
                    due_date="2026-10-24",
                )
            )
            db.commit()
        url = f"/api/v1/review-tasks?course_id={course}&state=all"
        assert client.get(url, headers=owner).json()["total"] == 1
        assert client.get(url, headers=foreign).status_code == 404
        assert (
            client.get(
                f"/api/v1/review-tasks?course_id={foreign_course}", headers=owner
            ).status_code
            == 404
        )
        assert client.get("/api/v1/review-tasks", headers=owner).json()["total"] == 2
        with SessionLocal() as db:
            row = db.get(Mistake, mistake)
            value = json.loads(row.detail_json)
            value["removed_from_bank"] = True
            row.detail_json = json.dumps(value)
            db.commit()
        assert client.get(url, headers=owner).json()["total"] == 0
        with SessionLocal() as db:
            db.get(Course, course).deleted_at = datetime.now(timezone.utc)
            db.commit()
        assert client.get(url, headers=owner).status_code == 404


def test_course_agenda_literal_search_validation_and_empty_counts():
    with TestClient(app) as client:
        owner, uid, course, _, _, _, mistake = seed(client)
        with SessionLocal() as db:
            for title in ("复习100%_TCP", "复习100xxTCP", "tcp网络"):
                db.add(
                    ReviewTask(
                        user_id=uid,
                        mistake_id=mistake,
                        title=title,
                        due_date="2026-10-24",
                    )
                )
            db.commit()
        url = f"/api/v1/review-tasks?course_id={course}"
        assert (
            client.get(url, headers=owner, params={"q": "100%_"}).json()["total"] == 1
        )
        assert client.get(url, headers=owner, params={"q": "TCP"}).json()["total"] == 3
        missing = client.get(url, headers=owner, params={"q": "不存在"}).json()
        assert missing["items"] == [] and missing["total"] == 0
        assert all(x == 0 for x in missing["counts"].values())
        for params in (
            {"period": "invalid"},
            {"state": "invalid"},
            {"q": "x" * 201},
            {"offset": 1000001},
            {"limit": 101},
        ):
            assert client.get(url, headers=owner, params=params).status_code == 422


def test_course_agenda_uses_account_day_at_timezone_boundary(monkeypatch):
    monkeypatch.setattr(review_schedule, "datetime", FixedDateTime)
    with TestClient(app) as client:
        owner, uid, course, _, _, _, mistake = seed(client)
        with SessionLocal() as db:
            db.get(User, uid).timezone = "Pacific/Honolulu"
            db.add(
                ReviewTask(
                    user_id=uid,
                    mistake_id=mistake,
                    title="跨日复习",
                    due_date="2026-10-23",
                )
            )
            db.commit()
        url = f"/api/v1/review-tasks?course_id={course}&period=today"
        page = client.get(url, headers=owner).json()
        assert page["today"] == "2026-10-23" and page["total"] == 1
        with SessionLocal() as db:
            db.get(User, uid).timezone = "Pacific/Kiritimati"
            db.commit()
        page = client.get(url, headers=owner).json()
        assert page["today"] == "2026-10-24" and page["total"] == 0
        assert page["counts"]["overdue"] == 1
