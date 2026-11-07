"""Synthetic credentials and local HTTP transports only; no paid model calls."""

import json
import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import base_settings, get_user_settings, get_zhipu_settings
from app.core import account_connection as store, model_connections as profiles
from app.ai.providers import ZhipuProvider, ProviderFailure
from app.routers import model_connections as connections, note_assistant
from app.services import bank_ai, bank_topic_ai
from tests.m1.test_material_organization import setup_course
from tests.shared.test_account_ai_isolation import personal, prepare
from app.workers.ai_queries import run_ai_once
from app.workers import ai_queries


KEY = "synthetic-deepseek-key-only-for-tests"


def test_model_connection_routes_registered_once():
    from fastapi.routing import APIRoute

    signatures = [
        (route.path, method)
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path.startswith("/api/v1/model-connections")
        for method in route.methods
    ]
    assert signatures
    assert len(signatures) == len(set(signatures))


def model(client, headers, **changes):
    status = client.get("/api/v1/model-connections", headers=headers).json()
    payload = dict(
        revision=status["revision"],
        name="测试DeepSeek",
        vendor="deepseek",
        endpoint="https://api.deepseek.com/chat/completions",
        model="deepseek-flash",
        key=KEY,
        thinking=True,
        vision=False,
        json_mode=True,
    )
    payload.update(changes)
    response = client.put("/api/v1/model-connections", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    profile = next(p for p in result["profiles"] if p["name"] == payload["name"])
    selected = client.post(
        "/api/v1/model-connections/active",
        headers=headers,
        json=dict(revision=result["revision"], profile_id=profile["id"]),
    )
    assert selected.status_code == 200, selected.text
    return selected.json(), profile


def owner(client, headers):
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


def note_input(client, headers, course):
    response = client.post(
        "/api/v1/notes",
        headers=headers,
        json=dict(
            course_id=course,
            title="并发笔记",
            content="# 并发\n\n事务隔离避免互相干扰。",
            tags=[],
        ),
    )
    assert response.status_code == 201, response.text
    note = response.json()
    return note, dict(
        course_id=course,
        note_id=note["id"],
        revision=note["revision"],
        task="summary",
        scope="full",
        text=note["content"],
        instruction="保留关键概念",
    )


def transport(
    markdown="## 要点\n\n事务隔离使并发事务互不干扰。", calls=None, after=None
):
    def handle(request):
        if calls is not None:
            calls.append(
                (
                    str(request.url),
                    request.headers["Authorization"],
                    json.loads(request.content),
                )
            )
        if after:
            after()
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps({"markdown": markdown}),
                            "reasoning_content": "internal reasoning never returned",
                        },
                    }
                ],
                "usage": {"total_tokens": 17},
            },
        )

    return httpx.MockTransport(handle)


def test_profiles_are_encrypted_isolated_and_keep_original_page_independent():
    with TestClient(app) as client:
        a, ca = setup_course(client)
        b, _ = setup_course(client)
        personal(client, a, "synthetic-original-zhipu-key")
        state, profile = model(client, a)
        uid = owner(client, a)
        assert KEY not in json.dumps(state)
        assert (
            KEY not in store.path(base_settings(), uid, profiles.NAMESPACE).read_text()
        )
        assert (
            client.get("/api/v1/model-connections", headers=b).json()["profiles"] == []
        )
        assert get_user_settings(uid).llm_provider == "compatible"
        assert (
            get_zhipu_settings(uid).zhipu_api_key.get_secret_value()
            == "synthetic-original-zhipu-key"
        )
        legacy = client.get("/api/v1/api-connection", headers=a).json()
        assert legacy["configured"] and legacy["model"] == "glm-5.3-flash"
        personal(client, a, "changed-original-zhipu-key")
        assert get_user_settings(uid).zhipu_api_key.get_secret_value() == KEY
        assert (
            len(client.get("/api/v1/model-connections", headers=a).json()["profiles"])
            == 1
        )
        assert (
            client.delete(
                "/api/v1/model-connections/" + profile["id"],
                headers=b,
                params={"revision": 0},
            ).status_code
            == 404
        )
        assert (
            client.delete(
                "/api/v1/model-connections/" + profile["id"],
                headers=a,
                params={"revision": state["revision"]},
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/v1/model-connections/test",
                headers=a,
                json={"revision": state["revision"], "profile_id": profile["id"]},
            ).status_code
            == 422
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://api.deepseek.com/chat/completions",
        "https://127.0.0.1/chat/completions",
        "https://evil.invalid/chat/completions",
        "https://api.deepseek.com@localhost/chat/completions",
        "https://api.deepseek.com:8443/chat/completions",
        "https://api.deepseek.com/chat/completions?secret=x",
    ],
)
def test_unapproved_or_credential_urls_are_rejected(url):
    with TestClient(app) as client:
        headers, _ = setup_course(client)
        result = client.put(
            "/api/v1/model-connections",
            headers=headers,
            json=dict(
                revision=0,
                name="unsafe",
                vendor="compatible",
                model="test",
                key=KEY,
                endpoint=url,
            ),
        )
        assert result.status_code == 422
        assert not client.get("/api/v1/model-connections", headers=headers).json()[
            "profiles"
        ]


