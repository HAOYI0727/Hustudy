import json
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models import PastPaper, PastQuestion, ProcessingJob, Topic
from app.models.base import utc_now
from app.services import bank_ai, bank_topic_ai
from app.ai.providers import ProviderFailure
from app.workers.bank_ai import run_bank_ai_once
from tests.m4.test_bank_pdf_zip_ai import configure
from tests.m1.test_materialhub import context


def setup(client):
    h, c = context(client)
    tag = client.post(
        f"/api/v1/courses/{c}/topics",
        headers=h,
        json={"name": "传输层拥塞管理", "aliases": ["拥塞控制"]},
    ).json()["id"]
    r = client.post(
        f"/api/v1/courses/{c}/question-bank/import",
        headers=h,
        json={
            "title": "AI分类",
            "content": "1. 发送方发现丢包时如何调整发送窗口？\n答案：原文的参考解答，不应发送给分类模型。",
        },
    )
    assert r.status_code == 201, r.text
    p = r.json()
    return h, c, tag, p, p["questions"][0]


def preview(client, h, p, q):
    r = client.post(
        f"/api/v1/past-papers/{p['id']}/topic-ai-preview",
        headers=h,
        json={"question_ids": [q["id"]]},
    )
    assert r.status_code == 201, r.text
    return r.json()


def confirm(client, h, p):
    status = client.get(
        f"/api/v1/past-papers/{p['id']}/topic-ai-preview", headers=h
    ).json()
    return client.post(
        f"/api/v1/past-papers/{p['id']}/topic-ai-confirm",
        headers=h,
        json={"confirm_remote_send": True, "preview_id": status["preview_id"]},
    )


def install_fake(monkeypatch, q, tag, calls, during=None, candidates=None):
    class Fake:
        def structured(self, *args, **kwargs):
            calls.append(args)
            if during:
                during()
            return bank_topic_ai.Output.model_validate(
                {
                    "questions": [
                        {
                            "question_id": q["id"],
                            "topic_ids": [tag] if tag else [],
                            "candidates": candidates or [],
                            "reason": "丢包后发送窗口调整考查拥塞控制。",
                        }
                    ]
                }
            ), {}

    monkeypatch.setattr(bank_ai, "provider", lambda *args: Fake())


def test_preview_consent_job_semantic_result_no_lexical_or_answer_and_no_overwrite(
    monkeypatch,
):
    configure(monkeypatch)
    calls = []
    with TestClient(app) as client:
        h, c, tag, p, q = setup(client)
        assert (
            not q["bank_data"]["topic_ids"]
            and not q["bank_data"]["topic_index"]["existing"]
        )
        install_fake(monkeypatch, q, tag, calls)
        pv = preview(client, h, p, q)
        assert not calls and not run_bank_ai_once()
        assert "答案" not in json.dumps(pv["input"], ensure_ascii=False)
        assert len(pv["input"]["topics"]) == 1
        bad = client.post(
            f"/api/v1/past-papers/{p['id']}/topic-ai-confirm",
            headers=h,
            json={"confirm_remote_send": False},
        )
        assert bad.status_code == 422
        assert confirm(client, h, p).status_code == 202
        assert confirm(client, h, p).status_code == 202
        assert run_bank_ai_once() and len(calls) == 1
        assert not run_bank_ai_once()
        result = client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()[
            "items"
        ][0]
        assert result["bank_data"]["topic_index"]["existing"][0]["topic_id"] == tag
        assert not result["bank_data"]["topic_ids"]
        assert result["revision"] == q["revision"] + 1
        assert result["stem"] == q["stem"] and result["answer"] == q["answer"]
        assert (
            client.get(
                f"/api/v1/past-papers/{p['id']}/topic-ai-preview", headers=h
            ).json()["status"]
            == "SUCCEEDED"
        )


def test_missing_key_and_ownership_blocks_preview(monkeypatch):
    monkeypatch.setattr(bank_ai, "capabilities", lambda *args: {"configured": False})
    with TestClient(app) as client:
        h, c, tag, p, q = setup(client)
        r = client.post(
            f"/api/v1/past-papers/{p['id']}/topic-ai-preview",
            headers=h,
            json={"question_ids": [q["id"]]},
        )
        assert r.status_code == 409
        h2, _ = context(client)
        assert (
            client.get(
                f"/api/v1/past-papers/{p['id']}/topic-ai-preview", headers=h2
            ).status_code
            == 404
        )


