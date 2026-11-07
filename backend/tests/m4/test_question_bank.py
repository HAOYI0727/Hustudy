"""User bank lifecycle: no provider, no user storage, deterministic assertions."""

import json
from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import ExamAttempt, ExamPaper, PastQuestion
from app.models.base import utc_now
from app.services import question_bank as bank
from app.workers.materials import drain_jobs
from tests.m1.test_materialhub import context, upload

TEXT = """1. 哪一个属于传输层？
A. IP B. TCP C. ARP D. ICMP
答案：B
知识标签：网络
2. TCP名称为____。
答案：传输控制协议
知识标签：网络
3. 简述TCP作用。
知识标签：网络
4. 网络的作用是____。
答案：连接与通信
知识标签：网络
"""


def seed_bank(client, headers, course, text=TEXT):
    response = client.post(
        f"/api/v1/courses/{course}/question-bank/import",
        headers=headers,
        json={"title": "用户题库", "content": text},
    )
    assert response.status_code == 201, response.text
    p = response.json()
    for q in p["questions"]:
        if q["question_type"] == "fill_blank":
            data = q["bank_data"]
            edit = {
                "revision": q["revision"],
                "stem": q["stem"],
                "question_type": "fill_blank",
                "answer": q["answer"],
                "blank_answers": data["blank_answers"],
                "unique_answer": q["number"] == "2",
                "topic_ids": data["topic_ids"],
            }
            saved = client.patch(
                f"/api/v1/past-questions/{q['id']}", headers=headers, json=edit
            )
            assert saved.status_code == 200, saved.text
    confirmed = client.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    topics = client.get(f"/api/v1/courses/{course}/topics", headers=headers).json()
    return confirmed.json(), topics[0]["id"]


