"""Long selected QA material; fake transports and late-page evidence only."""

import json
from datetime import timedelta
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import AIResult
from app.models.base import utc_now
from app.workers.ai_queries import run_ai_once
from app.services import m2_execution
from test_remote_ai import adapter, envelope
from test_remote_ai import configured as configured  # noqa: F401
from test_material_organization import setup_course, import_document
from test_m2_execution import confirm

FACT = "指令分为数据传送、算术运算、逻辑运算、程序转移和处理机控制。"


def selected(client, *, size=150, fact=True, **extra):
    owner, course = setup_course(client)
    text = "\n\n".join(
        f"# 第{i}页\n\n"
        + (
            FACT
            if i == size and fact
            else f"本页是第{i}页的示例说明和演示代码。" + "这里是代码演示。" * 12
        )
        for i in range(1, size + 1)
    )
    _, version = import_document(client, owner, course, text)
    response = client.post(
        f"/api/v1/courses/{course}/remote-queries/preview",
        headers=owner,
        json=dict(query="常用指令有哪些类型？", version_ids=[version], **extra),
    )
    assert response.status_code == 201, response.text
    return owner, course, version, response.json()


def fake(monkeypatch, calls, *, fail_at=None, empty=False):
    def handler(request):
        packet = json.loads(request.content)
        sent = json.loads(packet["messages"][1]["content"])
        calls.append(sent)
        if len(calls) == fail_at:
            return httpx.Response(429, json={"error": {"code": "1305"}})
        excerpts = [
            e for s in sent["sources"] for e in s["excerpts"] if FACT in e["text"]
        ]
        selected_evidence = (
            [] if empty else [{"excerpt_id": e["excerpt_id"]} for e in excerpts]
        )
        if "不要自己回答" in packet["messages"][0]["content"]:
            body = {"evidence": selected_evidence}
        else:
            body = {
                "status": "grounded" if selected_evidence else "insufficient_evidence",
                "answer": FACT if selected_evidence else "没有足够依据",
                "evidence": selected_evidence,
            }
        return httpx.Response(200, json=envelope(json.dumps(body)))

    adapter(monkeypatch, handler)


def drain(client, owner, pending):
    base = f"/api/v1/remote-queries/{pending['id']}"
    for _ in range(80):
        state = client.get(base, headers=owner).json()
        if state["job"]["status"] not in {"QUEUED", "RUNNING"}:
            return state
        assert run_ai_once()
    raise AssertionError("问答未结束")


@pytest.mark.usefixtures("configured")
def test_selected_full_course_reaches_last_page_then_synthesizes(monkeypatch):
    with TestClient(app) as client:
        owner, course, _, pending = selected(client)
        assert len(pending["sources"]) > 6
        coverage = pending["qa_scope"]["coverage"]
        assert coverage["truncated"] is False
        assert all(
            v["selected_chunks"] == v["total_chunks"]
            and v["sent_chars"] == v["total_chars"]
            for v in coverage["versions"]
        )
        assert FACT in "".join(s["text"] for s in pending["sources"])
        count = pending["qa_scope"]["batch_count"]
        assert count > 1 and pending["batch_progress"]["total"] == count + 1
        calls = []
        fake(monkeypatch, calls)
        confirm(client, owner, pending)
        result = drain(client, owner, pending)
        assert result["result"]["status"] == "grounded", result
        assert result["result"]["result"]["answer"] == FACT
        assert len(calls) == count + 1
        assert result["batch_progress"]["completed"] == count + 1
        assert any(FACT in c["quote"] for c in result["result"]["result"]["citations"])
        history = client.get(
            f"/api/v1/courses/{course}/ai-results", headers=owner
        ).json()
        assert len(history) == 1
        again = client.post(
            f"/api/v1/courses/{course}/remote-queries/preview",
            headers=owner,
            json={
                "query": pending["query"],
                "version_ids": [pending["sources"][0]["version_id"]],
            },
        ).json()
        assert again["reusable_result"]["id"] == result["result"]["id"]


@pytest.mark.usefixtures("configured")
def test_empty_batches_continue_and_zero_evidence_skips_final_call(monkeypatch):
    with TestClient(app) as client:
        owner, _, _, pending = selected(client, fact=False)
        calls = []
        fake(monkeypatch, calls, empty=True)
        confirm(client, owner, pending)
        result = drain(client, owner, pending)
        assert result["job"]["status"] == "SUCCEEDED"
        assert result["result"]["status"] == "insufficient_evidence"
        assert len(calls) == pending["qa_scope"]["batch_count"]
        assert result["result"]["result"]["partial"] is False


@pytest.mark.usefixtures("configured")
def test_failed_scan_requires_consent_and_resume_never_resends_completed_batch(
    monkeypatch,
):
    with TestClient(app) as client:
        owner, _, _, pending = selected(client)
        calls = []
        fake(monkeypatch, calls, fail_at=2)
        base = confirm(client, owner, pending)
        assert run_ai_once() and run_ai_once()
        state = client.get(base, headers=owner).json()
        assert state["job"]["status"] == "FAILED"
        assert state["batch_progress"]["completed"] == 1
        first_packet = calls[0]
        assert (
            client.post(
                base + "/resume", headers=owner, json={"confirm_remote_send": False}
            ).status_code
            == 422
        )
        assert (
            client.post(
                base + "/resume", headers=owner, json={"confirm_remote_send": True}
            ).status_code
            == 202
        )
        assert drain(client, owner, pending)["result"]["status"] == "grounded"
        assert calls.count(first_packet) == 1


