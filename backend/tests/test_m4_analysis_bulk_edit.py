import json

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import bank_ai, bank_topic_ai
from app.workers.bank_ai import run_bank_ai_once
from test_materialhub import context
from test_bank_pdf_zip_ai import configure


@pytest.mark.parametrize("unknown", [False, True])
def test_bulk_auto_classify_over_32_atomic_and_revision_guard(monkeypatch, unknown):
    configure(monkeypatch)
    with TestClient(app) as client:
        h, course = context(client)
        p = client.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "批量",
                "content": "\n".join(
                    f"{n}. 批量独立问题{n}。\n答案：不发送的答案" for n in range(1, 36)
                ),
            },
        ).json()
        path = f"/api/v1/courses/{course}/past-papers/{p['id']}/auto-classify"
        payload = {
            "revisions": {q["id"]: q["revision"] for q in p["questions"]},
            "confirm_remote_send": True,
        }
        assert (
            client.post(
                path, headers=h, json=payload | {"confirm_remote_send": False}
            ).status_code
            == 422
        )
        bad = payload | {"revisions": dict(payload["revisions"])}
        bad["revisions"][p["questions"][0]["id"]] += 1
        assert client.post(path, headers=h, json=bad).status_code == 409
        stranger, _ = context(client)
        assert client.post(path, headers=stranger, json=payload).status_code == 404
        calls = []

        class Fake:
            def structured(self, *args, **kwargs):
                raw = args[1][0]["text"]
                assert "不发送的答案" not in raw
                rows = json.loads(raw)["questions"]
                calls.append(len(rows))
                return bank_topic_ai.Output(
                    questions=[
                        bank_topic_ai.Recommendation(
                            question_id=q["question_id"],
                            candidates=[]
                            if unknown and q["question_id"] == p["questions"][-1]["id"]
                            else ["共同标签"],
                            reason="依据题干",
                        )
                        for q in rows
                    ]
                ), {}

        monkeypatch.setattr(bank_ai, "provider", lambda *args: Fake())
        response = client.post(path, headers=h, json=payload)
        assert response.status_code == 202, response.text
        assert response.json()["batch_count"] == 2
        assert run_bank_ai_once()
        state = client.get(
            f"/api/v1/past-papers/{p['id']}/topic-ai-preview", headers=h
        ).json()
        assert calls == [32, 3]
        assert state["status"] == ("FAILED" if unknown else "SUCCEEDED")
        rows = client.get(f"/api/v1/courses/{course}/question-bank", headers=h).json()[
            "items"
        ]
        assert all(bool(q["bank_data"]["topic_ids"]) is not unknown for q in rows)
        if not unknown:
            assert len({q["topic_id"] for q in rows}) == 1
            assert client.post(path, headers=h, json=payload).status_code == 409


def test_question_year_points_edit_isolated_stale_and_recomputed():
    with TestClient(app) as client:
        h, course = context(client)
        p = client.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "年份分值",
                "year": 2022,
                "content": "1. 第一道。\n分值：5\n知识标签：甲\n2. 第二道。\n分值：6\n知识标签：甲",
            },
        ).json()
        assert (
            client.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h).status_code
            == 200
        )
        report = client.post(
            f"/api/v1/courses/{course}/exam-analyses", headers=h
        ).json()
        q = p["questions"][0]
        path = f"/api/v1/past-questions/{q['id']}"
        payload = {
            "revision": q["revision"],
            "stem": q["stem"],
            "question_type": q["question_type"],
            "topic_ids": q["bank_data"]["topic_ids"],
            "points": 12,
            "year": 2025,
        }
        assert (
            client.patch(path, headers=h, json=payload | {"year": 1800}).status_code
            == 422
        )
        saved = client.patch(path, headers=h, json=payload)
        assert saved.status_code == 200, saved.text
        assert (
            saved.json()["bank_data"]["year"] == 2025 and saved.json()["points"] == 12
        )
        assert saved.json()["status"] == "DRAFT"
        assert client.patch(path, headers=h, json=payload).status_code == 409
        other = client.get(
            f"/api/v1/past-questions/{p['questions'][1]['id']}", headers=h
        ).json()
        assert "year" not in other["bank_data"] and other["points"] == 6
        old = client.get(f"/api/v1/exam-analyses/{report['id']}", headers=h).json()
        assert old["status"] == "STALE" and old["report"]["known_years"] == [2022]
        assert (
            client.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h).status_code
            == 200
        )
        result = client.post(
            f"/api/v1/courses/{course}/exam-analyses", headers=h
        ).json()["report"]
        assert result["known_years"] == [2022, 2025] and result["known_points"] == 18
        assert result["topics"][0]["years"] == [2022, 2025]
        # A legacy editor omitting year preserves the explicit per-question value.
        payload.pop("year")
        payload["revision"] = saved.json()["revision"]
        assert (
            client.patch(path, headers=h, json=payload).json()["bank_data"]["year"]
            == 2025
        )
        payload["revision"] += 1
        assert (
            client.patch(path, headers=h, json=payload | {"year": None}).json()[
                "bank_data"
            ]["year"]
            is None
        )