@pytest.mark.parametrize("change", ["question", "topic", "expired", "config"])
def test_changed_preview_is_not_dispatched(monkeypatch, change):
    configure(monkeypatch)
    with TestClient(app) as client:
        h, c, tag, p, q = setup(client)
        preview(client, h, p, q)
        with SessionLocal() as db:
            if change == "question":
                db.get(PastQuestion, q["id"]).revision += 1
            elif change == "topic":
                db.get(Topic, tag).name = "改名"
            else:
                paper = db.get(PastPaper, p["id"])
                meta = json.loads(paper.bank_meta_json)
                if change == "expired":
                    meta["ai_topic_index"]["expires_at"] = (
                        utc_now() - timedelta(seconds=1)
                    ).isoformat()
                else:
                    meta["ai_topic_index"]["key_hash"] = "invalid"
                paper.bank_meta_json = json.dumps(meta)
            db.commit()
        assert confirm(client, h, p).status_code == 409
        assert not run_bank_ai_once()


def test_late_output_cannot_overwrite_changed_question(monkeypatch):
    configure(monkeypatch)
    with TestClient(app) as client:
        h, c, tag, p, q = setup(client)
        preview(client, h, p, q)
        assert confirm(client, h, p).status_code == 202

        def change():
            with SessionLocal() as db:
                row = db.get(PastQuestion, q["id"])
                row.stem = "人工刚保存的新题干"
                row.revision += 1
                db.commit()

        calls = []
        install_fake(monkeypatch, q, tag, calls, during=change)
        assert run_bank_ai_once()
        assert (
            client.get(
                f"/api/v1/past-papers/{p['id']}/topic-ai-preview", headers=h
            ).json()["status"]
            == "FAILED"
        )
        row = client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()[
            "items"
        ][0]
        assert (
            row["stem"] == "人工刚保存的新题干"
            and not row["bank_data"]["topic_index"]["existing"]
        )


@pytest.mark.parametrize(
    "items",
    [
        [{"question_id": "unknown", "topic_ids": [], "reason": "理由"}],
        [{"question_id": "q", "topic_ids": ["foreign"], "reason": "理由"}],
        [{"question_id": "q", "topic_ids": ["t", "t"], "reason": "理由"}],
        [{"question_id": "q", "candidates": ["新标签", "新标签"], "reason": "理由"}],
        [
            {"question_id": "q", "reason": "理由"},
            {"question_id": "q", "reason": "理由"},
        ],
    ],
)
def test_invalid_model_output_is_rejected(items):
    class Fake:
        def structured(self, *a, **k):
            return bank_topic_ai.Output.model_validate({"questions": items}), {}

    with pytest.raises(ProviderFailure):
        bank_topic_ai.classify(
            {
                "input": {
                    "questions": [{"question_id": "q"}],
                    "topics": [{"id": "t", "name": "标签", "aliases": []}],
                }
            },
            Fake(),
        )


def test_new_candidate_stays_uncreated_and_manual_save_keeps_ai_until_stem_changes(
    monkeypatch,
):
    configure(monkeypatch)
    with TestClient(app) as client:
        h, c, tag, p, q = setup(client)
        calls = []
        install_fake(monkeypatch, q, None, calls, candidates=["发送窗口调整"])
        preview(client, h, p, q)
        confirm(client, h, p)
        run_bank_ai_once()
        row = client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()[
            "items"
        ][0]
        assert row["bank_data"]["topic_index"]["candidates"] == ["发送窗口调整"]
        assert len(client.get(f"/api/v1/courses/{c}/topics", headers=h).json()) == 1
        edit = {
            "revision": row["revision"],
            "stem": row["stem"],
            "question_type": "solution",
            "topic_ids": [tag],
        }
        saved = client.patch(
            f"/api/v1/past-questions/{q['id']}", headers=h, json=edit
        ).json()
        assert saved["bank_data"]["topic_index"]["candidates"]
        edit.update(revision=saved["revision"], stem="另一道问题。")
        saved = client.patch(
            f"/api/v1/past-questions/{q['id']}", headers=h, json=edit
        ).json()
        assert not saved["bank_data"]["topic_index"]


def test_cancelled_job_and_network_failure_never_retry(monkeypatch):
    configure(monkeypatch)
    with TestClient(app) as client:
        h, c, tag, p, q = setup(client)
        preview(client, h, p, q)
        confirm(client, h, p)
        calls = []

        def cancel():
            with SessionLocal() as db:
                job = (
                    db.query(ProcessingJob)
                    .filter_by(resource_id=p["id"], type="BANK_EXTRACT")
                    .one()
                )
                job.status = "CANCELLED"
                db.commit()

        install_fake(monkeypatch, q, tag, calls, during=cancel)
        assert run_bank_ai_once() and not run_bank_ai_once()
        row = client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()[
            "items"
        ][0]
        assert row["revision"] == q["revision"]


