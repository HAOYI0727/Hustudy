"""Isolated whole-paper completeness and final-answer persistence checks."""

import json
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.database import SessionLocal
from app.models import ExamAttempt, PastQuestion
from tests.m1.test_materialhub import context
from tests.m4.test_question_bank import seed_bank, start

TEXT = """1. 第一题。
知识标签：综合
2. 同一题干。
知识标签：综合
3. 同一题干。
知识标签：综合
4. 请选择。
A. 一 B. 二 C. 三 D. 四
答案：B
知识标签：综合
"""


def whole(client, headers, course, source, **kwargs):
    return client.post(
        f"/api/v1/courses/{course}/question-bank/papers/{source}/practice",
        headers=headers,
        json={"request_id": str(uuid4()), **kwargs},
    )


def test_complete_source_order_duplicates_options_and_final_state():
    with TestClient(app) as client:
        h, course = context(client)
        p, _ = seed_bank(client, h, course, TEXT)
        # Source numbers, rather than UUID order or lexical 1,10,2 ordering.
        with SessionLocal() as db:
            numbers = {"第一题。": "1-1", "请选择。": "2-10"}
            duplicates = iter(["2-2", "2-3"])
            for q in db.scalars(
                select(PastQuestion).where(PastQuestion.paper_id == p["id"])
            ):
                q.number = numbers.get(q.stem) or next(duplicates)
            db.commit()
        listing = client.get(
            f"/api/v1/courses/{course}/question-bank/practice-papers", headers=h
        ).json()
        assert listing[0]["available"] and listing[0]["question_count"] == 4
        assert set(listing[0]) == {
            "id",
            "title",
            "year",
            "question_count",
            "major_question_count",
            "eligible_count",
            "available",
            "reason",
        }
        key = str(uuid4())
        url = f"/api/v1/courses/{course}/question-bank/papers/{p['id']}/practice"
        payload = {"request_id": key, "duration_minutes": 90}
        response = client.post(url, headers=h, json=payload)
        assert response.status_code == 201, response.text
        exam = response.json()
        assert [q["source_number"] for q in exam["questions"]] == [
            "1-1",
            "2-2",
            "2-3",
            "2-10",
        ]
        assert [q["stem"] for q in exam["questions"]].count("同一题干。") == 2
        assert exam["questions"][-1]["options"] == ["一", "二", "三", "四"]
        assert all("answer" not in q for q in exam["questions"])
        assert client.post(url, headers=h, json=payload).json() == exam
        assert (
            client.post(
                url, headers=h, json=payload | {"duration_minutes": 60}
            ).status_code
            == 409
        )
        a = start(client, h, exam)
        path = f"/api/v1/attempts/{a['id']}"
        qid = exam["questions"][-1]["id"]
        for value in ["A", "C", "B"]:
            saved = client.put(
                path + f"/answers/{qid}", headers=h, json={"answer": value}
            )
            assert saved.status_code == 200
        restored = client.get(path, headers=h).json()
        assert restored["answers"] == {qid: "B"}
        final = client.post(path + "/submit", headers=h).json()
        assert (
            final["answers"] == {qid: "B"}
            and final["grading"][qid]["status"] == "correct"
        )
        assert client.post(path + "/submit", headers=h).json() == final
        another = client.post(
            f"/api/v1/exam-papers/{exam['id']}/attempts", headers=h
        ).json()
        assert another["id"] != a["id"] and another["answers"] == {}
        records = client.get(f"/api/v1/courses/{course}/exam-papers", headers=h).json()
        assert len(records[0]["attempts"]) == 2
        assert records[0]["attempts"][1] == {"id": a["id"], "status": final["status"]}
        with SessionLocal() as db:
            assert json.loads(db.get(ExamAttempt, a["id"]).answers_json) == {qid: "B"}
            assert (
                len(
                    db.scalars(
                        select(ExamAttempt).where(ExamAttempt.paper_id == exam["id"])
                    ).all()
                )
                == 2
            )


def test_permissions_unconfirmed_deleted_and_active_attempt_are_not_omitted():
    with TestClient(app) as client:
        h, course = context(client)
        other, other_course = context(client)
        p, _ = seed_bank(client, h, course, TEXT)
        assert whole(client, other, other_course, p["id"]).status_code == 404
        assert whole(client, h, other_course, p["id"]).status_code == 404
        with SessionLocal() as db:
            q = db.scalar(select(PastQuestion).where(PastQuestion.paper_id == p["id"]))
            q.status = "DRAFT"
            qid = q.id
            db.commit()
        listing = client.get(
            f"/api/v1/courses/{course}/question-bank/practice-papers", headers=h
        ).json()
        assert listing[0]["question_count"] == 4 and listing[0]["eligible_count"] == 3
        assert not listing[0]["available"]
        assert whole(client, h, course, p["id"]).status_code == 422
        with SessionLocal() as db:
            db.get(PastQuestion, qid).status = "CONFIRMED"
            db.commit()
        exam = whole(client, h, course, p["id"]).json()
        start(client, h, exam)
        assert whole(client, h, course, p["id"]).status_code == 409
        # Metadata remains readable during an active attempt without exposing answers.
        assert (
            client.get(
                f"/api/v1/courses/{course}/question-bank/practice-papers", headers=h
            ).status_code
            == 200
        )


def test_more_than_random_draw_limit_keeps_all_questions():
    with TestClient(app) as client:
        h, course = context(client)
        content = "\n".join(f"{n}. 题干{n}。\n知识标签：综合" for n in range(1, 102))
        p, _ = seed_bank(client, h, course, content)
        response = whole(client, h, course, p["id"])
        assert response.status_code == 201, response.text
        assert len(response.json()["questions"]) == 101


def test_invalid_sources_and_limits_fail_whole_instead_of_truncating(monkeypatch):
    from app.services import bank_paper_practice
    from app.models import PastPaper

    with TestClient(app) as client:
        h, course = context(client)
        p, _ = seed_bank(client, h, course, TEXT)
        monkeypatch.setattr(bank_paper_practice, "MAX_QUESTIONS", 3)
        assert whole(client, h, course, p["id"]).status_code == 422
        monkeypatch.setattr(bank_paper_practice, "MAX_QUESTIONS", 500)
        with SessionLocal() as db:
            q = db.scalar(select(PastQuestion).where(PastQuestion.paper_id == p["id"]))
            data = json.loads(q.bank_data_json)
            data["source_version_id"] = str(uuid4())
            q.bank_data_json = json.dumps(data)
            db.commit()
        assert whole(client, h, course, p["id"]).status_code == 422
        with SessionLocal() as db:
            db.get(PastPaper, p["id"]).bank_meta_json = json.dumps(
                {"deleted_by_user": True}
            )
            db.commit()
        assert whole(client, h, course, p["id"]).status_code == 404
        assert (
            client.get(
                f"/api/v1/courses/{course}/question-bank/practice-papers", headers=h
            ).json()
            == []
        )
