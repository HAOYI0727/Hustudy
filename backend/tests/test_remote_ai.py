"""No real network: consent, source ownership, strict output and durable jobs."""

import json
from datetime import timedelta
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select, update
from app.main import app
from app.core.config import get_settings, Settings
from app.core.database import SessionLocal
from app.models import RemoteQuery, ProcessingJob, AIResult
from app.models.base import utc_now
from app.ai.providers import ZhipuProvider, ProviderFailure
from app.workers.ai_queries import run_ai_once, claim
from test_material_organization import setup_course, import_document


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("HUSTUDY_LLM_PROVIDER", "zhipu")
    get_settings.cache_clear()
    yield
    with SessionLocal() as db:
        db.execute(
            update(ProcessingJob)
            .where(
                ProcessingJob.type == "AI_ANALYSIS",
                ProcessingJob.status.in_(["QUEUED", "RUNNING"]),
            )
            .values(status="CANCELLED", lease_token=None, lease_until=None)
        )
        db.commit()
    get_settings.cache_clear()


def source():
    return {
        "source_id": str(uuid4()),
        "version_id": str(uuid4()),
        "document_id": str(uuid4()),
        "locator": {"type": "heading", "value": "测试"},
        "source_kind": "extracted",
        "text": "两个苹果加三个苹果等于五个苹果。",
    }


def envelope(content, finish="stop"):
    return {
        "choices": [
            {
                "finish_reason": finish,
                "message": {"content": content, "reasoning_content": "do not expose"},
            }
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
            "secret": "not included",
        },
    }


def payload(s, status="grounded"):
    return {
        "status": status,
        "answer": "共有五个苹果。",
        "evidence": [{"source_id": s["source_id"], "quote": s["text"]}]
        if status == "grounded"
        else [],
    }


def adapter(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "app.workers.ai_queries.ZhipuProvider",
        lambda settings: ZhipuProvider(settings, transport),
    )


@pytest.mark.parametrize(
    "case,code",
    [
        ("bad_json", "INVALID_OUTPUT"),
        ("extra", "INVALID_OUTPUT"),
        ("empty", "INVALID_OUTPUT"),
        ("fake_id", "INVALID_CITATION"),
        ("fake_quote", "INVALID_CITATION"),
        ("length", "INCOMPLETE_OUTPUT"),
        ("key_echo", "INVALID_OUTPUT"),
        ("rate_limit", "RATE_LIMITED"),
        ("auth", "AUTH_FAILED"),
        ("timeout", "TIMEOUT"),
        ("network", "NETWORK_ERROR"),
        ("oversize", "RESPONSE_BUDGET"),
    ],
)
def test_provider_rejects_bad_outputs_without_exposing_bodies(case, code):
    s = source()
    settings = Settings(
        llm_provider="zhipu", zhipu_api_key=SecretStr("synthetic-private-key")
    )
    output = payload(s)
    if case == "extra":
        output["unexpected"] = "value"
    if case == "empty":
        output["evidence"] = []
    if case == "fake_id":
        output["evidence"][0]["source_id"] = str(uuid4())
    if case == "fake_quote":
        output["evidence"][0]["quote"] = "不存在的原文"
    if case == "key_echo":
        output["answer"] = "synthetic-private-key"

    def handler(request):
        assert request.url.host == "open.bigmodel.cn"
        assert request.headers["Authorization"] == "Bearer synthetic-private-key"
        body = json.loads(request.content)
        assert body["thinking"] == {"type": "disabled"} and body["response_format"] == {
            "type": "json_object"
        }
        assert "synthetic-private-key" not in request.content.decode()
        if case == "timeout":
            raise httpx.ReadTimeout("synthetic-private-key", request=request)
        if case == "network":
            raise httpx.ConnectError("synthetic-private-key", request=request)
        if case in {"rate_limit", "auth"}:
            return httpx.Response(
                429 if case == "rate_limit" else 401, text="synthetic-private-key"
            )
        if case == "oversize":
            return httpx.Response(200, content=b"x" * (1024 * 1024 + 1))
        content = "not-json" if case == "bad_json" else json.dumps(output)
        return httpx.Response(
            200, json=envelope(content, "length" if case == "length" else "stop")
        )

    with pytest.raises(ProviderFailure) as error:
        ZhipuProvider(settings, httpx.MockTransport(handler)).answer("多少苹果", [s])
    assert error.value.code == code and "synthetic-private-key" not in str(error.value)
    assert "synthetic-private-key" not in repr(settings)


