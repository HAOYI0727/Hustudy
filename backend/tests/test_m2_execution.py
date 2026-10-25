"""M2 consented repair and real deadlines; only fake transports/temporary data."""

import asyncio
import json
import time
from datetime import timedelta
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models import AIResult, RemoteQuery, ProcessingJob, User
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.models.base import utc_now
from app.services import m2_execution
from app.workers.ai_queries import run_ai_once
from test_remote_ai import adapter, envelope
from test_remote_ai import configured as configured  # noqa: F401
from test_material_organization import setup_course, import_document
from test_real_materials import long_report
from test_study_reports import model_report

BAD = "broken-json-SENTINEL-NOT-FOR-STORAGE"


def qa(client, repairs=0):
    owner, course = setup_course(client)
    document, version = import_document(
        client, owner, course, "# 苹果\n\n两个苹果加三个苹果等于五个苹果。"
    )
    preview = client.post(
        f"/api/v1/courses/{course}/remote-queries/preview",
        headers=owner,
        json={
            "query": "苹果",
            "version_ids": [version],
            "max_structure_repairs": repairs,
        },
    )
    assert preview.status_code == 201, preview.text
    return owner, course, document, preview.json()


def confirm(client, owner, pending):
    base = f"/api/v1/remote-queries/{pending['id']}"
    r = client.post(
        base + "/confirm", headers=owner, json={"confirm_remote_send": True}
    )
    assert r.status_code == 202, r.text
    return base


def valid_qa():
    return {
        "status": "grounded",
        "answer": "五个苹果",
        "evidence": [{"excerpt_id": "E1"}],
    }