@pytest.mark.usefixtures("configured")
def test_expired_window_preserves_scan_and_resume_uses_new_window(monkeypatch):
    with TestClient(app) as client:
        owner, _, _, pending = selected(client)
        calls = []
        fake(monkeypatch, calls)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        with SessionLocal() as db:
            record = db.get(AIResult, m2_execution.record_id(pending["id"]))
            state = json.loads(record.result_json)
            state["deadline_at"] = (utc_now() - timedelta(seconds=1)).isoformat()
            record.result_json = json.dumps(state)
            db.commit()
        assert not run_ai_once()
        state = client.get(base, headers=owner).json()
        assert state["result"]["result"]["error_code"] == "TASK_BUDGET_EXCEEDED"
        assert state["batch_progress"]["completed"] == 1
        assert len(calls) == 1
        assert (
            client.post(
                base + "/resume", headers=owner, json={"confirm_remote_send": True}
            ).status_code
            == 202
        )
        result = drain(client, owner, pending)
        assert result["result"]["status"] == "grounded"
        assert result["execution"]["window_number"] == 2


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("change", ["delete", "key", "cancel"])
def test_stop_during_scan_never_dispatches_next_batch(monkeypatch, change):
    with TestClient(app) as client:
        owner, _, _, pending = selected(client)
        calls = []

        def handler(request):
            calls.append(request)
            if change == "delete":
                client.delete(
                    f"/api/v1/documents/{pending['sources'][0]['document_id']}",
                    headers=owner,
                )
            elif change == "key":
                config = client.get("/api/v1/api-connection", headers=owner).json()
                client.delete(
                    f"/api/v1/api-connection?revision={config['revision']}",
                    headers=owner,
                )
            else:
                client.post(
                    f"/api/v1/remote-queries/{pending['id']}/cancel", headers=owner
                )
            return httpx.Response(200, json=envelope('{"evidence":[]}'))

        adapter(monkeypatch, handler)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        state = client.get(base, headers=owner).json()
        assert state["job"]["status"] in {"FAILED", "CANCELLED"}
        assert not run_ai_once()
        assert len(calls) == 1


@pytest.mark.usefixtures("configured")
def test_precise_more_than_six_chunks_and_long_tail_are_not_truncated():
    with TestClient(app) as client:
        owner, course, version, pending = selected(client, size=10)
        chunks = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()
        response = client.post(
            f"/api/v1/courses/{course}/remote-queries/preview",
            headers=owner,
            json={
                "query": "指令分类",
                "version_ids": [version],
                "chunk_ids": [c["id"] for c in chunks],
            },
        )
        assert response.status_code == 201, response.text
        assert FACT in "".join(s["text"] for s in response.json()["sources"])


@pytest.mark.usefixtures("configured")
def test_no_scope_stays_retrieved_and_foreign_version_rejected():
    with TestClient(app) as client:
        owner, course, version, _ = selected(client, size=4)
        result = client.post(
            f"/api/v1/courses/{course}/remote-queries/preview",
            headers=owner,
            json={"query": "演示"},
        )
        assert result.status_code == 201, result.text
        assert result.json()["qa_scope"]["mode"] == "retrieved"
        other, other_course = setup_course(client)
        assert (
            client.post(
                f"/api/v1/courses/{other_course}/remote-queries/preview",
                headers=other,
                json={"query": "指令分类", "version_ids": [version]},
            ).status_code
            == 404
        )


@pytest.mark.usefixtures("configured")
def test_synthesis_uses_independent_evidence_from_first_and_last_batches(monkeypatch):
    first = "数据传送指令用于传送数据。"
    last = "算术运算指令包括加法和减法。"
    calls = []
    with TestClient(app) as client:
        owner, course = setup_course(client)
        _, version = import_document(
            client,
            owner,
            course,
            "# 开始\n\n"
            + first
            + "\n\n# 示例\n\n"
            + "普通代码示例。" * 2400
            + "\n\n# 结束\n\n"
            + last,
        )
        response = client.post(
            f"/api/v1/courses/{course}/remote-queries/preview",
            headers=owner,
            json={"query": "资料包含哪些指令？", "version_ids": [version]},
        )
        assert response.status_code == 201, response.text
        pending = response.json()

        def handler(request):
            packet = json.loads(request.content)
            sent = json.loads(packet["messages"][1]["content"])
            calls.append(sent)
            evidence = [
                {"excerpt_id": e["excerpt_id"]}
                for s in sent["sources"]
                for e in s["excerpts"]
                if first in e["text"] or last in e["text"]
            ]
            if "不要自己回答" in packet["messages"][0]["content"]:
                body = {"evidence": evidence}
            else:
                text = "".join(
                    e["text"] for s in sent["sources"] for e in s["excerpts"]
                )
                assert first in text and last in text
                body = {
                    "status": "grounded",
                    "answer": first + last,
                    "evidence": evidence,
                }
            return httpx.Response(200, json=envelope(json.dumps(body)))

        adapter(monkeypatch, handler)
        confirm(client, owner, pending)
        result = drain(client, owner, pending)
        assert result["result"]["status"] == "grounded", result
        assert len(result["result"]["result"]["citations"]) == 2