@pytest.mark.parametrize("status", ["grounded", "insufficient_evidence"])
def test_provider_accepts_valid_structures_and_strips_reasoning_usage(status):
    s = source()
    result, returned = ZhipuProvider(
        Settings(llm_provider="zhipu", zhipu_api_key=SecretStr("fake-secret")),
        httpx.MockTransport(
            lambda _: httpx.Response(200, json=envelope(json.dumps(payload(s, status))))
        ),
    ).answer("问题", [s])
    assert returned == status and result["review_status"] == "UNREVIEWED"
    assert bool(result["citations"]) == (status == "grounded")
    assert "do not expose" not in json.dumps(
        result
    ) and "not included" not in json.dumps(result)


def test_secret_in_context_is_rejected_before_network_or_preview_storage(configured):
    settings = Settings(
        llm_provider="zhipu", zhipu_api_key=SecretStr("synthetic-private-key")
    )

    def never_call(_request):
        pytest.fail("secret must not reach the provider")

    with pytest.raises(ProviderFailure) as error:
        ZhipuProvider(settings, httpx.MockTransport(never_call)).answer(
            "synthetic-private-key", [source()]
        )
    assert error.value.code == "SECRET_IN_CONTEXT"
    with TestClient(app) as client:
        owner, course = setup_course(client)
        import_document(client, owner, course, "# 苹果\n\n苹果样例。")
        response = client.post(
            f"/api/v1/courses/{course}/remote-queries/preview",
            headers=owner,
            json={"query": "苹果 deterministic-test-key"},
        )
        assert response.status_code == 422
        with SessionLocal() as db:
            assert not db.scalars(
                select(RemoteQuery).where(RemoteQuery.course_id == course)
            ).all()


def preview(client, owner, course, **scope):
    response = client.post(
        f"/api/v1/courses/{course}/remote-queries/preview",
        headers=owner,
        json={"query": "苹果数量", **scope},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_preview_consent_replay_real_result_and_note_source(configured, monkeypatch):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        foreign, foreign_course = setup_course(client)
        doc, version = import_document(
            client, owner, course, "# 苹果\n\n两个苹果加三个苹果等于五个苹果。"
        )
        _, foreign_version = import_document(
            client, foreign, foreign_course, "# 苹果\n\n秘密资料"
        )
        status = client.get("/api/v1/ai/provider", headers=owner).json()
        assert status["configured"] and "deterministic-test-key" not in json.dumps(
            status
        )
        assert (
            client.post(
                f"/api/v1/courses/{course}/remote-queries/preview",
                headers=owner,
                json={"query": "苹果", "version_ids": [foreign_version]},
            ).status_code
            == 404
        )
        calls = []

        def handler(request):
            body = json.loads(request.content)
            sent = json.loads(body["messages"][1]["content"])
            assert "秘密资料" not in request.content.decode()
            assert set(sent["sources"][0]) == {"source_id", "text"}
            calls.append(body)
            first = sent["sources"][0]
            return httpx.Response(
                200,
                json=envelope(
                    json.dumps(
                        {
                            "status": "grounded",
                            "answer": "五个苹果。",
                            "evidence": [
                                {
                                    "source_id": first["source_id"],
                                    "quote": "两个苹果加三个苹果等于五个苹果。",
                                }
                            ],
                        }
                    )
                ),
            )

        adapter(monkeypatch, handler)
        request = preview(client, owner, course, version_ids=[version])
        assert not calls and request["consented_at"] is None and request["job"] is None
        base = f"/api/v1/remote-queries/{request['id']}"
        for bad in (
            {},
            {"confirm_remote_send": False},
            {"confirm_remote_send": 1},
            {"confirm_remote_send": True, "sources": []},
        ):
            assert (
                client.post(base + "/confirm", headers=owner, json=bad).status_code
                == 422
            )
        for path in ("", "/confirm", "/cancel"):
            response = (
                client.get(base, headers=foreign)
                if not path
                else client.post(
                    base + path, headers=foreign, json={"confirm_remote_send": True}
                )
            )
            assert response.status_code == 404
        queued = client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        ).json()
        assert queued["job"]["status"] == "QUEUED" and not calls
        assert (
            client.post(
                base + "/confirm", headers=owner, json={"confirm_remote_send": True}
            ).json()["job"]["id"]
            == queued["job"]["id"]
        )
        assert run_ai_once() and len(calls) == 1
        result = client.get(base, headers=owner).json()
        assert result["job"]["status"] == "SUCCEEDED" and result["dispatched_at"]
        assert (
            result["result"]["model_mode"] == "real"
            and result["result"]["status"] == "grounded"
        )
        citation = result["result"]["result"]["citations"][0]
        note = client.post(
            "/api/v1/notes",
            headers=owner,
            json={
                "course_id": course,
                "title": "审阅草稿",
                "content": "待核实",
                "citations": [
                    {
                        "version_id": citation["version_id"],
                        "chunk_id": citation["chunk_id"],
                        "quote": citation["quote"],
                    }
                ],
            },
        )
        assert note.status_code == 201
        assert (
            client.get(
                f"/api/v1/ai-results/{result['result']['id']}", headers=foreign
            ).status_code
            == 404
        )
        assert (
            client.post(
                base + "/confirm", headers=owner, json={"confirm_remote_send": True}
            ).json()["result"]["id"]
            == result["result"]["id"]
        )
        assert len(calls) == 1
        assert (
            client.delete(f"/api/v1/documents/{doc}", headers=owner).status_code == 204
        )
        assert (
            client.get(base, headers=owner).json()["result"]["result"]["citations"][0][
                "availability"
            ]
            == "unavailable"
        )


