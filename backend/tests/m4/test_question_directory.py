import json
from fastapi.testclient import TestClient
from app.core.database import SessionLocal
from app.main import app
from app.models import PastPaper, PastQuestion, ExamBlueprint, ExamPaper, ExamAttempt
from tests.m1.test_materialhub import context


def test_directory_is_bounded_no_answers_and_body_is_explicitly_owned():
    with TestClient(app) as client:
        headers, course = context(client)
        foreign, _ = context(client)
        owner = client.get("/api/v1/auth/me", headers=headers).json()["id"]
        with SessionLocal() as db:
            paper = PastPaper(
                user_id=owner, course_id=course, title="目录样例", content_hash="x" * 64
            )
            db.add(paper)
            db.flush()
            for i in range(205):
                db.add(
                    PastQuestion(
                        user_id=owner,
                        paper_id=paper.id,
                        number=str(i),
                        stem="题干起始" + str(i) + "上下文" * 100,
                        question_type="single_choice",
                        answer="A",
                        bank_data_json=json.dumps(
                            {
                                "options": ["甲", "乙", "丙", "丁"],
                                "explanation": "不可放入目录的解析",
                                "topic_ids": [],
                            }
                        ),
                    )
                )
            db.commit()
        path = f"/api/v1/courses/{course}/question-directory"
        first = client.get(path, headers=headers).json()
        last = client.get(path + "?offset=200", headers=headers).json()
        assert first["total"] == last["total"] == 205
        assert len(first["items"]) == 200 and len(last["items"]) == 5
        assert len({q["id"] for q in first["items"] + last["items"]}) == 205
        item = first["items"][0]
        assert len(item["stem"]) <= 70 and set(item["bank_data"]) == {"topic_ids"}
        assert "answer" not in item and "explanation" not in json.dumps(item)
        detail = client.get(
            "/api/v1/past-questions/" + item["id"], headers=headers
        ).json()
        assert len(detail["stem"]) > 70 and detail["answer"] == "A"
        assert client.get(path, headers=foreign).status_code == 404
        assert (
            client.get(
                "/api/v1/past-questions/" + item["id"], headers=foreign
            ).status_code
            == 404
        )
        assert client.get(path + "?limit=201", headers=headers).status_code == 422
        with SessionLocal() as db:
            db.get(PastQuestion, item["id"]).status = "SUPERSEDED"
            db.commit()
        assert (
            client.get(
                "/api/v1/past-questions/" + item["id"], headers=headers
            ).status_code
            == 404
        )
        assert client.get(path, headers=headers).json()["total"] == 204


def test_directory_keeps_display_dedup_and_blocks_active_attempt():
    with TestClient(app) as client:
        headers, course = context(client)
        owner = client.get("/api/v1/auth/me", headers=headers).json()["id"]
        with SessionLocal() as db:
            paper = PastPaper(
                user_id=owner, course_id=course, title="去重", content_hash="y" * 64
            )
            db.add(paper)
            db.flush()
            for i, (stem, options) in enumerate(
                [
                    ("Ａ题\r\n正文", ["x", "y", "z", "w"]),
                    ("A题\n正文", ["x", "y", "z", "w"]),
                    ("A题\n正文", ["other", "y", "z", "w"]),
                ]
            ):
                db.add(
                    PastQuestion(
                        user_id=owner,
                        paper_id=paper.id,
                        number=str(i),
                        stem=stem,
                        question_type="single_choice",
                        bank_data_json=json.dumps(
                            {"options": options, "topic_ids": []}
                        ),
                    )
                )
            db.commit()
        path = f"/api/v1/courses/{course}/question-directory"
        rows = client.get(path, headers=headers).json()["items"]
        assert (
            rows[0]["fingerprint"] == rows[1]["fingerprint"]
            and rows[0]["fingerprint"] == rows[2]["fingerprint"]
        )
        with SessionLocal() as db:
            bp = ExamBlueprint(
                user_id=owner, course_id=course, name="作答隔离", config_json="{}"
            )
            db.add(bp)
            db.flush()
            ep = ExamPaper(
                user_id=owner,
                course_id=course,
                blueprint_id=bp.id,
                title="作答",
                questions_json="[]",
                mode="question_bank",
            )
            db.add(ep)
            db.flush()
            db.add(ExamAttempt(user_id=owner, paper_id=ep.id, status="IN_PROGRESS"))
            db.commit()
        assert client.get(path, headers=headers).status_code == 409
        assert (
            client.get(
                "/api/v1/past-questions/" + rows[0]["id"], headers=headers
            ).status_code
            == 409
        )
