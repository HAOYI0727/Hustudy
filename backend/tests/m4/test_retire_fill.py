import json
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine
from app.models import PastQuestion, ExamPaper, ExamAttempt
from app.services.bank_question_types import upgrade_local_sources
from tests.m1.test_materialhub import context
from tests.m4.test_question_bank import start


def test_fill_import_edit_and_draw_are_solution_without_uniqueness_or_auto_grading():
    with TestClient(app) as c:
        h, course = context(c)
        p = c.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "空位保留",
                "content": "1. 已知x=2，结果____。\n答案：4 || 四\n解析：原文解答。",
            },
        ).json()
        q = p["questions"][0]
        assert q["question_type"] == "solution" and "____" in q["stem"]
        assert q["answer"] == "4 || 四" and not q["bank_data"]["warnings"]
        edited = c.patch(
            f"/api/v1/past-questions/{q['id']}",
            headers=h,
            json={
                "revision": q["revision"],
                "stem": q["stem"],
                "question_type": "fill_blank",
                "blank_answers": ["4", "四"],
                "unique_answer": True,
                "topic_ids": [],
            },
        )
        assert (
            edited.status_code == 200 and edited.json()["question_type"] == "solution"
        )
        assert edited.json()["answer"] == "4 || 四"
        assert (
            c.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h).status_code
            == 200
        )
        paper = c.post(
            f"/api/v1/courses/{course}/question-bank/draw",
            headers=h,
            json={
                "request_id": str(uuid4()),
                "count": 1,
                "question_type": "fill_blank",
            },
        ).json()
        assert paper["questions"][0]["type"] == "solution"
        a = start(c, h, paper)
        qid = paper["questions"][0]["id"]
        assert (
            c.put(
                f"/api/v1/attempts/{a['id']}/answers/{qid}",
                headers=h,
                json={"answer": "我的表述"},
            ).status_code
            == 200
        )
        submitted = c.post(f"/api/v1/attempts/{a['id']}/submit", headers=h).json()
        assert submitted["grading"][qid] == {
            "status": "submitted",
            "automatic": False,
            "submitted": True,
        }
        result = c.get(f"/api/v1/attempts/{a['id']}/result", headers=h).json()
        assert result["questions"][0]["answer"] == "4 || 四"


def test_existing_sources_upgrade_backed_up_idempotent_and_history_redo_preserved():
    with TestClient(app) as c:
        h, course = context(c)
        p = c.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={"title": "旧题库", "content": "1. 计算____。"},
        ).json()
        qid = p["questions"][0]["id"]
        c.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h)
        paper = c.post(
            f"/api/v1/courses/{course}/question-bank/draw",
            headers=h,
            json={"request_id": str(uuid4()), "count": 1},
        ).json()
        with SessionLocal() as db:
            source = db.get(PastQuestion, qid)
            source.question_type = "fill_blank"
            data = json.loads(source.bank_data_json)
            data.update(blank_answers=["原答案甲", "原答案乙"], unique_answer=True)
            source.bank_data_json = json.dumps(data)
            source.answer = None
            ep = db.get(ExamPaper, paper["id"])
            questions = json.loads(ep.questions_json)
            questions[0].update(
                type="fill_blank",
                blank_answers=["原答案甲", "原答案乙"],
                blank_count=2,
                unique_answer=True,
                answer=None,
            )
            ep.questions_json = json.dumps(questions)
            db.commit()
            old_revision = source.revision
        a = start(c, h, paper)
        c.post(f"/api/v1/attempts/{a['id']}/submit", headers=h)
        with SessionLocal() as db:
            before = (
                db.get(ExamPaper, paper["id"]).questions_json,
                db.get(ExamAttempt, a["id"]).snapshot_json,
                db.get(ExamAttempt, a["id"]).grading_json,
            )
        upgrade_local_sources()
        with SessionLocal() as db:
            source = db.get(PastQuestion, qid)
            assert (
                source.question_type == "solution"
                and source.answer == "原答案甲 || 原答案乙"
            )
            assert source.status == "CONFIRMED" and source.revision == old_revision + 1
            assert before == (
                db.get(ExamPaper, paper["id"]).questions_json,
                db.get(ExamAttempt, a["id"]).snapshot_json,
                db.get(ExamAttempt, a["id"]).grading_json,
            )
        backups = list(
            Path(engine.url.database).parent.glob(
                Path(engine.url.database).name + ".pre-fill-retirement-*.bak"
            )
        )
        assert backups
        upgrade_local_sources()
        with SessionLocal() as db:
            assert db.get(PastQuestion, qid).revision == old_revision + 1
        mistake = c.get("/api/v1/mistakes", headers=h).json()[0]
        redo = c.post(
            f"/api/v1/mistakes/{mistake['id']}/redoes",
            headers=h,
            json={"request_id": str(uuid4())},
        ).json()
        assert redo["question"]["type"] == "solution"
        saved = c.post(
            f"/api/v1/mistakes/{mistake['id']}/redoes/{redo['id']}/submit",
            headers=h,
            json={"answer": "自己的解释"},
        ).json()
        assert (
            saved["status"] == "NEEDS_SELF_REVIEW"
            and saved["question"]["answer"] == "原答案甲 || 原答案乙"
        )
        current = c.get(f"/api/v1/courses/{course}/question-bank", headers=h).json()[
            "items"
        ][0]
        same = c.patch(
            f"/api/v1/past-questions/{qid}",
            headers=h,
            json={
                "revision": current["revision"],
                "stem": current["stem"],
                "question_type": "solution",
                "answer": current["answer"],
                "topic_ids": current["bank_data"]["topic_ids"],
            },
        )
        assert same.status_code == 200 and same.json()["status"] == "CONFIRMED"
