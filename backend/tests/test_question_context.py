import json
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import PastQuestion, ExamAttempt
from test_materialhub import context
from test_question_bank import start


def seeded(c, h, course):
    p = c.post(
        f"/api/v1/courses/{course}/question-bank/import",
        headers=h,
        json={
            "title": "大题公共条件",
            "content": "1. 已知内存容量为8KB，请使用以下完整表格。\n\n| 地址 | 数值 |\n| --- | --- |\n| 0 | 2 |\n答案：父题参考答案不得泄露\n解析：父题解析不得泄露",
        },
    ).json()
    children = c.post(
        f"/api/v1/past-questions/{p['questions'][0]['id']}/split",
        headers=h,
        json={
            "revision": 1,
            "parts": [
                "结果是____。\n答案：2",
                "解释求值过程。\n答案：兄弟答案不得泄露\n解析：兄弟解析不得泄露",
            ],
        },
    ).json()
    fill = children[0]
    assert (
        c.patch(
            f"/api/v1/past-questions/{fill['id']}",
            headers=h,
            json={
                "revision": fill["revision"],
                "stem": fill["stem"],
                "question_type": "fill_blank",
                "answer": "2",
                "blank_answers": ["2"],
                "unique_answer": True,
                "topic_ids": [],
            },
        ).status_code
        == 200
    )
    assert (
        c.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h).status_code == 200
    )
    return p, children


def test_single_subquestion_has_complete_context_without_other_answers_or_extra_scoring():
    with TestClient(app) as c:
        h, course = context(c)
        p, children = seeded(c, h, course)
        drawn = c.post(
            f"/api/v1/courses/{course}/question-bank/draw",
            headers=h,
            json={
                "request_id": str(uuid4()),
                "count": 1,
                "question_type": "fill_blank",
                "topic_ids": [],
            },
        ).json()
        assert len(drawn["questions"]) == 1
        q = drawn["questions"][0]
        assert q["type"] == "solution"
        assert "8KB" in q["context_stem"] and "| 地址 | 数值 |" in q["context_stem"]
        assert "解释求值过程" in q["context_stem"] + q["stem"]
        assert "8KB" in q["whole_stem"]
        assert "结果是" in q["whole_stem"] and "解释求值过程" in q["whole_stem"]
        assert q["whole_stem"].index("结果是") < q["whole_stem"].index("解释求值过程")
        assert "不得泄露" not in json.dumps(drawn, ensure_ascii=False)
        attempt = start(c, h, drawn)
        assert (
            c.put(
                f"/api/v1/attempts/{attempt['id']}/answers/{q['id']}",
                headers=h,
                json={"answer": "2"},
            ).status_code
            == 200
        )
        submitted = c.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=h).json()
        assert submitted["score"] == 0 and len(submitted["grading"]) == 1
        with SessionLocal() as db:
            old = db.get(ExamAttempt, attempt["id"]).snapshot_json
            db.get(PastQuestion, p["questions"][0]["id"]).stem = "修改后的条件"
            db.commit()
            assert db.get(ExamAttempt, attempt["id"]).snapshot_json == old
        result = c.get(f"/api/v1/attempts/{attempt['id']}/result", headers=h).json()
        assert "8KB" in result["questions"][0]["context_stem"]
        assert result["questions"][0]["whole_stem"] == q["whole_stem"]
        from test_account_backups import exported, restored, empty_account
        from app.models import User

        uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        raw, _ = exported(c, h)
        with SessionLocal() as db:
            db.delete(db.get(User, uid))
            db.commit()
        destination, _ = empty_account(c)
        assert restored(c, destination, raw)["job"]["status"] == "SUCCEEDED"
        restored_result = c.get(
            f"/api/v1/attempts/{attempt['id']}/result", headers=destination
        ).json()
        assert (
            restored_result["questions"][0]["context_stem"]
            == result["questions"][0]["context_stem"]
        )


def test_blueprint_also_freezes_context_and_tag_manual_choices_persist():
    with TestClient(app) as c:
        h, course = context(c)
        _, children = seeded(c, h, course)
        bp = c.post(
            f"/api/v1/exam-blueprints?course_id={course}",
            headers=h,
            json={
                "name": "单子题蓝图",
                "total_points": 2,
                "duration_minutes": 30,
                "question_types": [{"type": "fill_blank", "count": 1, "points": 2}],
                "topics": [],
            },
        ).json()
        drawn = c.post(f"/api/v1/exam-blueprints/{bp['id']}/generate", headers=h).json()
        assert (
            len(drawn["questions"]) == 1
            and "8KB" in drawn["questions"][0]["context_stem"]
        )
        child = children[1]
        with SessionLocal() as db:
            row = db.get(PastQuestion, child["id"])
            data = json.loads(row.bank_data_json)
            data["topic_index"] = {
                "version": "bank-topic-ai-v3",
                "existing": [],
                "candidates": [],
            }
            row.bank_data_json = json.dumps(data)
            db.commit()
        saved = c.patch(
            f"/api/v1/past-questions/{child['id']}",
            headers=h,
            json={
                "revision": child["revision"],
                "stem": child["stem"],
                "question_type": "solution",
                "answer": child["answer"],
                "topic_ids": [],
            },
        ).json()
        assert saved["bank_data"]["topic_index"]["selection_reviewed"] is True


def test_deleted_sibling_is_not_returned_through_archived_parent():
    with TestClient(app) as c:
        h, course = context(c)
        _, children = seeded(c, h, course)
        with SessionLocal() as db:
            sibling = db.get(PastQuestion, children[1]["id"])
            sibling.status = "SUPERSEDED"
            data = json.loads(sibling.bank_data_json)
            data["removed_by_user"] = True
            sibling.bank_data_json = json.dumps(data)
            db.commit()
        response = c.post(
            f"/api/v1/courses/{course}/question-bank/draw",
            headers=h,
            json={
                "request_id": str(uuid4()),
                "count": 1,
                "question_type": "fill_blank",
                "topic_ids": [],
            },
        )
        assert response.status_code == 422 and "公共条件" in response.text