def draw(client, headers, course, topic, count=4, **extra):
    response = client.post(
        f"/api/v1/courses/{course}/question-bank/draw",
        headers=headers,
        json={
            "request_id": str(uuid4()),
            "topic_ids": [topic],
            "count": count,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def start(client, headers, paper):
    url = f"/api/v1/exam-papers/{paper['id']}"
    assert client.post(url + "/attempts", headers=headers).status_code == 404
    assert client.post(url + "/review", headers=headers).status_code == 200
    response = client.post(url + "/attempts", headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def seed_choice(client, headers, course):
    text = "1. 哪个是传输层协议？\nA. IP B. TCP C. ARP D. ICMP\n答案：B\n知识标签：综合"
    return seed_bank(client, headers, course, text)


def test_import_detects_types_options_unknown_answers_and_revision():
    with TestClient(app) as client:
        owner, course = context(client)
        url = f"/api/v1/courses/{course}/question-bank/import"
        p = client.post(
            url, headers=owner, json={"title": "题库", "content": TEXT}
        ).json()
        assert [q["question_type"] for q in p["questions"]] == [
            "single_choice",
            "solution",
            "solution",
            "solution",
        ]
        assert p["questions"][0]["bank_data"]["options"] == ["IP", "TCP", "ARP", "ICMP"]
        assert p["questions"][0]["answer"] == "B"
        assert p["questions"][2]["answer"] is None
        assert p["questions"][1]["bank_data"]["unique_answer"] is None
        assert (
            client.post(
                f"/api/v1/past-papers/{p['id']}/confirm", headers=owner
            ).status_code
            == 200
        )
        assert (
            client.post(
                url, headers=owner, json={"title": "重复", "content": TEXT}
            ).json()["id"]
            != p["id"]
        )
        q = p["questions"][0]
        edit = {
            "revision": 1,
            "stem": q["stem"],
            "question_type": "single_choice",
            "options": ["IP", "TCP", "ARP", "ICMP"],
            "answer": "B",
            "topic_ids": q["bank_data"]["topic_ids"],
        }
        assert (
            client.patch(
                f"/api/v1/past-questions/{q['id']}", headers=owner, json=edit
            ).status_code
            == 200
        )
        assert (
            client.patch(
                f"/api/v1/past-questions/{q['id']}", headers=owner, json=edit
            ).status_code
            == 409
        )


def test_shuffle_syncs_key_does_not_change_bank_and_draw_is_idempotent():
    with TestClient(app) as client:
        owner, course = context(client)
        imported, topic = seed_bank(client, owner, course)
        request = {
            "request_id": str(uuid4()),
            "topic_ids": [topic],
            "count": 1,
            "question_type": "single_choice",
        }
        path = f"/api/v1/courses/{course}/question-bank/draw"
        paper = client.post(path, headers=owner, json=request).json()
        assert paper == client.post(path, headers=owner, json=request).json()
        assert (
            client.post(path, headers=owner, json=request | {"count": 2}).status_code
            == 409
        )
        assert (
            client.post(
                path,
                headers=owner,
                json=request | {"request_id": str(uuid4()), "count": 2},
            ).status_code
            == 422
        )
        with SessionLocal() as db:
            snapshot = json.loads(db.get(ExamPaper, paper["id"]).questions_json)[0]
            assert snapshot["options"]["ABCD".index(snapshot["answer"])] == "TCP"
            assert json.loads(
                db.get(PastQuestion, imported["questions"][0]["id"]).bank_data_json
            )["options"] == ["IP", "TCP", "ARP", "ICMP"]
        assert not {
            "answer",
            "blank_answers",
            "source_question_id",
            "citations",
            "source_revision",
        }.intersection(paper["questions"][0])


def test_choice_auto_solution_submission_self_review_and_retries():
    with TestClient(app) as client:
        owner, course = context(client)
        _, topic = seed_bank(client, owner, course)
        paper = draw(client, owner, course, topic)
        attempt = start(client, owner, paper)
        with SessionLocal() as db:
            questions = json.loads(db.get(ExamPaper, paper["id"]).questions_json)
        for q in questions:
            value = (
                q["answer"]
                if q["type"] == "single_choice"
                else [" 传输控制协议 "]
                if q["type"] == "fill_blank" and q["unique_answer"]
                else ["我自己的表述"]
                if q["type"] == "fill_blank"
                else "这是解答内容"
            )
            response = client.put(
                f"/api/v1/attempts/{attempt['id']}/answers/{q['id']}",
                headers=owner,
                json={"answer": value},
            )
            assert response.status_code == 200, response.text
            if q["type"] == "fill_blank" and q["unique_answer"]:
                assert response.json()["grading"][q["id"]]["status"] == "correct"
                assert "blank_answers" not in response.text
        path = f"/api/v1/attempts/{attempt['id']}"
        assert client.get(path + "/result", headers=owner).status_code == 409
        assert (
            client.get(
                f"/api/v1/courses/{course}/question-bank", headers=owner
            ).status_code
            == 409
        )
        assert (
            client.get(
                f"/api/v1/courses/{course}/past-papers", headers=owner
            ).status_code
            == 409
        )
        assert (
            client.post(
                f"/api/v1/exam-papers/{paper['id']}/review", headers=owner
            ).status_code
            == 409
        )
        result = client.post(path + "/submit", headers=owner).json()
        assert result == client.post(path + "/submit", headers=owner).json()
        assert result["status"] == "SCORED" and result["score"] == 0
        solution = next(q for q in questions if q["type"] == "solution")
        assert result["grading"][solution["id"]] == {
            "automatic": False,
            "status": "submitted",
            "submitted": True,
        }
        fill = next(
            q
            for q in questions
            if q["type"] == "solution" and "网络的作用" in q["stem"]
        )
        assert client.get(path + "/result", headers=owner).status_code == 200
        graded = client.post(
            path + f"/self-grades/{fill['id']}", headers=owner, json={"correct": False}
        )
        assert graded.status_code == 200 and graded.json()["status"] == "SCORED"
        assert (
            graded.json()
            == client.post(
                path + f"/self-grades/{fill['id']}",
                headers=owner,
                json={"correct": False},
            ).json()
        )
        assert len(client.get("/api/v1/mistakes", headers=owner).json()) == 1
        mistake = client.get("/api/v1/mistakes", headers=owner).json()[0]
        data = {"mistake_id": mistake["id"], "title": "复习"}
        task = client.post("/api/v1/review-tasks", headers=owner, json=data).json()
        assert (
            task == client.post("/api/v1/review-tasks", headers=owner, json=data).json()
        )


def test_ownership_deadline_restore_and_frozen_snapshot():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, other = context(client)
        _, topic = seed_bank(client, owner, course)
        paper = draw(
            client,
            owner,
            course,
            topic,
            1,
            question_type="solution",
            duration_minutes=1,
        )
        attempt = start(client, owner, paper)
        path = f"/api/v1/attempts/{attempt['id']}"
        assert client.get(path, headers=stranger).status_code == 404
        assert (
            client.get(
                f"/api/v1/courses/{course}/question-bank", headers=stranger
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/v1/courses/{other}/question-bank/draw",
                headers=stranger,
                json={"request_id": str(uuid4()), "topic_ids": [topic], "count": 1},
            ).status_code
            == 404
        )
        restored = client.get(path, headers=owner).json()
        original = restored["questions"][0]["stem"]
        with SessionLocal() as db:
            p = db.get(ExamPaper, paper["id"])
            altered = json.loads(p.questions_json)
            altered[0]["stem"] = "不应影响旧作答"
            p.questions_json = json.dumps(altered)
            a = db.get(ExamAttempt, attempt["id"])
            a.created_at = utc_now() - timedelta(minutes=2)
            db.commit()
        assert (
            client.get(path, headers=owner).json()["questions"][0]["stem"] == original
        )
        assert (
            client.put(
                path + f"/answers/{paper['questions'][0]['id']}",
                headers=owner,
                json={"answer": "过期"},
            ).status_code
            == 409
        )
        response = client.post(path + "/submit", headers=owner).json()
        assert (
            response["grading"][paper["questions"][0]["id"]]["status"] == "unanswered"
        )
        assert (
            client.get(path + "/result", headers=owner).json()["questions"][0]["stem"]
            == original
        )


def test_uploaded_document_sources_and_deletion_remove_sampling_eligibility():
    with TestClient(app) as client:
        owner, course = context(client)
        job = upload(client, owner, course, TEXT)
        drain_jobs()
        imported = client.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=owner,
            json={"title": "上传版", "version_id": job["resource_id"]},
        )
        assert imported.status_code == 201, imported.text
        q = imported.json()["questions"][0]
        assert q["bank_data"]["citations"]
        # Correct every fill field using the same confirmation path as text imports.
        assert client.post(f"/api/v1/past-papers/{imported.json()['id']}/confirm", headers=owner).status_code == 200
        topic = client.get(f"/api/v1/courses/{course}/topics", headers=owner).json()[0]["id"]
        paper = draw(client, owner, course, topic, 1, question_type="single_choice")
        citation = q["bank_data"]["citations"][0]
        version = client.get(
            f"/api/v1/versions/{citation['version_id']}", headers=owner
        ).json()
        assert (
            client.delete(
                f"/api/v1/documents/{version['document_id']}", headers=owner
            ).status_code
            == 204
        )
        assert (
            client.post(
                f"/api/v1/exam-papers/{paper['id']}/review", headers=owner
            ).status_code
            == 404
        )


def test_legacy_multi_blank_exact_rules_remain_for_old_snapshots():
    q = {
        "type": "fill_blank",
        "unique_answer": True,
        "blank_answers": ["TCP", "80"],
        "points": 3,
    }
    assert bank.grade(q, [" TCP ", "８０"])["status"] == "correct"
    assert bank.grade(q, ["tcp", "80"])["status"] == "incorrect"
    assert bank.grade(q, ["80", "TCP"])["status"] == "incorrect"
    assert bank.parse_text("不带题号的正文")[0]["answer"] is None


def test_missing_key_unset_uniqueness_invalid_types_and_insufficient_bank_reject():
    with TestClient(app) as client:
        owner, course = context(client)
        imported = client.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=owner,
            json={
                "title": "缺答案",
                "content": "1. 选择题：请选择。\nA. 一 B. 二 C. 三 D. 四\n知识标签：测试",
            },
        ).json()
        assert imported["questions"][0]["answer"] is None
        assert (
            client.post(
                f"/api/v1/past-papers/{imported['id']}/confirm", headers=owner
            ).status_code
            == 200
        )
        topic = imported["questions"][0]["bank_data"]["topic_ids"][0]
        response = client.post(
            f"/api/v1/courses/{course}/question-bank/draw",
            headers=owner,
            json={"request_id": str(uuid4()), "topic_ids": [topic], "count": 2},
        )
        assert (
            response.status_code == 422
            and response.json()["error"]["details"]["available"] == 1
        )
        assert (
            client.get(f"/api/v1/courses/{course}/exam-papers", headers=owner).json()
            == []
        )
        assert (
            client.post(
                f"/api/v1/courses/{course}/question-bank/import",
                headers=owner,
                json={"title": "空", "content": ""},
            ).status_code
            == 422
        )


def test_blueprint_overlapping_tag_quotas_are_satisfied_without_repeated_questions():
    with TestClient(app) as client:
        owner, course = context(client)
        text = "1. 第一题选择什么？\nA. 一 B. 二 C. 三 D. 四\n答案：A\n知识标签：甲,乙\n2. 第二题选择什么？\nA. 一 B. 二 C. 三 D. 四\n答案：D\n知识标签：甲"
        seed_bank(client, owner, course, text)
        payload = {
            "name": "重叠配额",
            "total_points": 6,
            "duration_minutes": 10,
            "question_types": [{"type": "single_choice", "count": 2, "points": 3}],
            "topics": [{"name": "甲", "count": 1}, {"name": "乙", "count": 1}],
        }
        bp = client.post(
            f"/api/v1/exam-blueprints?course_id={course}", headers=owner, json=payload
        ).json()
        paper = client.post(
            f"/api/v1/exam-blueprints/{bp['id']}/generate", headers=owner
        )
        assert paper.status_code == 201, paper.text
        assert len({q["stem"] for q in paper.json()["questions"]}) == 2
        assert sum(q["points"] for q in paper.json()["questions"]) == 6
        bad = payload | {"topics": [{"name": "乙", "count": 2}]}
        bp = client.post(
            f"/api/v1/exam-blueprints?course_id={course}", headers=owner, json=bad
        ).json()
        assert (
            client.post(
                f"/api/v1/exam-blueprints/{bp['id']}/generate", headers=owner
            ).status_code
            == 422
        )


def test_submission_freezes_answers_unanswered_objective_is_one_mistake():
    with TestClient(app) as client:
        owner, course = context(client)
        _, topic = seed_choice(client, owner, course)
        paper = draw(client, owner, course, topic, 1, question_type="single_choice")
        attempt = start(client, owner, paper)
        path = f"/api/v1/attempts/{attempt['id']}"
        assert (
            client.post(
                path + f"/self-grades/{paper['questions'][0]['id']}",
                headers=owner,
                json={"correct": True},
            ).status_code
            == 409
        )
        first = client.post(path + "/submit", headers=owner).json()
        assert first["grading"][paper["questions"][0]["id"]]["status"] == "unanswered"
        assert (
            client.put(
                path + f"/answers/{paper['questions'][0]['id']}",
                headers=owner,
                json={"answer": "A"},
            ).status_code
            == 409
        )
        assert client.post(path + "/submit", headers=owner).json() == first
        assert len(client.get("/api/v1/mistakes", headers=owner).json()) == 1


def test_bank_and_self_grade_roundtrip_new_archive_and_legacy_defaults():
    from app.models import User
    from tests.shared.test_account_backups import exported, restored, empty_account

    with TestClient(app) as client:
        owner, course = context(client)
        _, topic = seed_bank(client, owner, course)
        paper = draw(client, owner, course, topic)
        attempt = start(client, owner, paper)
        client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=owner)
        result = client.get(
            f"/api/v1/attempts/{attempt['id']}/result", headers=owner
        ).json()
        fill = next(
            q
            for q in result["questions"]
            if q["type"] == "solution" and "网络的作用" in q["stem"]
        )
        graded = client.post(
            f"/api/v1/attempts/{attempt['id']}/self-grades/{fill['id']}",
            headers=owner,
            json={"correct": False},
        ).json()
        source = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        body, archive = exported(client, owner)
        with SessionLocal() as db:
            db.delete(db.get(User, source))
            db.commit()
        target, _ = empty_account(client)
        done = restored(client, target, body)
        assert done["job"]["status"] == "SUCCEEDED", done
        assert done["counts"] == archive["counts"]
        assert (
            client.get(f"/api/v1/attempts/{attempt['id']}", headers=target).json()[
                "grading"
            ]
            == graded["grading"]
        )
        assert (
            client.get(
                f"/api/v1/attempts/{attempt['id']}/result", headers=target
            ).json()["questions"]
            == result["questions"]
        )
    from app.services.exam_backup import upgrade_legacy

    tables = {"past_papers": [{}], "past_questions": [{}], "exam_attempts": [{}]}
    upgrade_legacy(tables)
    assert tables["past_questions"][0] == {"bank_data_json": "{}", "revision": 1}
    assert tables["exam_attempts"][0] == {"snapshot_json": "{}", "grading_json": "{}"}


