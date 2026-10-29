"""Manual-verifiable denominators, stale snapshots and module discovery boundaries."""

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import Topic, User
from app.workers.materials import drain_jobs
from test_materialhub import context, upload
from test_question_bank import seed_bank, seed_choice, draw, start
from test_preview_assets import png


def test_historical_denominators_known_unknown_primary_secondary_and_stale():
    with TestClient(app) as client:
        owner, course = context(client)
        bodies = [
            (
                2022,
                "1. 第一年的题目？\nA. 一 B. 二 C. 三 D. 四\n答案：A\n分值：10\n知识标签：甲,乙",
            ),
            (
                2024,
                "1. 第二年的选择？\nA. 一 B. 二 C. 三 D. 四\n答案：B\n分值：20\n知识标签：乙\n2. 第二年的说明题。\n知识标签：甲",
            ),
            (None, "1. 年份未知的说明题。\n分值：5\n知识标签：甲,乙,丙"),
        ]
        for year, content in bodies:
            p = client.post(
                f"/api/v1/courses/{course}/question-bank/import",
                headers=owner,
                json={"title": "样卷", "content": content, "year": year},
            ).json()
            assert (
                client.post(
                    f"/api/v1/past-papers/{p['id']}/confirm", headers=owner
                ).status_code
                == 200
            )
        # A duplicate source does not create an independent fourth sample.
        assert (
            len(
                client.get(
                    f"/api/v1/courses/{course}/past-papers", headers=owner
                ).json()
            )
            == 3
        )
        response = client.post(f"/api/v1/courses/{course}/exam-analyses", headers=owner)
        assert response.status_code == 201, response.text
        r = response.json()
        body = r["report"]
        rows = {t["name"]: t for t in body["topics"]}
        assert (
            body["sample_count"],
            body["question_count"],
            body["unknown_years"],
            body["unknown_points"],
            body["known_points"],
        ) == (3, 4, 1, 1, 35)
        assert body["known_points_coverage"] == 0.75 and body["known_years"] == [
            2022,
            2024,
        ]
        assert rows["甲"]["count"] == 3 and rows["乙"]["count"] == 3
        assert (
            rows["甲"]["primary_known_points"] == 15
            and rows["乙"]["primary_known_points"] == 20
        )
        assert rows["丙"]["year_rate"] == 0 and rows["丙"]["years"] == []
        topics = client.get(f"/api/v1/courses/{course}/topics", headers=owner).json()
        t = next(t for t in topics if t["name"] == "甲")
        renamed = client.patch(
            f"/api/v1/topics/{t['id']}",
            headers=owner,
            json={"revision": t["revision"], "name": "新甲", "aliases": ["旧称"]},
        )
        assert renamed.status_code == 200 and renamed.json()["id"] == t["id"]
        assert (
            client.patch(
                f"/api/v1/topics/{t['id']}",
                headers=owner,
                json={"revision": t["revision"], "name": "覆盖", "aliases": []},
            ).status_code
            == 409
        )
        old = client.get(f"/api/v1/exam-analyses/{r['id']}", headers=owner).json()
        assert old["status"] == "STALE" and old["report"] == body
        assert (
            client.post(
                f"/api/v1/courses/{course}/exam-analyses", headers=owner
            ).json()["status"]
            == "READY"
        )


