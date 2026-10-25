"""Model switching is offline tested; never use a real key or live provider."""

import importlib.util
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app.ai.providers import ZhipuProvider
from app.core.config import Settings, get_settings
from app.services.remote_ai import provider_status
from app.workers.ai_queries import run_ai_once
from app.main import app
from test_remote_ai import source, envelope, payload, adapter
from test_remote_ai import configured as configured  # noqa: F401
from test_question_drafts import setup


def test_default_and_supported_models():
    assert Settings(_env_file=None).llm_model == "glm-5.3-flash"
    assert (
        Settings(llm_model="glm-4.7-flash", _env_file=None).llm_model == "glm-4.7-flash"
    )
    with pytest.raises(ValidationError):
        Settings(llm_model="arbitrary-unsupported-model", _env_file=None)


def test_new_model_request_preserves_json_budget_and_drops_reasoning():
    item = source()
    calls = []

    def handler(request):
        sent = json.loads(request.content)
        calls.append(sent)
        assert sent["thinking"]["type"] == "enabled"
        assert sent["reasoning_effort"] == "low"
        assert sent["response_format"] == {"type": "json_object"}
        assert sent["max_tokens"] == 2048 and sent["stream"] is False
        result = envelope(json.dumps(payload(item)))
        result["choices"][0]["message"]["reasoning_content"] = "private reasoning"
        return httpx.Response(200, json=result)

    provider = ZhipuProvider(
        Settings(
            llm_model="glm-5.3-flash",
            llm_provider="zhipu",
            zhipu_api_key=SecretStr("synthetic-key-only"),
        ),
        httpx.MockTransport(handler),
    )
    result, status = provider.answer("问题", [item])
    assert status == "grounded" and result["model"] == "glm-5.3-flash"
    assert len(calls) == 1 and "private reasoning" not in json.dumps(result)


def test_configure_script_defaults_and_preserves_unrelated_settings(tmp_path):
    path = Path(__file__).resolve().parents[2] / "scripts/configure_zhipu.py"
    spec = importlib.util.spec_from_file_location("configure_model_test", path)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    target = tmp_path / ".env"
    target.write_text(
        "HUSTUDY_JWT_SECRET=preserved-secret\nOTHER=preserved\nHUSTUDY_LLM_MODEL=glm-4.7-flash\n",
        encoding="utf-8",
    )
    script.configure(tmp_path, "synthetic-key-only")
    result = target.read_text()
    assert "HUSTUDY_LLM_MODEL=glm-5.3-flash" in result
    assert (
        "HUSTUDY_JWT_SECRET=preserved-secret" in result and "OTHER=preserved" in result
    )
    script.configure(tmp_path, "synthetic-key-only", "glm-4.7-flash")
    assert "HUSTUDY_LLM_MODEL=glm-4.7-flash" in target.read_text()


@pytest.mark.parametrize("queued", [False, True])
@pytest.mark.usefixtures("configured")
def test_model_switch_rejects_old_preview_or_queued_job(monkeypatch, queued):
    calls = []

    def unexpected(request):
        calls.append(request)
        return httpx.Response(500)

    adapter(monkeypatch, unexpected)
    monkeypatch.setenv("HUSTUDY_LLM_MODEL", "glm-4.7-flash")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            owner, course, _, version, _, spec = setup(client)
            pending = client.post(f"/api/v1/courses/{course}/remote-queries/preview", headers=owner, json={"query": "苹果", "version_ids": [version]}).json()
            base = f"/api/v1/remote-queries/{pending['id']}"
            if queued:
                assert (
                    client.post(
                        base + "/confirm",
                        headers=owner,
                        json={"confirm_remote_send": True},
                    ).status_code
                    == 202
                )
            from ai_account_test_support import change_model

            change_model(client, owner, "glm-5.3-flash")
            uid = client.get("/api/v1/auth/me", headers=owner).json()["id"]
            assert "vlm/glm-5.3-flash" in provider_status(uid)["documentation_url"]
            if queued:
                assert run_ai_once()
                result = client.get(base, headers=owner).json()
                assert result["result"]["result"]["error_code"] == "CONFIG_CHANGED"
                assert result["dispatched_at"] is None
            else:
                assert (
                    client.post(
                        base + "/confirm",
                        headers=owner,
                        json={"confirm_remote_send": True},
                    ).status_code
                    == 409
                )
            assert not calls
    finally:
        get_settings.cache_clear()