def test_expiry_cancel_source_delete_course_delete_and_stale_worker(
    configured, monkeypatch
):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        doc, version = import_document(
            client, owner, course, "# 苹果\n\n苹果是自制样例。"
        )
        calls = []
        adapter(monkeypatch, lambda r: calls.append(r) or httpx.Response(429))
        expired = preview(client, owner, course)
        with SessionLocal() as db:
            db.get(RemoteQuery, expired["id"]).expires_at = utc_now() - timedelta(
                seconds=1
            )
            db.commit()
        assert (
            client.post(
                f"/api/v1/remote-queries/{expired['id']}/confirm",
                headers=owner,
                json={"confirm_remote_send": True},
            ).status_code
            == 409
        )
        request = preview(client, owner, course)
        base = f"/api/v1/remote-queries/{request['id']}"
        queued = client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        ).json()
        assert (
            client.post(base + "/cancel", headers=owner).json()["job"]["status"]
            == "CANCELLED"
        )
        assert not run_ai_once() and not calls
        request = preview(client, owner, course)
        base = f"/api/v1/remote-queries/{request['id']}"
        client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        )
        with SessionLocal() as db:
            job = claim(db)
            job.lease_until = utc_now() - timedelta(seconds=1)
            db.commit()
        assert not run_ai_once()
        assert (
            client.get(base, headers=owner).json()["job"]["status"] == "FAILED"
            and not calls
        )
        request = preview(client, owner, course)
        base = f"/api/v1/remote-queries/{request['id']}"
        client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        )
        client.delete(f"/api/v1/documents/{doc}", headers=owner)
        assert client.get(base, headers=owner).json()["job"]["status"] == "CANCELLED"
        assert not run_ai_once() and not calls
        assert (
            client.delete(
                f"/api/v1/courses/{course}?revision=1", headers=owner
            ).status_code
            == 204
        )
        assert client.get(base, headers=owner).status_code == 404
        assert (
            client.get(f"/api/v1/jobs/{queued['job']['id']}", headers=owner).status_code
            == 404
        )