def test_topic_merge_preserves_ids_old_attempt_snapshot_and_recomputes():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, _ = context(client)
        p, _ = seed_bank(
            client,
            owner,
            course,
            "1. 合并标签的题目？\nA. 一 B. 二 C. 三 D. 四\n答案：A\n分值：5\n知识标签：甲,乙",
        )
        topics = client.get(f"/api/v1/courses/{course}/topics", headers=owner).json()
        left, right = topics
        paper = draw(client, owner, course, left["id"], 1)
        a = start(client, owner, paper)
        client.post(f"/api/v1/attempts/{a['id']}/submit", headers=owner)
        original = client.get(
            f"/api/v1/attempts/{a['id']}/result", headers=owner
        ).json()
        report = client.post(
            f"/api/v1/courses/{course}/exam-analyses", headers=owner
        ).json()
        data = {
            "revision": left["revision"],
            "target_id": right["id"],
            "target_revision": right["revision"],
        }
        assert (
            client.post(
                f"/api/v1/topics/{left['id']}/merge", headers=stranger, json=data
            ).status_code
            == 404
        )
        merged = client.post(
            f"/api/v1/topics/{left['id']}/merge", headers=owner, json=data
        )
        assert merged.status_code == 200, merged.text
        with SessionLocal() as db:
            assert db.get(Topic, left["id"]).merged_into_id == right["id"]
        assert (
            client.get(f"/api/v1/attempts/{a['id']}/result", headers=owner).json()
            == original
        )
        assert (
            client.get(f"/api/v1/exam-analyses/{report['id']}", headers=owner).json()[
                "status"
            ]
            == "STALE"
        )
        new = client.post(
            f"/api/v1/courses/{course}/exam-analyses", headers=owner
        ).json()["report"]
        assert len(new["topics"]) == 1 and new["topics"][0]["primary_known_points"] == 5
        matrix = client.get(
            f"/api/v1/exam-analyses/{report['id']}/gaps", headers=owner
        ).json()
        assert (
            matrix["topics"][0]["error_count"] == 1
            and matrix["topics"][0]["judged_count"] == 1
        )
        # Cycles/self/merged targets cannot be created.
        assert (
            client.post(
                f"/api/v1/topics/{right['id']}/merge",
                headers=owner,
                json={
                    "revision": merged.json()["revision"],
                    "target_id": right["id"],
                    "target_revision": merged.json()["revision"],
                },
            ).status_code
            == 422
        )


def test_gap_candidates_manual_confirmation_notes_images_and_source_retraction():
    with TestClient(app) as client:
        owner, course = context(client)
        _, topic = seed_choice(client, owner, course)
        job = upload(client, owner, course, "# 课程讲义\n综合知识可以在此学习。")
        drain_jobs()
        assert (
            client.post(
                "/api/v1/notes",
                headers=owner,
                json={
                    "course_id": course,
                    "title": "综合笔记",
                    "content": "真实笔记正文",
                },
            ).status_code
            == 201
        )
        asset = client.post(
            f"/api/v1/courses/{course}/assets?alt=综合图片",
            headers=owner,
            files={"file": ("figure.png", png(), "image/png")},
        )
        assert asset.status_code == 201
        report = client.post(
            f"/api/v1/courses/{course}/exam-analyses", headers=owner
        ).json()
        path = f"/api/v1/exam-analyses/{report['id']}/gaps"
        m = client.get(path, headers=owner).json()["topics"][0]
        assert (
            m["match_status"] == "candidate"
            and m["mastery"] == "unknown"
            and m["notes"]
            and m["images"]
        )
        c = m["material_candidates"][0]
        response = client.put(
            f"/api/v1/topics/{topic}/sources",
            headers=owner,
            json={
                "revision": m["revision"],
                "version_id": c["version_id"],
                "chunk_id": c["chunk_id"],
                "quote": c["quote"],
            },
        )
        assert response.status_code == 200, response.text
        assert (
            client.get(path, headers=owner).json()["topics"][0]["match_status"]
            == "confirmed"
        )
        version = client.get(
            f"/api/v1/versions/{job['resource_id']}", headers=owner
        ).json()
        client.delete(f"/api/v1/documents/{version['document_id']}", headers=owner)
        current = client.get(path, headers=owner).json()
        assert (
            current["status"] == "STALE"
            and current["topics"][0]["match_status"] == "unmatched"
        )
        assert current["topics"][0]["confirmed_sources"] == []


def test_empty_analysis_and_analysis_archive_roundtrip():
    from test_account_backups import exported, restored, empty_account

    with TestClient(app) as client:
        owner, course = context(client)
        r = client.post(f"/api/v1/courses/{course}/exam-analyses", headers=owner).json()
        assert (
            r["report"]["sample_count"] == 0
            and r["report"]["known_points_coverage"] is None
        )
        source = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        body, _ = exported(client, owner)
        with SessionLocal() as db:
            db.delete(db.get(User, source))
            db.commit()
        target, _ = empty_account(client)
        result = restored(client, target, body)
        assert result["job"]["status"] == "SUCCEEDED", result
        assert (
            client.get(f"/api/v1/exam-analyses/{r['id']}", headers=target).json()[
                "report"
            ]
            == r["report"]
        )