def expire(pending):
    with SessionLocal() as db:
        record = db.get(AIResult, m2_execution.record_id(pending["id"]))
        state = json.loads(record.result_json)
        state["deadline_at"] = (utc_now() - timedelta(seconds=1)).isoformat()
        record.result_json = json.dumps(state)
        db.commit()


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("repairs", [0, 1, 2])
def test_opt_in_limits_and_no_failed_text_persistence(monkeypatch, repairs):
    with TestClient(app) as client:
        owner, _, _, pending = qa(client, repairs)
        calls = []
        adapter(
            monkeypatch,
            lambda request: calls.append(json.loads(request.content))
            or httpx.Response(200, json=envelope(BAD)),
        )
        base = confirm(client, owner, pending)
        assert not calls
        assert run_ai_once()
        response = client.get(base, headers=owner).json()
        assert response["result"]["status"] == "provider_error"
        assert len(calls) == repairs + 1
        assert response["execution"]["repairs_used"] == repairs
        assert response["execution"]["total_calls"] == repairs + 1
        assert all(call["messages"][1] == calls[0]["messages"][1] for call in calls)
        if repairs:
            assert calls[1]["messages"][2]["content"] == BAD
        with SessionLocal() as db:
            assert all(
                BAD not in record.result_json for record in db.scalars(select(AIResult))
            )
        assert BAD not in json.dumps(response)


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("kind", ["qa", "report"])
@pytest.mark.parametrize("malformed", ["json", "field"])
def test_authorized_structure_repair_success(monkeypatch, kind, malformed):
    with TestClient(app) as client:
        owner, course, _, pending = qa(client, 2)
        if kind == "report":
            pending = client.post(
                f"/api/v1/courses/{course}/study-reports/preview",
                headers=owner,
                json={
                    "version_ids": [pending["sources"][0]["version_id"]],
                    "max_structure_repairs": 2,
                },
            ).json()
        calls = []

        def handler(request):
            packet = json.loads(request.content)
            calls.append(packet)
            sent = json.loads(packet["messages"][1]["content"])
            body = valid_qa() if kind == "qa" else model_report(sent["sources"][0])
            if len(calls) == 1:
                if malformed == "json":
                    return httpx.Response(200, json=envelope(BAD))
                if kind == "qa":
                    body.pop("evidence")
                else:
                    body["report"].pop("learning_goals")
            return httpx.Response(200, json=envelope(json.dumps(body)))

        adapter(monkeypatch, handler)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        value = client.get(base, headers=owner).json()
        assert value["result"]["status"] == "grounded", value
        assert value["execution"]["repairs_used"] == 1 and len(calls) == 2
        assert value["result"]["result"]["execution"]["total_calls"] == 2
        assert value["result"]["result"]["citations"]
        from app.services import study_workspace

        with SessionLocal() as db:
            row = db.get(RemoteQuery, pending["id"])
            summary = study_workspace.summary(
                db, db.get(User, row.user_id), row.course_id
            )
            assert summary["counts"]["total"] == 1
            assert (
                len(
                    db.execute(
                        study_workspace.records(row.user_id, row.course_id)
                    ).all()
                )
                == 1
            )
        assert (
            client.post(
                base + "/confirm", headers=owner, json={"confirm_remote_send": True}
            ).json()["execution"]["total_calls"]
            == 2
        )


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize(
    "failure",
    [
        "citation",
        "citation_shape",
        "busy",
        "timeout",
        "secret",
        "truncated",
        "oversize",
        "long_bad",
    ],
)
def test_non_structure_failures_never_auto_retry(monkeypatch, failure):
    with TestClient(app) as client:
        owner, _, _, pending = qa(client, 2)
        calls = []

        def handler(request):
            calls.append(request)
            if failure == "busy":
                return httpx.Response(429, json={"error": {"code": "1305"}})
            if failure == "timeout":
                raise httpx.ReadTimeout("synthetic timeout")
            body = valid_qa()
            if failure == "citation":
                body["evidence"] = [{"excerpt_id": "E999"}]
            if failure == "citation_shape":
                body["evidence"] = [{"excerpt_id": "invented-reference"}]
            if failure == "long_bad":
                return httpx.Response(200, json=envelope("x" * 16001))
            if failure == "secret":
                body["answer"] = get_settings().zhipu_api_key.get_secret_value()
            if failure == "oversize":
                return httpx.Response(200, content=b"x" * (1024 * 1024 + 1))
            return httpx.Response(
                200,
                json=envelope(
                    json.dumps(body),
                    finish="length" if failure == "truncated" else "stop",
                ),
            )

        adapter(monkeypatch, handler)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        value = client.get(base, headers=owner).json()
        assert value["result"]["status"] == "provider_error", value
        assert len(calls) == 1 and value["execution"]["repairs_used"] == 0


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("change", ["cancel", "source", "config", "lease"])
def test_no_repair_after_cancel_revoke_config_or_lease_change(monkeypatch, change):
    with TestClient(app) as client:
        owner, _, document, pending = qa(client, 2)
        base = confirm(client, owner, pending)
        calls = []

        def handler(request):
            calls.append(request)
            if change == "cancel":
                assert client.post(base + "/cancel", headers=owner).status_code == 200
            elif change == "source":
                assert (
                    client.delete(
                        f"/api/v1/documents/{document}", headers=owner
                    ).status_code
                    == 204
                )
            elif change == "config":
                from ai_account_test_support import change_model

                change_model(client, owner, "glm-4.7-flash")
            else:
                with SessionLocal() as db:
                    row = db.get(RemoteQuery, pending["id"])
                    db.get(ProcessingJob, row.job_id).lease_until = (
                        utc_now() - timedelta(seconds=1)
                    )
                    db.commit()
            return httpx.Response(200, json=envelope(BAD))

        adapter(monkeypatch, handler)
        assert run_ai_once()
        response = client.get(base, headers=owner).json()
        assert len(calls) == 1
        assert response["result"] is None or response["result"]["status"] != "grounded"


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("wait", ["headers", "slow_body"])
def test_absolute_deadline_cancels_headers_and_trickling_body(monkeypatch, wait):
    monkeypatch.setattr(m2_execution, "WINDOW_SECONDS", 0.08)
    with TestClient(app) as client:
        owner, _, _, pending = qa(client, 2)
        calls, closed = [], []

        class SlowBody(httpx.AsyncByteStream):
            async def __aiter__(self):
                for _ in range(100):
                    await asyncio.sleep(0.03)
                    yield b" "

            async def aclose(self):
                closed.append(True)

        async def handler(request):
            calls.append(time.monotonic())
            if wait == "headers":
                await asyncio.sleep(5)
                return httpx.Response(200, json=envelope(BAD))
            return httpx.Response(200, stream=SlowBody())

        adapter(monkeypatch, handler)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        assert time.monotonic() - calls[0] < 1
        value = client.get(base, headers=owner).json()
        assert value["result"]["result"]["error_code"] == "TASK_BUDGET_EXCEEDED", value
        assert len(calls) == 1
        if wait == "slow_body":
            assert closed