def test_failure_persists_safe_result_and_cancel_during_request_rejects_late_answer(
    configured, monkeypatch
):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        import_document(client, owner, course, "# 苹果\n\n苹果是自制样例。")
        first = preview(client, owner, course)
        base = f"/api/v1/remote-queries/{first['id']}"
        client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        )
        adapter(
            monkeypatch, lambda _: httpx.Response(429, text="deterministic-test-key")
        )
        assert run_ai_once()
        failed = client.get(base, headers=owner).json()
        assert (
            failed["job"]["status"] == "FAILED"
            and failed["result"]["status"] == "provider_error"
        )
        assert failed["result"]["result"]["error_code"] == "RATE_LIMITED"
        assert "deterministic-test-key" not in json.dumps(failed)
        second = preview(client, owner, course)
        base2 = f"/api/v1/remote-queries/{second['id']}"
        client.post(
            base2 + "/confirm", headers=owner, json={"confirm_remote_send": True}
        )

        def delayed(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            assert client.post(base2 + "/cancel", headers=owner).status_code == 200
            return httpx.Response(
                200,
                json=envelope(
                    json.dumps(
                        {
                            "status": "grounded",
                            "answer": "待核实",
                            "evidence": [
                                {
                                    "source_id": sent["sources"][0]["source_id"],
                                    "quote": "苹果是自制样例。",
                                }
                            ],
                        }
                    )
                ),
            )

        adapter(monkeypatch, delayed)
        assert run_ai_once()
        late = client.get(base2, headers=owner).json()
        assert late["job"]["status"] == "CANCELLED" and late["result"] is None
        with SessionLocal() as db:
            assert (
                db.scalar(select(AIResult).where(AIResult.id == failed["result"]["id"]))
                is not None
            )


def test_selected_chunk_scope_budget_and_manual_withdrawal(configured):
    from test_manual_transcripts import draft, confirm
    from test_preview_assets import blank_pdf

    with TestClient(app) as client:
        owner, course = setup_course(client)
        foreign, foreign_course = setup_course(client)
        _, version = import_document(
            client, owner, course, "# 苹果\n\n" + "苹果原文。" * 900
        )
        chunks = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()
        chosen = preview(
            client, owner, course, chunk_ids=[chunks[0]["id"]], version_ids=[version]
        )
        assert len(chosen["sources"]) == 1 and len(chosen["sources"][0]["text"]) <= 2000
        assert chosen["sources"][0]["text"] in chunks[0]["text"]
        _, other_version = import_document(
            client, foreign, foreign_course, "# 苹果\n\n他人片段。"
        )
        other_chunk = client.get(
            f"/api/v1/versions/{other_version}/chunks", headers=foreign
        ).json()[0]["id"]
        assert (
            client.post(
                f"/api/v1/courses/{course}/remote-queries/preview",
                headers=owner,
                json={"query": "苹果", "chunk_ids": [other_chunk]},
            ).status_code
            == 404
        )
        pdf = client.post(
            f"/api/v1/courses/{course}/documents",
            headers=owner,
            files={"file": ("scan.pdf", blank_pdf(), "application/pdf")},
        ).json()
        from app.workers.materials import drain_jobs

        drain_jobs()
        transcript = confirm(
            client, owner, draft(client, owner, {"id": pdf["resource_id"]})
        )
        request = preview(
            client,
            owner,
            course,
            version_ids=[pdf["resource_id"]],
            chunk_ids=[transcript["chunk_id"]],
        )
        base = f"/api/v1/remote-queries/{request['id']}"
        assert (
            client.post(
                base + "/confirm", headers=owner, json={"confirm_remote_send": True}
            ).status_code
            == 202
        )
        assert (
            client.post(
                f"/api/v1/transcripts/{transcript['id']}/withdraw",
                headers=owner,
                json={"revision": transcript["revision"]},
            ).status_code
            == 200
        )
        assert client.get(base, headers=owner).json()["job"]["status"] == "CANCELLED"
        assert not run_ai_once()


def test_course_removal_cancels_queued_real_query_without_network(
    configured, monkeypatch
):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        import_document(client, owner, course, "# 苹果\n\n苹果样例。")
        row = preview(client, owner, course)
        queued = client.post(
            f"/api/v1/remote-queries/{row['id']}/confirm",
            headers=owner,
            json={"confirm_remote_send": True},
        ).json()

        def never_call(_request):
            pytest.fail("deleted course must not be sent")

        adapter(monkeypatch, never_call)
        assert (
            client.delete(
                f"/api/v1/courses/{course}?revision=1", headers=owner
            ).status_code
            == 204
        )
        assert not run_ai_once()
        with SessionLocal() as db:
            job = db.get(ProcessingJob, queued["job"]["id"])
            assert job.status == "CANCELLED" and job.lease_token is None
            assert db.get(RemoteQuery, row["id"]) is None