def test_missing_answers_and_solutions_self_review_without_tags_preserve_automatic_scores():
    with TestClient(app) as c:
        h, course = context(c)
        p = c.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "无答案自评",
                "content": "1. 选一项。\nA.甲 B.乙 C.丙 D.丁\n2. 补全____。\n3. 简述作用。\n4. 标准题。\nA.一 B.二 C.三 D.四\n答案：B",
            },
        ).json()
        fill = p["questions"][1]
        assert (
            c.patch(
                f"/api/v1/past-questions/{fill['id']}",
                headers=h,
                json={
                    "revision": fill["revision"],
                    "stem": fill["stem"],
                    "question_type": "fill_blank",
                    "unique_answer": True,
                    "blank_answers": [],
                    "topic_ids": [],
                },
            ).status_code
            == 200
        )
        result = c.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h)
        assert result.status_code == 200, result.text
        paper = c.post(
            f"/api/v1/courses/{course}/question-bank/draw",
            headers=h,
            json={"request_id": str(uuid4()), "topic_ids": [], "count": 4},
        ).json()
        attempt = start(c, h, paper)
        path = f"/api/v1/attempts/{attempt['id']}"
        assert (
            c.post(
                path + f"/self-grades/{paper['questions'][0]['id']}",
                headers=h,
                json={"correct": True},
            ).status_code
            == 409
        )
        submitted = c.post(path + "/submit", headers=h).json()
        before = submitted["score"]
        with SessionLocal() as db:
            questions = json.loads(db.get(ExamPaper, paper["id"]).questions_json)
        manual = [
            q
            for q in questions
            if q["type"] == "solution"
            or q["type"] == "fill_blank"
            or q["answer"] is None
        ]
        automatic = next(q for q in questions if q not in manual)
        assert (
            c.post(
                path + f"/self-grades/{automatic['id']}",
                headers=h,
                json={"correct": True},
            ).status_code
            == 422
        )
        for q in manual:
            response = c.post(
                path + f"/self-grades/{q['id']}", headers=h, json={"correct": False}
            )
            assert response.status_code == 200, response.text
            assert response.json()["grading"][q["id"]]["status"] == "self_incorrect"
            assert response.json()["score"] == before
            assert (
                c.post(
                    path + f"/self-grades/{q['id']}", headers=h, json={"correct": False}
                ).status_code
                == 200
            )
            assert (
                c.post(
                    path + f"/self-grades/{q['id']}", headers=h, json={"correct": True}
                ).status_code
                == 409
            )
        mistakes = c.get("/api/v1/mistakes", headers=h).json()
        assert len(mistakes) == 4