@pytest.mark.usefixtures("configured")
def test_report_window_shared_across_steps_and_resume_preserves_repair_quota(
    monkeypatch,
):
    with TestClient(app) as client:
        owner, _, _, _, pending = long_report(client)
        # long_report makes its preview with the default no-repair policy.
        with SessionLocal() as db:
            row = db.get(RemoteQuery, pending["id"])
            sources = json.loads(json.dumps(row.sources))
            sources[0]["execution_policy"]["max_structure_repairs"] = 1
            row.sources = sources
            db.commit()
        calls = []

        def handler(request):
            packet = json.loads(request.content)
            sent = json.loads(packet["messages"][1]["content"])
            calls.append(sent)
            if len(calls) in (1, 3):
                return httpx.Response(200, json=envelope(BAD))
            return httpx.Response(
                200, json=envelope(json.dumps(model_report(sent["sources"][0])))
            )

        adapter(monkeypatch, handler)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        assert (
            client.get(base, headers=owner).json()["batch_progress"]["completed"] == 1
        )
        expire(pending)
        run_ai_once()
        stopped = client.get(base, headers=owner).json()
        assert stopped["result"]["result"]["error_code"] == "TASK_BUDGET_EXCEEDED"
        assert stopped["result"]["result"]["partial"] is True and len(calls) == 2
        other, _ = setup_course(client)
        assert (
            client.post(
                base + "/resume", headers=other, json={"confirm_remote_send": True}
            ).status_code
            == 404
        )
        assert (
            client.post(
                base + "/resume", headers=owner, json={"confirm_remote_send": False}
            ).status_code
            == 422
        )
        resumed = client.post(
            base + "/resume", headers=owner, json={"confirm_remote_send": True}
        )
        assert resumed.status_code == 202, resumed.text
        assert resumed.json()["execution"]["window_number"] == 2
        assert resumed.json()["execution"]["repairs_used"] == 1
        assert run_ai_once()
        final = client.get(base, headers=owner).json()
        assert final["job"]["status"] == "FAILED" and len(calls) == 3
        assert final["batch_progress"]["completed"] == 1
        assert (
            calls[2]["sources"][0]["source_id"] != calls[0]["sources"][0]["source_id"]
        )


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("invalid", [-1, 3, True, "2"])
def test_repair_consent_bounds_are_strict(invalid):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        response = client.post(
            f"/api/v1/courses/{course}/remote-queries/preview",
            headers=owner,
            json={"query": "苹果", "max_structure_repairs": invalid},
        )
        assert response.status_code == 422


@pytest.mark.usefixtures("configured")
def test_budget_resume_completes_without_repeating_successful_batches(monkeypatch):
    with TestClient(app) as client:
        owner, _, _, _, pending = long_report(client)
        calls = []

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            calls.append(sent["sources"][0]["source_id"])
            return httpx.Response(
                200, json=envelope(json.dumps(model_report(sent["sources"][0])))
            )

        adapter(monkeypatch, handler)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        expire(pending)
        run_ai_once()
        assert len(calls) == 1
        r = client.post(
            base + "/resume", headers=owner, json={"confirm_remote_send": True}
        )
        assert r.status_code == 202
        for _ in range(50):
            assert run_ai_once()
            value = client.get(base, headers=owner).json()
            if value["job"]["status"] != "QUEUED":
                break
        assert value["result"]["status"] == "grounded", value
        assert calls.count(calls[0]) == 1
        assert value["batch_progress"]["completed"] == value["batch_progress"]["total"]
        assert value["execution"]["window_number"] == 2


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize(
    "limit", ["window_call_limit", "input_chars_limit", "output_tokens_limit"]
)
def test_cumulative_call_input_output_limits_stop_next_step(monkeypatch, limit):
    with TestClient(app) as client:
        owner, _, _, _, pending = long_report(client)
        calls = []

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            calls.append(sent)
            return httpx.Response(
                200, json=envelope(json.dumps(model_report(sent["sources"][0])))
            )

        adapter(monkeypatch, handler)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        with SessionLocal() as db:
            record = db.get(AIResult, m2_execution.record_id(pending["id"]))
            state = json.loads(record.result_json)
            state[limit] = 0
            record.result_json = json.dumps(state)
            db.commit()
        assert run_ai_once()
        value = client.get(base, headers=owner).json()
        assert value["result"]["result"]["error_code"] == "TASK_BUDGET_EXCEEDED"
        assert len(calls) == 1 and value["batch_progress"]["completed"] == 1