def test_independent_type_tag_quotas_do_not_invent_joint_pairing():
    with TestClient(app) as client:
        owner, course = context(client)
        text = "1. 乙的选择？\nA. 一 B. 二 C. 三 D. 四\n答案：A\n知识标签：乙\n2. 甲的解答。\n知识标签：甲"
        seed_bank(client, owner, course, text)
        bp = client.post(
            f"/api/v1/exam-blueprints?course_id={course}",
            headers=owner,
            json={
                "name": "独立配额",
                "total_points": 6,
                "duration_minutes": 10,
                "question_types": [
                    {"type": "single_choice", "count": 1, "points": 3},
                    {"type": "solution", "count": 1, "points": 3},
                ],
                "topics": [{"name": "甲", "count": 1}, {"name": "乙", "count": 1}],
            },
        ).json()
        paper = client.post(
            f"/api/v1/exam-blueprints/{bp['id']}/generate", headers=owner
        )
        assert paper.status_code == 201, paper.text
        assert {q["topic"] for q in paper.json()["questions"]} == {"甲", "乙"}


def test_split_merge_keep_only_leaves_counted_and_never_rewrite_old_attempt():
    from app.models import PastQuestion

    with TestClient(app) as client:
        owner, course = context(client)
        p, topic = seed_bank(
            client, owner, course, "1. 父题包含两个要求。\n分值：10\n知识标签：综合"
        )
        paper = draw(client, owner, course, topic, 1, question_type="solution")
        a = start(client, owner, paper)
        client.post(f"/api/v1/attempts/{a['id']}/submit", headers=owner)
        old = client.get(f"/api/v1/attempts/{a['id']}/result", headers=owner).json()
        q = p["questions"][0]
        children = client.post(
            f"/api/v1/past-questions/{q['id']}/split",
            headers=owner,
            json={"revision": q["revision"], "parts": ["第一要求。", "第二要求。"]},
        )
        assert children.status_code == 200, children.text
        children = children.json()
        assert len(children) == 2 and all(c["points"] is None for c in children)
        assert (
            client.post(
                f"/api/v1/past-papers/{p['id']}/confirm", headers=owner
            ).status_code
            == 200
        )
        report = client.post(
            f"/api/v1/courses/{course}/exam-analyses", headers=owner
        ).json()["report"]
        assert (
            report["question_count"] == 2
            and report["known_points"] == 0
            and report["unknown_points"] == 2
        )
        assert (
            client.post(
                f"/api/v1/past-questions/{q['id']}/split",
                headers=owner,
                json={"revision": q["revision"], "parts": ["一", "二"]},
            ).status_code
            == 409
        )
        merged = client.post(
            f"/api/v1/courses/{course}/question-bank/merge",
            headers=owner,
            json={
                "question_ids": [c["id"] for c in children],
                "revisions": {c["id"]: c["revision"] for c in children},
                "stem": "合并后的两个要求。",
            },
        )
        assert merged.status_code == 200, merged.text
        assert (
            client.post(
                f"/api/v1/past-papers/{p['id']}/confirm", headers=owner
            ).status_code
            == 200
        )
        report = client.post(
            f"/api/v1/courses/{course}/exam-analyses", headers=owner
        ).json()["report"]
        assert report["question_count"] == 1 and report["unknown_points"] == 1
        with SessionLocal() as db:
            assert db.get(PastQuestion, q["id"]).status == "SUPERSEDED"
        assert (
            client.get(f"/api/v1/attempts/{a['id']}/result", headers=owner).json()
            == old
        )


