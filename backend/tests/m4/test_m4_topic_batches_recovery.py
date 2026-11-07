import json
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.services import bank_topic_ai, bank_ai, bank_vision
from app.workers.bank_ai import run_bank_ai_once
from tests.m1.test_materialhub import context
from tests.m4.test_bank_pdf_zip_ai import configure
from tests.m4.test_bank_vision import block


def test_more_than_32_topics_auto_batches_complete_and_no_answers(monkeypatch):
    configure(monkeypatch)
    with TestClient(app) as client:
        h, course = context(client)
        r = client.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "70题",
                "content": "\n".join(
                    f"{n}. 唯一题干{n}。\n答案：保密答案" for n in range(1, 71)
                ),
            },
        )
        assert r.status_code == 201, r.text
        paper = r.json()
        url = f"/api/v1/past-papers/{paper['id']}/topic-ai-"
        preview = client.post(url + "preview", headers=h, json={"question_ids": []})
        assert preview.status_code == 201, preview.text
        scope = preview.json()
        assert len(scope["input"]["questions"]) == 70 and scope["batch_count"] == 3
        assert "保密答案" not in json.dumps(scope, ensure_ascii=False)
        calls = []

        class Fake:
            def structured(self, *args, **kwargs):
                data = json.loads(args[1][0]["text"])
                calls.append(len(data["questions"]))
                return bank_topic_ai.Output(
                    questions=[
                        bank_topic_ai.Recommendation(
                            question_id=q["question_id"],
                            candidates=["综合"],
                            reason="依据题干",
                        )
                        for q in data["questions"]
                    ]
                ), {}

        monkeypatch.setattr(bank_ai, "provider", lambda *args: Fake())
        assert (
            client.post(
                url + "confirm",
                headers=h,
                json={"confirm_remote_send": True, "preview_id": scope["preview_id"]},
            ).status_code
            == 202
        )
        assert run_bank_ai_once()
        assert calls == [32, 32, 6]
        assert client.get(url + "preview", headers=h).json()["status"] == "SUCCEEDED"
        items = client.get(
            f"/api/v1/courses/{course}/question-bank?limit=100", headers=h
        ).json()["items"]
        assert len(items) == 70 and all(
            q["bank_data"]["topic_index"]["reason"] for q in items
        )


def test_duplicate_source_number_keeps_both_and_continues_correct_item():
    pages = [
        {"asset_id": str(uuid4()), "result": {"blocks": [block("1")], "empty": False}},
        {"asset_id": str(uuid4()), "result": {"blocks": [block("1")], "empty": False}},
        {
            "asset_id": str(uuid4()),
            "result": {"blocks": [block("1", continuation=True)], "empty": False},
        },
    ]
    _, rows = bank_vision.assemble(pages)
    assert len(rows) == 2 and len(rows[1]["source_images"]) == 2
    assert rows[0]["number"] != rows[1]["number"]
    assert any("原题号1重复" in warning for warning in rows[1]["warnings"])


def test_duplicate_page_numbers_are_saved_by_real_worker_not_zero_questions(monkeypatch):
    from tests.m4.test_bank_vision import configured, enqueue
    from tests.m4.test_bank_pdf_ocr import setup
    from app.workers.bank_ocr import run_bank_ocr_once
    configured(monkeypatch)
    monkeypatch.setattr(bank_vision, "transcribe", lambda *args, **kwargs:
        {"blocks": [block("1")], "empty": False})
    with TestClient(app) as client:
        h, course, version = setup(client)
        job = enqueue(client, h, course, version).json()
        assert run_bank_ocr_once()
        rows = client.get(f"/api/v1/courses/{course}/question-bank", headers=h).json()["items"]
        assert len(rows) == 2
        assert any(any("重复" in w for w in q["bank_data"]["import_warnings"]) for q in rows)
        meta = client.get(f"/api/v1/courses/{course}/question-bank/papers", headers=h).json()
        row = next(p for p in meta if p["id"] == job["paper_id"])
        assert row["recognition"]["status"] == "SUCCEEDED"
        assert row["question_count"] == 2
