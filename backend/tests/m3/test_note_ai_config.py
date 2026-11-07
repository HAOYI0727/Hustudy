import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.services.note_ai_config import effective_settings, cipher, config_response
from app.services import material_backup
from app.models import NoteAIConfig
from app.ai.providers import ProviderFailure
from tests.m1.test_materialhub import context

KEY = "self-authored-test-key-only-123456"
ENDPOINT = "/api/v1/note-ai/config"


def test_disabled_config_keeps_legacy_key_private_and_allows_clear():
    with TestClient(app) as client:
        owner, _ = context(client)
        other, _ = context(client)
        user_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        with SessionLocal() as db:
            db.add(
                NoteAIConfig(
                    user_id=user_id,
                    model="glm-4.7-flash",
                    encrypted_key=cipher(user_id).encrypt(KEY.encode()).decode(),
                    revision=3,
                )
            )
            db.commit()
            assert "note_ai_configs" not in material_backup.snapshot(db, user_id)[0]
            with pytest.raises(ProviderFailure, match="停用"):
                effective_settings(db, user_id)
        assert client.get(ENDPOINT).status_code == 401
        result = client.get(ENDPOINT, headers=owner)
        assert result.headers["cache-control"] == "no-store"
        assert KEY not in result.text and "encrypted_key" not in result.text
        assert result.json()["has_personal_key"] and not result.json()["configured"]
        assert not client.get(ENDPOINT, headers=other).json()["has_personal_key"]
        assert client.delete(ENDPOINT + "?revision=0", headers=owner).status_code == 409
        assert client.delete(ENDPOINT + "?revision=0", headers=other).status_code == 200
        assert client.get(ENDPOINT, headers=owner).json()["has_personal_key"]
        cleared = client.delete(ENDPOINT + "?revision=3", headers=owner).json()
        assert not cleared["has_personal_key"] and not cleared["configured"]
        assert cleared["revision"] == 4


def test_config_cannot_enable_or_echo_keys():
    with TestClient(app) as client:
        owner, _ = context(client)
        payload = {"revision": 0, "model": "glm-4.7-flash", "api_key": KEY}
        assert client.put(ENDPOINT, json=payload).status_code == 401
        result = client.put(ENDPOINT, headers=owner, json=payload)
        assert result.status_code == 410 and KEY not in result.text
        assert not client.get(ENDPOINT, headers=owner).json()["has_personal_key"]
        for bad in [
            {**payload, "model": KEY},
            {**payload, "api_key": {"key": KEY}},
            {**payload, "revision": KEY, "extra": KEY},
        ]:
            result = client.put(ENDPOINT, headers=owner, json=bad)
            assert result.status_code == 422 and KEY not in result.text


def test_server_config_never_reenables_note_ai(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_provider", "zhipu")
    with TestClient(app) as client:
        owner, _ = context(client)
        caps = client.get("/api/v1/note-captures/capabilities", headers=owner).json()
        assert not caps["ai"] and "停用" in caps["ai_unavailable_reason"]
        user_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        with SessionLocal() as db:
            assert not config_response(db, user_id)["configured"]
            with pytest.raises(ProviderFailure, match="停用"):
                effective_settings(db, user_id)
        assert (
            get_settings().llm_provider == "zhipu"
        )  # M2 server configuration is untouched.