@pytest.mark.usefixtures("configured")
def test_queue_time_excluded_and_old_previews_default_to_no_repair(monkeypatch):
    with TestClient(app) as client:
        owner, _, _, pending = qa(client)
        base = confirm(client, owner, pending)
        with SessionLocal() as db:
            row = db.get(RemoteQuery, pending["id"])
            sources = json.loads(json.dumps(row.sources))
            sources[0].pop("execution_policy")
            row.sources = sources
            row.consented_at = utc_now() - timedelta(days=1)
            db.commit()
        assert (
            client.get(base, headers=owner).json()["execution"]["window_started_at"]
            is None
        )
        adapter(
            monkeypatch,
            lambda request: httpx.Response(200, json=envelope(json.dumps(valid_qa()))),
        )
        assert run_ai_once()
        value = client.get(base, headers=owner).json()
        assert value["result"]["status"] == "grounded"
        assert value["execution"]["max_structure_repairs"] == 0


@pytest.mark.usefixtures("configured")
def test_internal_execution_backup_restore_does_not_dispatch(monkeypatch):
    from test_account_backups import exported, restored, empty_account

    with TestClient(app) as client:
        owner, _, _, pending = qa(client, 1)
        user_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(
                200, json=envelope(BAD if len(calls) == 1 else json.dumps(valid_qa()))
            )

        adapter(monkeypatch, handler)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        assert client.get(base, headers=owner).json()["result"]["status"] == "grounded"
        archive, _ = exported(client, owner)
        target, _ = empty_account(client)
        with SessionLocal() as db:
            db.delete(db.get(User, user_id))
            db.commit()
        assert restored(client, target, archive)["job"]["status"] == "SUCCEEDED"
        value = client.get(base, headers=target).json()
        assert value["execution"]["repairs_used"] == 1
        assert value["execution"]["total_calls"] == 2 and len(calls) == 2
        history = client.get(
            f"/api/v1/courses/{pending['course_id']}/ai-results", headers=target
        ).json()
        assert all(not item["query"].startswith("execution:") for item in history)


@pytest.mark.usefixtures("configured")
def test_queued_window_expires_even_when_other_ai_blocks_dispatch(monkeypatch):
    from uuid import uuid4

    with TestClient(app) as client:
        owner, _, _, _, pending = long_report(client)
        calls = []

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            calls.append(sent)
            return httpx.Response(
                200, json=envelope(json.dumps(model_report(sent["sources"][0])))
            )

        adapter(monkeypatch, handler)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        expire(pending)
        with SessionLocal() as db:
            row = db.get(RemoteQuery, pending["id"])
            blocker = ProcessingJob(
                user_id=row.user_id,
                type="BANK_EXTRACT",
                resource_id=str(uuid4()),
                status="RUNNING",
            )
            db.add(blocker)
            db.commit()
            blocker_id = blocker.id
        try:
            assert not run_ai_once()
            result = client.get(base, headers=owner).json()
            assert result["job"]["status"] == "FAILED"
            assert result["result"]["result"]["error_code"] == "TASK_BUDGET_EXCEEDED"
            assert len(calls) == 1
        finally:
            with SessionLocal() as db:
                db.get(ProcessingJob, blocker_id).status = "FAILED"
                db.commit()