@pytest.mark.parametrize("damaged", ["not-json", '{"revision":1,"profiles":[{}]}'])
def test_damaged_profiles_refuse_calls_without_falling_back_to_original_key(damaged):
    with TestClient(app) as client:
        headers, _ = setup_course(client)
        personal(client, headers, "synthetic-original-key")
        model(client, headers)
        uid = owner(client, headers)
        if damaged.startswith("{"):
            damaged = json.dumps({**json.loads(damaged), "user_id": uid})
        store.path(base_settings(), uid, profiles.NAMESPACE).write_text(
            damaged, encoding="utf-8"
        )
        assert (
            client.get("/api/v1/model-connections", headers=headers).status_code == 409
        )
        assert (
            client.post(
                "/api/v1/model-connections/active",
                headers=headers,
                json={"revision": 1, "profile_id": None},
            ).status_code
            == 409
        )
        with pytest.raises(HTTPException) as error:
            get_user_settings(uid)
        assert error.value.status_code == 409
        assert (
            get_zhipu_settings(uid).zhipu_api_key.get_secret_value()
            == "synthetic-original-key"
        )


def test_selecting_original_before_creating_profiles_keeps_valid_empty_state():
    with TestClient(app) as client:
        headers, _ = setup_course(client)
        response = client.post(
            "/api/v1/model-connections/active",
            headers=headers,
            json={"revision": 0, "profile_id": None},
        )
        assert response.status_code == 200, response.text
        assert response.json()["profiles"] == [] and response.json()["active"] is None
        assert (
            client.get("/api/v1/model-connections", headers=headers).status_code == 200
        )


@pytest.mark.parametrize("json_mode", [True, False])
def test_compatible_vision_respects_json_mode_without_vendor_only_fields(json_mode):
    with TestClient(app) as client:
        headers, _ = setup_course(client)
        model(client, headers, vendor="compatible", vision=True, json_mode=json_mode)
        calls = []

        def handle(request):
            calls.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"finish_reason": "stop", "message": {"content": '{"ok":true}'}}
                    ]
                },
            )

        provider = ZhipuProvider(
            get_user_settings(owner(client, headers)),
            transport=httpx.MockTransport(handle),
        )
        assert provider.structured(
            "检查图片",
            [],
            "返回JSON",
            connections.Probe,
            images=["data:image/png;base64,c3ludGhldGlj"],
        )[0].ok
        payload = calls[0]
        assert ("response_format" in payload) == json_mode
        assert payload["messages"][1]["content"][1]["type"] == "image_url"
        assert "thinking" not in payload and "reasoning_effort" not in payload


def test_adapter_uses_selected_model_and_checks_capabilities_and_stale_selection():
    with TestClient(app) as client:
        headers, _ = setup_course(client)
        state, profile = model(client, headers)
        uid = owner(client, headers)
        settings = get_user_settings(uid)
        calls = []

        def handle(request):
            calls.append(json.loads(request.content))
            assert request.headers["Authorization"] == "Bearer " + KEY
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": '{"ok":true}',
                                "reasoning_content": "private",
                            },
                        }
                    ]
                },
            )

        provider = ZhipuProvider(settings, transport=httpx.MockTransport(handle))
        assert provider.structured("测试", [], "返回JSON", connections.Probe)[0].ok
        assert (
            calls[0]["model"] == "deepseek-flash"
            and calls[0]["thinking"]["type"] == "enabled"
        )
        assert bank_ai.capabilities(uid)["model"] == "deepseek-flash"
        assert bank_topic_ai.fingerprint(uid)["model"] == "deepseek-flash"
        assert bank_ai.provider(uid).settings.llm_model == "deepseek-flash"
        with pytest.raises(ProviderFailure, match="图片"):
            provider.structured(
                "测试",
                [],
                "返回JSON",
                connections.Probe,
                images=["data:image/png;base64,AA=="],
            )
        assert len(calls) == 1
        assert (
            client.post(
                "/api/v1/model-connections/active",
                headers=headers,
                json={"revision": state["revision"] - 1, "profile_id": None},
            ).status_code
            == 409
        )
        client.post(
            "/api/v1/model-connections/active",
            headers=headers,
            json={"revision": state["revision"], "profile_id": None},
        )
        with pytest.raises(ProviderFailure, match="配置已变化"):
            provider.structured("测试", [], "返回JSON", connections.Probe)
        assert len(calls) == 1


