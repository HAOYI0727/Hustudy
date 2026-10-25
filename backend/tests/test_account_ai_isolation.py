"""Real personal stores and two owners, fake HTTP only; no shared-key fallback."""

import json
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_user_settings, base_settings, get_settings
from app.core import account_connection, connection_store
from app.ai.providers import ZhipuProvider, ProviderFailure
from app.services import bank_ai, bank_vision
from app.workers.ai_queries import run_ai_once
from test_material_organization import setup_course, import_document
from test_remote_ai import adapter, envelope
from test_m2_execution import confirm, valid_qa


def personal(client, headers, key, model="glm-5.3-flash"):
    status = client.get("/api/v1/api-connection", headers=headers).json()
    response = client.put(
        "/api/v1/api-connection",
        headers=headers,
        json={"revision": status["revision"], "key": key, "model": model},
    )
    assert response.status_code == 200, response.text
    return response.json()


def prepare(client, headers, course):
    _, version = import_document(
        client, headers, course, "# 苹果\n\n两个苹果加三个苹果等于五个苹果。"
    )
    response = client.post(
        f"/api/v1/courses/{course}/remote-queries/preview",
        headers=headers,
        json={"query": "苹果", "version_ids": [version]},
    )
    return response


def test_machine_file_and_environment_key_are_never_personal_fallback(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("HUSTUDY_LLM_PROVIDER", "zhipu")
    get_settings.cache_clear()
    monkeypatch.setattr(connection_store, "path", lambda _: tmp_path / "legacy.json")
    settings = base_settings()
    connection_store.write(
        settings,
        dict(
            model="glm-5.3-flash",
            encrypted_key=connection_store.cipher(settings)
            .encrypt(b"legacy-machine-private-key")
            .decode(),
        ),
    )
    with TestClient(app) as client:
        owner, course = setup_course(client)
        status = client.get("/api/v1/api-connection", headers=owner).json()
        assert status["scope"] == "account" and status["configured"] is False
        assert prepare(client, owner, course).status_code == 409
        assert not client.get(
            "/api/v1/question-bank/ai-capabilities", headers=owner
        ).json()["configured"]
    get_settings.cache_clear()


def test_two_queued_owners_send_only_their_own_authorization(monkeypatch):
    with TestClient(app) as client:
        a, ca = setup_course(client)
        b, cb = setup_course(client)
        personal(client, a, "synthetic-key-account-A")
        personal(client, b, "synthetic-key-account-B")
        pa = prepare(client, a, ca).json()
        pb = prepare(client, b, cb).json()
        ba = confirm(client, a, pa)
        bb = confirm(client, b, pb)
        calls = []

        def handler(request):
            calls.append(request.headers["Authorization"])
            assert "synthetic-key-account" not in request.content.decode()
            return httpx.Response(200, json=envelope(json.dumps(valid_qa())))

        adapter(monkeypatch, handler)
        assert run_ai_once() and run_ai_once()
        assert calls == [
            "Bearer synthetic-key-account-A",
            "Bearer synthetic-key-account-B",
        ]
        assert client.get(ba, headers=a).json()["result"]["status"] == "grounded"
        assert client.get(bb, headers=b).json()["result"]["status"] == "grounded"
        assert client.get(ba, headers=b).status_code == 404


@pytest.mark.parametrize("phase", ["confirm", "queued", "during_call"])
def test_own_clear_invalidates_pending_and_late_results(monkeypatch, phase):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        personal(client, owner, "synthetic-own-key")
        pending = prepare(client, owner, course).json()

        def clear():
            status = client.get("/api/v1/api-connection", headers=owner).json()
            assert (
                client.delete(
                    f"/api/v1/api-connection?revision={status['revision']}",
                    headers=owner,
                ).status_code
                == 200
            )

        if phase == "confirm":
            clear()
            assert (
                client.post(
                    f"/api/v1/remote-queries/{pending['id']}/confirm",
                    headers=owner,
                    json={"confirm_remote_send": True},
                ).status_code
                == 409
            )
            return
        base = confirm(client, owner, pending)
        calls = []

        def handler(request):
            calls.append(request)
            if phase == "during_call":
                clear()
            return httpx.Response(200, json=envelope(json.dumps(valid_qa())))

        adapter(monkeypatch, handler)
        if phase == "queued":
            clear()
        assert run_ai_once()
        assert client.get(base, headers=owner).json()["result"]["status"] != "grounded"
        assert len(calls) == (0 if phase == "queued" else 1)


def test_other_account_changes_do_not_invalidate_owner_preview(monkeypatch):
    with TestClient(app) as client:
        a, ca = setup_course(client)
        b, _ = setup_course(client)
        personal(client, a, "synthetic-key-A")
        personal(client, b, "synthetic-key-B")
        pa = prepare(client, a, ca).json()
        personal(client, b, "synthetic-key-B-updated")
        adapter(
            monkeypatch,
            lambda _: httpx.Response(200, json=envelope(json.dumps(valid_qa()))),
        )
        base = confirm(client, a, pa)
        assert run_ai_once()
        assert client.get(base, headers=a).json()["result"]["status"] == "grounded"


def test_cipher_and_model_factories_are_owner_bound(monkeypatch, tmp_path):
    with TestClient(app) as client:
        a, _ = setup_course(client)
        b, _ = setup_course(client)
        personal(client, a, "synthetic-private-A")
        personal(client, b, "synthetic-private-B")
        aid = client.get("/api/v1/auth/me", headers=a).json()["id"]
        bid = client.get("/api/v1/auth/me", headers=b).json()["id"]
        for factory in (bank_ai.provider, bank_vision.provider):
            assert (
                factory(aid).settings.zhipu_api_key.get_secret_value()
                == "synthetic-private-A"
            )
            assert (
                factory(bid).settings.zhipu_api_key.get_secret_value()
                == "synthetic-private-B"
            )
        assert bank_vision.fingerprint(aid) != bank_vision.fingerprint(bid)
        settings = base_settings()
        encrypted = account_connection.read(settings, aid)
        account_connection.write(settings, bid, encrypted)
        assert not get_user_settings(bid).zhipu_api_key.get_secret_value()
        assert (
            get_user_settings(aid).zhipu_api_key.get_secret_value()
            == "synthetic-private-A"
        )


def test_same_key_resave_still_rejects_old_provider_without_network(monkeypatch):
    with TestClient(app) as client:
        owner, _ = setup_course(client)
        personal(client, owner, "synthetic-unchanged-key")
        uid = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        calls = []
        provider = ZhipuProvider(
            get_user_settings(uid),
            httpx.MockTransport(
                lambda request: calls.append(request) or httpx.Response(500)
            ),
        )
        personal(client, owner, "synthetic-unchanged-key")
        with pytest.raises(ProviderFailure, match="本账户API配置已变化"):
            provider.answer("测试", [])
        assert not calls


def test_connection_test_of_a_does_not_write_status_to_b(monkeypatch):
    from app.routers import connection

    with TestClient(app) as client:
        a, _ = setup_course(client)
        b, _ = setup_course(client)
        personal(client, a, "synthetic-A-key")
        personal(client, b, "synthetic-B-key")

        def probe(settings):
            assert settings.zhipu_api_key.get_secret_value() == "synthetic-A-key"
            personal(client, b, "synthetic-B-new-key")

        monkeypatch.setattr(connection, "probe", probe)
        response = client.post(
            "/api/v1/api-connection/test",
            headers=a,
            json={"revision": 1, "confirm": True},
        )
        assert response.json()["test_status"] == "connected"
        assert (
            client.get("/api/v1/api-connection", headers=b).json()["test_status"]
            == "not_tested"
        )


def test_personal_credentials_are_not_exported_or_restored():
    import io
    import zipfile
    from test_account_backups import exported, restored, empty_account

    with TestClient(app) as client:
        owner, _ = empty_account(client)
        key = "synthetic-private-not-for-backup"
        personal(client, owner, key)
        body, _ = exported(client, owner)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            assert not any("api-connection" in name for name in archive.namelist())
            assert all(
                key.encode() not in archive.read(name) for name in archive.namelist()
            )
        target, _ = empty_account(client)
        record = restored(client, target, body)
        assert record["job"]["status"] == "SUCCEEDED", record
        assert not client.get("/api/v1/api-connection", headers=target).json()[
            "configured"
        ]
        assert client.get("/api/v1/api-connection", headers=owner).json()["configured"]


def test_bank_worker_dispatches_each_owners_personal_key(monkeypatch):
    from app.workers.bank_ai import run_bank_ai_once

    calls = []

    def handler(request):
        calls.append(request.headers["Authorization"])
        content = {
            "questions": [
                {
                    "number": "1",
                    "type": "solution",
                    "stem_lines": [1],
                    "answer_lines": [2],
                    "explanation_lines": [],
                }
            ]
        }
        return httpx.Response(200, json=envelope(json.dumps(content)))

    monkeypatch.setattr(
        bank_ai,
        "ZhipuProvider",
        lambda settings: ZhipuProvider(settings, httpx.MockTransport(handler)),
    )
    with TestClient(app) as client:
        for key in ["synthetic-bank-key-A", "synthetic-bank-key-B"]:
            owner, course = setup_course(client)
            personal(client, owner, key)
            _, version = import_document(
                client, owner, course, "1. 简述协议。\n原文给定的解释。"
            )
            preview = client.post(
                f"/api/v1/courses/{course}/question-bank/ai-preview",
                headers=owner,
                json={"title": "个人题库识别", "version_id": version},
            )
            assert preview.status_code == 201, preview.text
            pid = preview.json()["paper_id"]
            assert (
                client.post(
                    f"/api/v1/past-papers/{pid}/ai-confirm",
                    headers=owner,
                    json={"confirm_remote_send": True},
                ).status_code
                == 202
            )
            assert run_bank_ai_once()
            done = client.get(
                f"/api/v1/past-papers/{pid}/ai-preview", headers=owner
            ).json()
            assert done["status"] == "SUCCEEDED", done
        assert calls == ["Bearer synthetic-bank-key-A", "Bearer synthetic-bank-key-B"]


def test_vision_dispatches_owner_key_and_clear_stops_second_stage(
    monkeypatch, tmp_path
):
    from test_preview_assets import png

    calls = []
    with TestClient(app) as client:
        owner, _ = setup_course(client)
        personal(client, owner, "synthetic-vision-private-key")
        uid = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        image = tmp_path / "original.png"
        image.write_bytes(png())

        def handler(request):
            calls.append(request.headers["Authorization"])
            assert (
                client.delete(
                    "/api/v1/api-connection?revision=1", headers=owner
                ).status_code
                == 200
            )
            return httpx.Response(
                200,
                json=envelope(
                    json.dumps(
                        {
                            "blocks": [],
                            "empty": True,
                            "content_profile": "questions_only",
                        }
                    )
                ),
            )

        model = bank_vision.provider(uid)
        model.transport = httpx.MockTransport(handler)
        with pytest.raises(ProviderFailure, match="本账户API配置已变化"):
            bank_vision.transcribe(image, questions_only=False, adapter=model)
        assert calls == ["Bearer synthetic-vision-private-key"]
