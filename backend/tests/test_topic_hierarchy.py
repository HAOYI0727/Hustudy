import json
from fastapi.testclient import TestClient
from app.main import app
from app.services.topic_tree import validate_links
from app.core.database import SessionLocal
from app.models import Topic
from test_materialhub import context
from test_question_bank import draw, start
import pytest


def test_tree_parent_scope_cycles_depth_draw_list_and_merge():
    with TestClient(app) as c:
        h, course = context(c)

        def create(name, parent=None):
            return c.post(
                f"/api/v1/courses/{course}/topics",
                headers=h,
                json={"name": name, "parent_id": parent},
            )

        root = create("计算机组成").json()
        child = create("存储系统", root["id"]).json()
        leaf = create("缓存", child["id"]).json()
        assert leaf["parent_id"] == child["id"]
        bad = c.patch(
            f"/api/v1/topics/{root['id']}",
            headers=h,
            json={
                "revision": root["revision"],
                "name": root["name"],
                "parent_id": leaf["id"],
            },
        )
        assert bad.status_code == 422
        last = leaf
        for n in range(3):
            last = create(f"层级{n}", last["id"]).json()
        assert create("第7级", last["id"]).status_code == 422
        other, _ = context(c)
        assert (
            c.post(
                f"/api/v1/courses/{course}/topics",
                headers=other,
                json={"name": "越权", "parent_id": root["id"]},
            ).status_code
            == 404
        )
        p = c.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={"title": "层级题库", "content": "1. 缓存是什么？\n知识标签：缓存"},
        ).json()
        assert (
            c.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h).status_code
            == 200
        )
        result = c.get(
            f"/api/v1/courses/{course}/question-bank?topic_id={root['id']}", headers=h
        ).json()
        assert result["total"] == 1
        paper = draw(c, h, course, root["id"], count=1)
        assert paper["questions"][0]["topic_ids"] == [leaf["id"]]
        a = start(c, h, paper)
        assert (
            c.post(f"/api/v1/attempts/{a['id']}/submit", headers=h).status_code == 200
        )
        # Solution submissions are intentionally not wrong; create separate objective source.
        target = create("体系结构").json()
        assert (
            c.post(
                f"/api/v1/topics/{root['id']}/merge",
                headers=h,
                json={
                    "revision": root["revision"],
                    "target_id": leaf["id"],
                    "target_revision": leaf["revision"],
                },
            ).status_code
            == 422
        )
        assert (
            c.post(
                f"/api/v1/topics/{root['id']}/merge",
                headers=h,
                json={
                    "revision": root["revision"],
                    "target_id": target["id"],
                    "target_revision": target["revision"],
                },
            ).status_code
            == 200
        )
        items = c.get(f"/api/v1/courses/{course}/topics", headers=h).json()
        assert (
            next(t for t in items if t["id"] == child["id"])["parent_id"]
            == target["id"]
        )
        # Omitting parent in older edit clients must preserve hierarchy.
        value = next(t for t in items if t["id"] == leaf["id"])
        r = c.patch(
            f"/api/v1/topics/{leaf['id']}",
            headers=h,
            json={"revision": value["revision"], "name": "高速缓存", "aliases": []},
        )
        assert r.status_code == 200 and r.json()["parent_id"] == child["id"]
        with SessionLocal() as db:
            assert (
                json.loads(db.get(Topic, leaf["id"]).sources_json)["hierarchy"][
                    "parent_id"
                ]
                == child["id"]
            )


def test_tree_links_reject_backup_cross_scope_and_cycle():
    for links in (
        {"a": "other"},
        {"a": "b", "b": "a"},
        {str(i): str(i + 1) if i < 6 else None for i in range(7)},
    ):
        with pytest.raises(ValueError):
            validate_links(links)
    validate_links({"a": None, "b": "a"})


def test_parent_mistake_filter_keeps_immutable_child_snapshot():
    with TestClient(app) as c:
        h, course = context(c)
        root = c.post(
            f"/api/v1/courses/{course}/topics", headers=h, json={"name": "计组"}
        ).json()
        child = c.post(
            f"/api/v1/courses/{course}/topics",
            headers=h,
            json={"name": "缓存", "parent_id": root["id"]},
        ).json()
        p = c.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "客观题",
                "content": "1. 选一个。\nA.甲 B.乙 C.丙 D.丁\n答案：A\n知识标签：缓存",
            },
        ).json()
        assert (
            c.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h).status_code
            == 200
        )
        a = start(c, h, draw(c, h, course, root["id"], count=1))
        c.post(f"/api/v1/attempts/{a['id']}/submit", headers=h)
        rows = c.get(f"/api/v1/mistakes?topic_id={root['id']}", headers=h).json()
        assert len(rows) == 1
        assert {t["id"] for t in rows[0]["topics"]} == {root["id"], child["id"]}
        assert rows[0]["question"]["topic_ids"] == [child["id"]]
        report = c.post(f"/api/v1/courses/{course}/exam-analyses", headers=h).json()
        assert (
            next(t for t in report["report"]["topics"] if t["id"] == root["id"])[
                "count"
            ]
            == 1
        )
        matrix = c.get(f"/api/v1/exam-analyses/{report['id']}/gaps", headers=h).json()
        assert (
            next(t for t in matrix["topics"] if t["id"] == root["id"])["error_count"]
            == 1
        )