def test_duplicate_or_outside_question_ids_are_rejected(monkeypatch):
    configure(monkeypatch)
    with TestClient(app) as client:
        h, c, tag, p, q = setup(client)
        for ids in [[q["id"], q["id"]], [str(uuid4())]]:
            r = client.post(
                f"/api/v1/past-papers/{p['id']}/topic-ai-preview",
                headers=h,
                json={"question_ids": ids},
            )
            assert r.status_code == 409


def test_another_preview_cannot_change_the_confirmed_scope(monkeypatch):
    configure(monkeypatch)
    with TestClient(app) as client:
        h, c, tag, p, q = setup(client)
        first = preview(client, h, p, q)
        second = preview(client, h, p, q)
        assert first["preview_id"] != second["preview_id"]
        r = client.post(
            f"/api/v1/past-papers/{p['id']}/topic-ai-confirm",
            headers=h,
            json={"confirm_remote_send": True, "preview_id": first["preview_id"]},
        )
        assert r.status_code == 409
        assert not run_bank_ai_once()


def test_source_revocation_blocks_dispatch_and_hides_preview(monkeypatch):
    from tests.m1.test_materialhub import upload
    from app.workers.materials import drain_jobs

    configure(monkeypatch)
    with TestClient(app) as client:
        h, c = context(client)
        version = upload(client, h, c, "1. 解释协议。", name="topics.md")["resource_id"]
        drain_jobs()
        p = client.post(
            f"/api/v1/courses/{c}/question-bank/import",
            headers=h,
            json={"title": "来源撤权", "version_id": version},
        ).json()
        preview(client, h, p, p["questions"][0])
        version_info = client.get(f"/api/v1/versions/{version}", headers=h).json()
        assert client.delete(
            f"/api/v1/documents/{version_info['document_id']}", headers=h
        ).is_success
        detail = client.get(
            f"/api/v1/past-papers/{p['id']}/topic-ai-preview", headers=h
        ).json()
        assert detail["status"] == "STALE" and "input" not in detail
        assert confirm(client, h, p).status_code != 202
        assert not run_bank_ai_once()


def test_network_failure_is_terminal_without_retry(monkeypatch):
    configure(monkeypatch)
    calls = []

    class Failed:
        def structured(self, *a, **k):
            calls.append(1)
            raise ProviderFailure("TIMEOUT", "模拟超时")

    monkeypatch.setattr(bank_ai, "provider", lambda *args: Failed())
    with TestClient(app) as client:
        h, c, tag, p, q = setup(client)
        preview(client, h, p, q)
        confirm(client, h, p)
        assert run_bank_ai_once() and not run_bank_ai_once()
        assert calls == [1]
        detail = client.get(
            f"/api/v1/past-papers/{p['id']}/topic-ai-preview", headers=h
        ).json()
        assert detail["status"] == "FAILED" and "TIMEOUT" in detail["error"]


def test_topic_ai_job_and_suggestions_survive_backup_restore(monkeypatch):
    from app.models import User
    from tests.shared.test_account_backups import exported, restored, empty_account

    configure(monkeypatch)
    with TestClient(app) as client:
        h, c, tag, p, q = setup(client)
        install_fake(monkeypatch, q, tag, [])
        preview(client, h, p, q)
        confirm(client, h, p)
        run_bank_ai_once()
        body, _ = exported(client, h)
        owner = client.get("/api/v1/auth/me", headers=h).json()["id"]
        with SessionLocal() as db:
            db.delete(db.get(User, owner))
            db.commit()
        target, _ = empty_account(client)
        result = restored(client, target, body)
        assert result["job"]["status"] == "SUCCEEDED", result
        rows = client.get(f"/api/v1/courses/{c}/question-bank", headers=target).json()[
            "items"
        ]
        assert rows[0]["bank_data"]["topic_index"]["existing"][0]["topic_id"] == tag
        assert (
            client.get(
                f"/api/v1/past-papers/{p['id']}/topic-ai-preview", headers=target
            ).json()["status"]
            == "SUCCEEDED"
        )


def test_optional_candidate_capacity_preserves_four_valid_names():
    q = {"question_id": "q", "stem": "综合计算机题", "options": [], "revision": 1}

    class Fake:
        def structured(self, *args, **kwargs):
            return bank_topic_ai.Output(
                questions=[
                    {
                        "question_id": "q",
                        "topic_ids": [],
                        "candidates": [
                            "多周期控制器",
                            "数据通路",
                            "微程序设计",
                            "控制信号",
                        ],
                        "reason": "综合题考查多个相关结构",
                    }
                ]
            ), {}

    result = bank_topic_ai.classify({"input": {"questions": [q], "topics": []}}, Fake())
    assert result["q"]["candidates"] == [
        "多周期控制器",
        "数据通路",
        "微程序设计",
        "控制信号",
    ]