def test_bulk_year_points_atomic_and_preserves_unselected_and_other_fields():
    with TestClient(app) as client:
        h, course = context(client)
        p = client.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "批量数值",
                "year": 2022,
                "content": "1. 题一。\n分值：5\n2. 题二。\n分值：6\n3. 题三。\n分值：7",
            },
        ).json()
        questions = p["questions"]
        path = f"/api/v1/courses/{course}/question-bank/batch-values"
        payload = {
            "question_ids": [q["id"] for q in questions[:2]],
            "revisions": {q["id"]: q["revision"] for q in questions[:2]},
        }
        assert client.post(path, headers=h, json=payload).status_code == 422
        assert (
            client.post(path, headers=h, json=payload | {"points": 0}).status_code
            == 422
        )
        assert (
            client.post(path, headers=h, json=payload | {"year": "2025"}).status_code
            == 422
        )
        stranger, _ = context(client)
        assert (
            client.post(
                path, headers=stranger, json=payload | {"year": 2025}
            ).status_code
            == 404
        )
        stale = dict(payload["revisions"])
        stale[questions[1]["id"]] += 1
        assert (
            client.post(
                path,
                headers=h,
                json=payload | {"year": 2025, "points": 12, "revisions": stale},
            ).status_code
            == 409
        )
        unchanged = client.get(
            f"/api/v1/past-questions/{questions[0]['id']}", headers=h
        ).json()
        assert unchanged["points"] == 5 and "year" not in unchanged["bank_data"]
        result = client.post(
            path, headers=h, json=payload | {"year": 2025, "points": 12}
        )
        assert result.status_code == 200 and result.json()["changed"] == 2
        for q in questions[:2]:
            saved = client.get(f"/api/v1/past-questions/{q['id']}", headers=h).json()
            assert saved["points"] == 12 and saved["bank_data"]["year"] == 2025
            assert saved["stem"] == q["stem"] and saved["answer"] == q["answer"]
        other = client.get(
            f"/api/v1/past-questions/{questions[2]['id']}", headers=h
        ).json()
        assert other["points"] == 7 and "year" not in other["bank_data"]
        payload["revisions"] = result.json()["revisions"]
        result = client.post(path, headers=h, json=payload | {"points": None})
        assert result.status_code == 200
        saved = client.get(
            f"/api/v1/past-questions/{questions[0]['id']}", headers=h
        ).json()
        assert saved["points"] is None and saved["bank_data"]["year"] == 2025
        payload["revisions"] = result.json()["revisions"]
        result = client.post(path, headers=h, json=payload | {"year": None})
        assert result.status_code == 200
        saved = client.get(
            f"/api/v1/past-questions/{questions[0]['id']}", headers=h
        ).json()
        assert saved["points"] is None and saved["bank_data"]["year"] is None
