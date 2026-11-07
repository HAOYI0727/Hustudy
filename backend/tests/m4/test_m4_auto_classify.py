import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import bank_ai, bank_topic_ai
from app.workers.bank_ai import run_bank_ai_once
from tests.m4.test_bank_topic_ai import setup
from tests.m4.test_bank_pdf_zip_ai import configure


@pytest.mark.parametrize("mode", ["existing", "candidate", "unknown"])
def test_auto_classify_assigns_or_creates_and_unknown_does_not_remove(
    monkeypatch, mode
):
    configure(monkeypatch)
    with TestClient(app) as client:
        h, course, topic, paper, question = setup(client)
        path = f"/api/v1/courses/{course}/past-questions/{question['id']}/auto-classify"
        assert (
            client.post(
                path,
                headers=h,
                json={"revision": question["revision"], "confirm_remote_send": False},
            ).status_code
            == 422
        )

        class Fake:
            def structured(self, *args, **kwargs):
                assert "参考解答" not in args[1][0]["text"]
                return bank_topic_ai.Output(
                    questions=[
                        bank_topic_ai.Recommendation(
                            question_id=question["id"],
                            topic_ids=[topic] if mode == "existing" else [],
                            candidates=["新知识点"] if mode == "candidate" else [],
                            reason="从题干判断" if mode != "unknown" else "无法判断",
                        )
                    ]
                ), {}

        monkeypatch.setattr(bank_ai, "provider", lambda *args: Fake())
        response = client.post(
            path,
            headers=h,
            json={"revision": question["revision"], "confirm_remote_send": True},
        )
        assert response.status_code == 202, response.text
        assert run_bank_ai_once()
        state = client.get(
            f"/api/v1/past-papers/{paper['id']}/topic-ai-preview", headers=h
        ).json()
        saved = client.get(f"/api/v1/courses/{course}/question-bank", headers=h).json()[
            "items"
        ][0]
        assert (
            saved["stem"] == question["stem"] and saved["answer"] == question["answer"]
        )
        if mode == "unknown":
            assert state["status"] == "FAILED" and not saved["bank_data"]["topic_ids"]
        else:
            assert (
                state["status"] == "SUCCEEDED"
                and len(saved["bank_data"]["topic_ids"]) == 1
            )
            assert saved["bank_data"]["topic_index"]["auto_assigned"]
            assert not saved["bank_data"]["topic_index"]["selection_reviewed"]
            assert saved["revision"] == question["revision"] + 1
            if mode == "candidate":
                topics = client.get(
                    f"/api/v1/courses/{course}/topics", headers=h
                ).json()
                assert any(t["name"] == "新知识点" for t in topics)
            assert (
                client.post(
                    path,
                    headers=h,
                    json={"revision": saved["revision"], "confirm_remote_send": True},
                ).status_code
                == 409
            )
