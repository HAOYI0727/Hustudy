"""Original-source review links preserve frozen attempts and current M4 semantics."""

import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from sqlalchemy import event
from app.main import app
from app.core.database import SessionLocal, engine
from app.models import Mistake, ReviewTask, User
from tests.shared.test_learning_workspace import snapshot
from tests.integration.test_source_learning import setup, endpoint
from tests.m1.test_material_organization import setup_course
from tests.m1.test_preview_assets import import_pdf
from tests.m1.test_manual_transcripts import draft, confirm


def make(uid, course, version, citation, **extra):
    _, mid = snapshot(uid, course, version, {"id": citation["chunk_id"]})
    with SessionLocal() as db:
        m = db.get(Mistake, mid)
        m.detail_json = json.dumps(
            {
                "question": {
                    "stem": "私有题干不可投影",
                    "answer": "标准答案不可投影",
                    "source_version_id": version,
                    "citations": [citation],
                },
                **extra,
            }
        )
        db.commit()
    return mid


def change(mid, **values):
    with SessionLocal() as db:
        row = db.get(Mistake, mid)
        data = json.loads(row.detail_json)
        data.update(values)
        row.detail_json = json.dumps(data)
        db.commit()


def fetch(c, h, version, **params):
    response = c.get(endpoint(version), headers=h, params={"kind": "mistake", **params})
    assert response.status_code == 200, response.status_code
    return response.json()


def test_exact_sources_and_explicit_version_only_fallback_no_body_projection_or_writes():
    with TestClient(app) as c:
        h, course, uid, doc, version, citations = setup(c)
        exact = make(uid, course, version, citations[0])
        fallback = make(uid, course, version, citations[0])
        change(fallback, question={"source_version_id": version})
        for bad in (
            [{**citations[0], "quote": "假引用"}],
            {},
            None,
            ["legacy"],
            [{**citations[0], "quote": 1}],
        ):
            mid = make(uid, course, version, citations[0])
            change(mid, question={"source_version_id": version, "citations": bad})
        removed = make(uid, course, version, citations[0], removed_from_bank=True)
        other_h, other_course = setup_course(c)
        foreign_uid = c.get("/api/v1/auth/me", headers=other_h).json()["id"]
        make(foreign_uid, other_course, version, citations[0])
        own_other = c.post(
            "/api/v1/courses", headers=h, json={"name": "另一门课"}
        ).json()["id"]
        make(uid, own_other, version, citations[0])
        sql = []

        def capture(_c, _cursor, statement, _params, _context, _many):
            sql.append(statement.lower())

        event.listen(engine, "before_cursor_execute", capture)
        try:
            page = fetch(c, h, version)
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert page["total"] == 2 and page["counts"]["mistake"] == 2
        rows = {row["id"]: row for row in page["items"]}
        assert set(rows) == {exact, fallback} and removed not in rows
        assert rows[exact]["source_relation"] == "citation"
        assert rows[fallback]["source_relation"] == "version"
        assert rows[exact]["review"] == dict(
            mastered=False, pending_count=0, due_count=0, next_due_date=None
        )
        assert fetch(c, h, version, chunk_id=citations[0]["chunk_id"])["total"] == 1
        assert fetch(c, h, version, chunk_id=citations[1]["chunk_id"])["total"] == 0
        response = json.dumps(page, ensure_ascii=False)
        assert not any(
            secret in response
            for secret in ("私有题干", "标准答案", "quote", "redoes", "relapses")
        )
        assert not any(
            re.match(r"\s*(insert|update|delete|replace)\b", statement)
            for statement in sql
        )
        projection = "\n".join(
            re.findall(r"\bselect\b(.*?)\bfrom\b", "\n".join(sql), re.S)
        )
        assert not re.search(r"select\s+mistakes\.detail_json", "\n".join(sql))
        for forbidden in (
            "$.question.stem",
            "$.answer",
            "$.grading",
            "$.redoes.question",
        ):
            assert forbidden not in projection
        assert c.get(endpoint(version), headers=other_h).status_code == 404