def test_hierarchy_roundtrips_in_full_backup_without_new_schema():
    from test_account_backups import exported, restored, empty_account
    from app.models import User

    with TestClient(app) as c:
        h, course = context(c)
        uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        root = c.post(
            f"/api/v1/courses/{course}/topics", headers=h, json={"name": "大标签"}
        ).json()
        child = c.post(
            f"/api/v1/courses/{course}/topics",
            headers=h,
            json={"name": "小标签", "parent_id": root["id"]},
        ).json()
        raw, _ = exported(c, h)
        with SessionLocal() as db:
            db.delete(db.get(User, uid))
            db.commit()
        destination, _ = empty_account(c)
        record = restored(c, destination, raw)
        assert record["job"]["status"] == "SUCCEEDED", record
        values = c.get(f"/api/v1/courses/{course}/topics", headers=destination).json()
        assert (
            next(t for t in values if t["id"] == child["id"])["parent_id"] == root["id"]
        )


def test_delete_used_topic_detaches_current_promotes_children_keeps_history_and_backup():
    from app.models import PastQuestion, ExamPaper, ExamAttempt
    from test_account_backups import exported, restored, empty_account

    with TestClient(app) as c:
        h, course = context(c)

        def create(name, parent=None):
            return c.post(
                f"/api/v1/courses/{course}/topics",
                headers=h,
                json={"name": name, "parent_id": parent},
            ).json()

        root = create("祖级")
        target = create("待删除", root["id"])
        child = create("子级", target["id"])
        p = c.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "删除标签保留题目",
                "content": "1. 简述目标。\n知识标签：待删除\n2. 简述其他。\n知识标签：子级",
            },
        ).json()
        assert (
            c.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h).status_code
            == 200
        )
        paper = draw(c, h, course, target["id"], count=1)
        attempt = start(c, h, paper)
        assert (
            c.delete(f"/api/v1/topics/{target['id']}?revision=1", headers=h).status_code
            == 409
        )
        c.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=h)
        with SessionLocal() as db:
            old_paper = db.get(ExamPaper, paper["id"]).questions_json
            old_attempt = db.get(ExamAttempt, attempt["id"]).snapshot_json
        other, _ = context(c)
        assert (
            c.delete(
                f"/api/v1/topics/{target['id']}?revision=1", headers=other
            ).status_code
            == 404
        )
        assert (
            c.delete(
                f"/api/v1/topics/{target['id']}?revision=99", headers=h
            ).status_code
            == 409
        )
        result = c.delete(f"/api/v1/topics/{target['id']}?revision=1", headers=h)
        assert result.status_code == 200, result.text
        values = c.get(f"/api/v1/courses/{course}/topics", headers=h).json()
        assert target["id"] not in {t["id"] for t in values}
        assert (
            next(t for t in values if t["id"] == child["id"])["parent_id"] == root["id"]
        )
        with SessionLocal() as db:
            q = db.get(PastQuestion, p["questions"][0]["id"])
            assert (
                q.topic_id is None and json.loads(q.bank_data_json)["topic_ids"] == []
            )
            assert q.status == "CONFIRMED"
            assert db.get(ExamPaper, paper["id"]).questions_json == old_paper
            assert db.get(ExamAttempt, attempt["id"]).snapshot_json == old_attempt
            assert (
                json.loads(db.get(Topic, target["id"]).sources_json)["deleted_by_user"]
                is True
            )
        report = c.post(f"/api/v1/courses/{course}/exam-analyses", headers=h)
        assert report.status_code in (200, 201), report.text
        assert report.json()["report"]["question_count"] == 2
        again = create("待删除")
        assert again["id"] != target["id"]
        data = c.post(
            f"/api/v1/courses/{course}/question-bank/draw",
            headers=h,
            json={
                "request_id": __import__("uuid").uuid4().hex,
                "topic_ids": [target["id"]],
                "count": 1,
            },
        )
        assert data.status_code == 404
        raw, _ = exported(c, h)
        from app.models import User

        uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        with SessionLocal() as db:
            db.delete(db.get(User, uid))
            db.commit()
        destination, _ = empty_account(c)
        record = restored(c, destination, raw)
        assert record["job"]["status"] == "SUCCEEDED", record
        restored_topics = c.get(
            f"/api/v1/courses/{course}/topics", headers=destination
        ).json()
        assert target["id"] not in {t["id"] for t in restored_topics}


def test_deleted_merge_target_hides_redirects_without_resurrecting_on_import():
    with TestClient(app) as c:
        h, course = context(c)

        def create(name):
            return c.post(
                f"/api/v1/courses/{course}/topics", headers=h, json={"name": name}
            ).json()

        alias = create("旧标签")
        target = create("合并目标")
        c.post(
            f"/api/v1/topics/{alias['id']}/merge",
            headers=h,
            json={"revision": 1, "target_id": target["id"], "target_revision": 1},
        )
        assert (
            c.delete(f"/api/v1/topics/{target['id']}?revision=2", headers=h).status_code
            == 200
        )
        assert c.get(f"/api/v1/courses/{course}/topics", headers=h).json() == []
        p = c.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={"title": "重新导入", "content": "1. 简述。\n知识标签：旧标签"},
        ).json()
        assert p["questions"][0]["topic_id"] not in {alias["id"], target["id"]}