@pytest.mark.parametrize("task", ["summary", "explain", "organize", "review", "custom"])
def test_note_tasks_need_consent_return_suggestions_only_and_replay_without_new_call(
    monkeypatch, task
):
    with TestClient(app) as client:
        headers, course = setup_course(client)
        model(client, headers)
        note, payload = note_input(client, headers, course)
        payload["task"] = task
        calls = []
        fake = transport(calls=calls)
        monkeypatch.setattr(
            note_assistant,
            "ZhipuProvider",
            lambda settings: ZhipuProvider(settings, transport=fake),
        )
        preview = client.post(
            "/api/v1/note-assistant/preview", headers=headers, json=payload
        )
        assert preview.status_code == 200, preview.text
        assert preview.json()["text"] == payload["text"] and not calls
        body = {
            "input": payload,
            "preview_token": preview.json()["preview_token"],
            "confirm": False,
        }
        assert (
            client.post(
                "/api/v1/note-assistant/generate", headers=headers, json=body
            ).status_code
            == 422
        )
        body["confirm"] = True
        response = client.post(
            "/api/v1/note-assistant/generate", headers=headers, json=body
        )
        assert response.status_code == 200, response.text
        assert (
            response.json()["model"] == "deepseek-flash"
            and "互不干扰" in response.json()["markdown"]
        )
        assert "internal reasoning" not in response.text
        assert (
            len(calls) == 1
            and calls[0][0] == "https://api.deepseek.com/chat/completions"
        )
        assert (
            client.post(
                "/api/v1/note-assistant/generate", headers=headers, json=body
            ).json()
            == response.json()
        )
        assert len(calls) == 1
        saved = client.get("/api/v1/notes/" + note["id"], headers=headers).json()
        assert saved["content"] == note["content"] and saved["revision"] == 1


def test_preview_is_bound_to_owner_content_revision_and_model(monkeypatch):
    with TestClient(app) as client:
        a, ca = setup_course(client)
        b, _ = setup_course(client)
        state, _ = model(client, a)
        note, payload = note_input(client, a, ca)
        preview = client.post(
            "/api/v1/note-assistant/preview", headers=a, json=payload
        ).json()
        body = {
            "input": payload,
            "preview_token": preview["preview_token"],
            "confirm": True,
        }
        assert (
            client.post(
                "/api/v1/note-assistant/generate", headers=b, json=body
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/v1/note-assistant/preview", headers=b, json=payload
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/v1/note-assistant/generate",
                headers=a,
                json={**body, "input": {**payload, "text": "tampered"}},
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/v1/model-connections/active",
                headers=a,
                json={"revision": state["revision"], "profile_id": None},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/note-assistant/generate", headers=a, json=body
            ).status_code
            == 409
        )
        state, _ = model(client, a, name="另一配置")
        preview = client.post(
            "/api/v1/note-assistant/preview", headers=a, json=payload
        ).json()
        client.patch(
            "/api/v1/notes/" + note["id"],
            headers=a,
            json={"revision": 1, "content": "新的服务端正文"},
        )
        assert (
            client.post(
                "/api/v1/note-assistant/generate",
                headers=a,
                json={**body, "preview_token": preview["preview_token"]},
            ).status_code
            == 409
        )


@pytest.mark.parametrize(
    "task,text,answer",
    [
        ("organize", "原图 [[asset:source-image|图]]", "遗漏图片的整理"),
        ("summary", "原文", "[[note:invented-id|编造链接]]"),
    ],
)
def test_changed_internal_links_are_not_adopted(monkeypatch, task, text, answer):
    with TestClient(app) as client:
        headers, course = setup_course(client)
        model(client, headers)
        note, payload = note_input(client, headers, course)
        payload.update(task=task, text=text)
        monkeypatch.setattr(
            note_assistant,
            "ZhipuProvider",
            lambda settings: ZhipuProvider(settings, transport=transport(answer)),
        )
        p = client.post(
            "/api/v1/note-assistant/preview", headers=headers, json=payload
        ).json()
        response = client.post(
            "/api/v1/note-assistant/generate",
            headers=headers,
            json={
                "input": payload,
                "preview_token": p["preview_token"],
                "confirm": True,
            },
        )
        assert response.status_code == 422, response.text
        assert (
            client.get("/api/v1/notes/" + note["id"], headers=headers).json()["content"]
            == note["content"]
        )


def test_m2_dispatch_uses_selected_profile_and_checked_evidence(monkeypatch):
    with TestClient(app) as client:
        headers, course = setup_course(client)
        model(client, headers)
        preview = prepare(client, headers, course)
        assert preview.status_code == 201, preview.text
        assert preview.json()["model"] == "deepseek-flash"
        calls = []

        def handle(request):
            packet = json.loads(request.content)
            calls.append(packet)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": json.dumps(
                                    {
                                        "status": "grounded",
                                        "answer": "五个苹果",
                                        "evidence": [{"excerpt_id": "E1"}],
                                    }
                                )
                            },
                        }
                    ]
                },
            )

        monkeypatch.setattr(
            ai_queries,
            "ZhipuProvider",
            lambda settings: ZhipuProvider(
                settings, transport=httpx.MockTransport(handle)
            ),
        )
        response = client.post(
            "/api/v1/remote-queries/" + preview.json()["id"] + "/confirm",
            headers=headers,
            json={"confirm_remote_send": True},
        )
        assert response.status_code == 202, response.text
        assert run_ai_once()
        result = client.get(
            "/api/v1/remote-queries/" + preview.json()["id"], headers=headers
        ).json()
        assert result["job"]["status"] == "SUCCEEDED", result
        assert result["result"]["result"]["citations"]
        assert len(calls) == 1 and calls[0]["model"] == "deepseek-flash"