def test_review_dates_timezone_mastery_recurrence_and_owner_are_independent():
    with TestClient(app) as c:
        h, course, uid, doc, version, citations = setup(c)
        foreign, _ = setup_course(c)
        foreign_uid = c.get("/api/v1/auth/me", headers=foreign).json()["id"]
        mid = make(uid, course, version, citations[0])
        today = datetime.now(ZoneInfo("Pacific/Honolulu")).date()
        with SessionLocal() as db:
            db.get(User, uid).timezone = "Pacific/Honolulu"
            plans = [
                ReviewTask(
                    user_id=uid,
                    mistake_id=mid,
                    title="私人计划标题不投影",
                    due_date=(today + timedelta(days=delta)).isoformat(),
                    status=status,
                )
                for delta, status in [
                    (-1, "PENDING"),
                    (0, "PENDING"),
                    (1, "PENDING"),
                    (-2, "COMPLETED"),
                ]
            ]
            db.add_all(plans)
            db.add(
                ReviewTask(
                    user_id=foreign_uid,
                    mistake_id=mid,
                    title="他人计划",
                    due_date="2000-01-01",
                )
            )
            db.add(ReviewTask(user_id=uid, title="非关联计划", due_date="2000-01-01"))
            db.commit()
            pending_ids = [p.id for p in plans if p.status == "PENDING"]
        change(
            mid,
            redoes={
                "good": dict(
                    status="COMPLETED",
                    correct=True,
                    completed_at="2026-01-01T00:00:00+00:00",
                    sequence=1,
                    answer="不投影的重做答案",
                    question={"answer": "私有标准答案"},
                )
            },
        )
        page = fetch(c, h, version)
        assert (
            page["timezone"] == "Pacific/Honolulu"
            and page["today"] == today.isoformat()
        )
        assert page["items"][0]["review"] == dict(
            mastered=True,
            pending_count=3,
            due_count=2,
            next_due_date=(today - timedelta(days=1)).isoformat(),
        )
        change(
            mid,
            relapses={
                "again": dict(completed_at="2025-12-01T00:00:00+00:00", sequence=2)
            },
        )
        assert fetch(c, h, version)["items"][0]["review"]["mastered"] is False
        for plan_id in pending_ids:
            assert (
                c.post(
                    f"/api/v1/review-tasks/{plan_id}/complete", headers=h
                ).status_code
                == 200
            )
        summary = fetch(c, h, version)["items"][0]["review"]
        assert summary == dict(
            mastered=False, pending_count=0, due_count=0, next_due_date=None
        )
        change(
            mid,
            redoes={
                "correct": dict(
                    status="COMPLETED",
                    correct=True,
                    completed_at="2026-02-01T00:00:00+00:00",
                    sequence=3,
                )
            },
        )
        latest = fetch(c, h, version)["items"][0]["review"]
        assert latest["mastered"] is True
        actual = next(
            row
            for row in c.get("/api/v1/mistakes", headers=h).json()
            if row["id"] == mid
        )
        assert actual["mastered"] == latest["mastered"]
        change(
            mid,
            redoes={
                "invalid": dict(
                    status="COMPLETED", correct=True, completed_at="bad", sequence=3
                )
            },
            relapses={},
        )
        assert fetch(c, h, version)["items"][0]["review"]["mastered"] is None


def test_sql_paging_literal_title_matching_versions_and_material_revocation():
    with TestClient(app) as c:
        h, course, uid, doc, version, citations = setup(c)
        ids = [make(uid, course, version, citations[0]) for _ in range(15)]
        with SessionLocal() as db:
            for mid in ids:
                db.get(Mistake, mid).updated_at = datetime(
                    2026, 1, 1, tzinfo=timezone.utc
                )
            db.commit()
        first, second = fetch(c, h, version), fetch(c, h, version, offset=12)
        assert first["total"] == 15 and len(second["items"]) == 3
        assert [r["id"] for r in first["items"] + second["items"]] == sorted(ids)
        assert fetch(c, h, version, q="已保存的练习")["total"] == 15
        assert fetch(c, h, version, q="%_' OR 1=1 --")["total"] == 0
        assert fetch(c, h, version, offset=100)["items"] == []
        next_version = c.post(
            f"/api/v1/documents/{doc}/versions",
            headers=h,
            files={
                "file": ("新版.md", b"# New\nNot the original source.", "text/markdown")
            },
        ).json()["resource_id"]
        assert fetch(c, h, next_version)["total"] == 0
        assert c.delete(f"/api/v1/documents/{doc}", headers=h).status_code == 204
        assert c.get(endpoint(version), headers=h).status_code == 404


def test_manual_source_withdrawal_does_not_fall_back_to_version_identity():
    with TestClient(app) as c:
        h, course = setup_course(c)
        uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        version = import_pdf(c, h, course)
        candidate = draft(c, h, version, text="可核对原文。")
        confirmed = confirm(c, h, candidate)
        quote = dict(
            version_id=version["id"],
            chunk_id=confirmed["chunk_id"],
            quote="可核对原文。",
        )
        make(uid, course, version["id"], quote)
        assert fetch(c, h, version["id"])["total"] == 1
        assert (
            c.post(
                f"/api/v1/transcripts/{confirmed['id']}/withdraw",
                headers=h,
                json={"revision": confirmed["revision"]},
            ).status_code
            == 200
        )
        assert fetch(c, h, version["id"])["total"] == 0