def test_manual_duplicate_samples_stale_report_and_metadata_conflict():
    with TestClient(app) as client:
        owner, course = context(client)
        first, _ = seed_bank(
            client, owner, course, "1. 同年原卷的一题。\n知识标签：综合"
        )
        second, _ = seed_bank(
            client, owner, course, "1. 同年另一扫描件的转录题。\n知识标签：综合"
        )
        r = client.post(f"/api/v1/courses/{course}/exam-analyses", headers=owner).json()
        assert r["report"]["sample_count"] == 2
        payload = {
            "expected_revision": 1,
            "year": 2024,
            "variant": "A",
            "duplicate_of": first["id"],
        }
        assert (
            client.patch(
                f"/api/v1/past-papers/{second['id']}/metadata",
                headers=owner,
                json=payload,
            ).status_code
            == 200
        )
        assert (
            client.patch(
                f"/api/v1/past-papers/{second['id']}/metadata",
                headers=owner,
                json=payload,
            ).status_code
            == 409
        )
        assert (
            client.get(f"/api/v1/exam-analyses/{r['id']}", headers=owner).json()[
                "status"
            ]
            == "STALE"
        )
        new = client.post(
            f"/api/v1/courses/{course}/exam-analyses", headers=owner
        ).json()["report"]
        assert new["sample_count"] == 2 and new["question_count"] == 2  # Different stems remain distinct despite duplicate_of.
        assert (
            client.patch(
                f"/api/v1/past-papers/{first['id']}/metadata",
                headers=owner,
                json={"duplicate_of": second["id"]},
            ).status_code
            == 422
        )


def test_review_reschedule_and_0019_archive_upgrade():
    from test_account_backups import exported, restored, empty_account
    from test_note_tags import rewrite_manifest

    with TestClient(app) as client:
        owner, course = context(client)
        seed_choice(client, owner, course)
        task = client.post(
            "/api/v1/review-tasks",
            headers=owner,
            json={"title": "独立复习", "due_date": "2026-10-19"},
        ).json()
        path = f"/api/v1/review-tasks/{task['id']}"
        payload = {"due_date": "2026-11-01", "expected_due_date": task["due_date"]}
        assert client.patch(path, headers=owner, json=payload).status_code == 200
        assert client.patch(path, headers=owner, json=payload).status_code == 409
        body, _ = exported(client, owner)

        def downgrade(m):
            m["schema_revision"] = "0019_exam_bank"
            del m["tables"]["exam_analysis_reports"]
            for topic in m["tables"]["topics"]:
                for key in ("revision", "merged_into_id", "sources_json"):
                    del topic[key]

        legacy = rewrite_manifest(body, downgrade)
        source = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        with SessionLocal() as db:
            db.delete(db.get(User, source))
            db.commit()
        target, _ = empty_account(client)
        done = restored(client, target, legacy)
        assert done["job"]["status"] == "SUCCEEDED", done
        assert (
            client.get(f"/api/v1/courses/{course}/topics", headers=target).json()[0][
                "revision"
            ]
            == 1
        )


def test_ten_legal_and_five_illegal_blueprints_exact_structure():
    with TestClient(app) as client:
        owner,course=context(client)
        text='\n'.join(f'{i}. 第{i}个自制选择题。\nA. 一 B. 二 C. 三 D. 四\n答案：A\n知识标签：综合' for i in range(1,11))
        seed_bank(client,owner,course,text)
        path=f'/api/v1/exam-blueprints?course_id={course}'
        for count in range(1,11):
            points=1+count%3
            spec={'name':f'合法{count}','total_points':count*points,'duration_minutes':20,'question_types':[{'type':'single_choice','count':count,'points':points}],'topics':[{'name':'综合','count':count}]}
            bp=client.post(path,headers=owner,json=spec)
            assert bp.status_code==201,bp.text
            response=client.post(f"/api/v1/exam-blueprints/{bp.json()['id']}/generate",headers=owner)
            assert response.status_code==201,response.text
            questions=response.json()['questions']
            assert len(questions)==count and len({q['stem'] for q in questions})==count
            assert sum(q['points'] for q in questions)==count*points
        base={'name':'非法','total_points':2,'duration_minutes':20,'question_types':[{'type':'single_choice','count':1,'points':2}]}
        for mutation in [
            {'question_types':[{'type':'single_choice','count':-1,'points':2}]},
            {'question_types':[{'type':'single_choice','count':1,'points':0}]},
            {'total_points':3},
            {'topics':[{'name':'综合','count':2}]},
            {'question_types':[{'type':'single_choice','count':1,'points':1},{'type':'single_choice','count':1,'points':1}]},
        ]:
            assert client.post(path,headers=owner,json=base|mutation).status_code==422
