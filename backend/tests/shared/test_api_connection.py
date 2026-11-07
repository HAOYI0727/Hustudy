import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import account_connection
from app.core.config import get_settings, get_user_settings, base_settings
from app.ai.providers import ProviderFailure
from tests.m1.test_materialhub import context


@pytest.mark.parametrize("ok", [True, False])
def test_probe_unpacks_provider_result_and_usage(monkeypatch, ok):
    from app.routers import connection

    monkeypatch.setattr(
        connection.ZhipuProvider,
        "structured",
        lambda *args, **kwargs: (connection.Probe(ok=ok), {"total_tokens": 10}),
    )
    if ok:
        connection.probe(get_settings())
    else:
        with pytest.raises(ProviderFailure, match="连接测试未通过"):
            connection.probe(get_settings())


def test_account_config_isolated_encrypted_live_effect_clear_and_conflicts(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        account_connection, "path", lambda _, uid: tmp_path / (uid + ".json")
    )
    with TestClient(app) as c:
        h, _ = context(c)
        other, _ = context(c)
        a = c.get("/api/v1/auth/me", headers=h).json()["id"]
        b = c.get("/api/v1/auth/me", headers=other).json()["id"]
        assert c.get("/api/v1/api-connection").status_code == 401
        key = "isolated-secret-account-A"
        result = c.put(
            "/api/v1/api-connection",
            headers=h,
            json={"revision": 0, "key": key, "model": "glm-5.3-flash"},
        )
        assert result.status_code == 200, result.text
        assert result.json()["scope"] == "account"
        assert (
            key not in result.text and key not in (tmp_path / (a + ".json")).read_text()
        )
        assert get_user_settings(a).zhipu_api_key.get_secret_value() == key
        assert not get_user_settings(b).zhipu_api_key.get_secret_value()
        assert not c.get("/api/v1/api-connection", headers=other).json()["configured"]
        assert (
            c.put(
                "/api/v1/api-connection", headers=h, json={"revision": 0, "key": key}
            ).status_code
            == 409
        )
        assert (
            c.post(
                "/api/v1/api-connection/test", headers=h, json={"revision": 1}
            ).status_code
            == 422
        )
        calls = []
        from app.routers import connection

        monkeypatch.setattr(
            connection,
            "probe",
            lambda settings: calls.append(
                (
                    settings.credential_account_id,
                    settings.zhipu_api_key.get_secret_value(),
                )
            ),
        )
        assert (
            c.post(
                "/api/v1/api-connection/test",
                headers=h,
                json={"revision": 1, "confirm": True},
            ).json()["test_status"]
            == "connected"
        )
        assert calls == [(a, key)]
        assert (
            c.put(
                "/api/v1/api-connection",
                headers=other,
                json={"revision": 0, "key": "isolated-secret-account-B"},
            ).status_code
            == 200
        )
        assert get_user_settings(a).zhipu_api_key.get_secret_value() == key
        assert (
            c.delete("/api/v1/api-connection?revision=1", headers=other).json()[
                "configured"
            ]
            is False
        )
        assert get_user_settings(a).zhipu_api_key.get_secret_value() == key
        assert (
            c.delete("/api/v1/api-connection?revision=1", headers=h).json()[
                "configured"
            ]
            is False
        )
        assert not get_user_settings(a).zhipu_api_key.get_secret_value()
        assert (
            json.loads((tmp_path / (a + ".json")).read_text())["encrypted_key"] is None
        )


def test_connection_result_not_written_over_own_changed_configuration(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        account_connection, "path", lambda _, uid: tmp_path / (uid + ".json")
    )
    from app.routers import connection

    with TestClient(app) as c:
        h, _ = context(c)
        a = c.get("/api/v1/auth/me", headers=h).json()["id"]
        c.put(
            "/api/v1/api-connection",
            headers=h,
            json={"revision": 0, "key": "isolated-secret-key"},
        )

        def changed(_):
            account_connection.write(
                base_settings(), a, {"revision": 2, "encrypted_key": None}
            )

        monkeypatch.setattr(connection, "probe", changed)
        assert (
            c.post(
                "/api/v1/api-connection/test",
                headers=h,
                json={"revision": 1, "confirm": True},
            ).status_code
            == 409
        )
        assert not c.get("/api/v1/api-connection", headers=h).json()["configured"]
