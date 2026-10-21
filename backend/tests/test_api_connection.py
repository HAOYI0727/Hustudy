import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import connection_store
from app.core.config import get_settings
from app.ai.providers import ProviderFailure
from test_materialhub import context


@pytest.mark.parametrize("ok", [True, False])
def test_probe_unpacks_provider_result_and_usage(monkeypatch, ok):
    from app.routers import connection

    monkeypatch.setattr(
        connection.ZhipuProvider, "structured",
        lambda *args, **kwargs: (connection.Probe(ok=ok), {"total_tokens": 10}),
    )
    if ok:
        connection.probe(get_settings())
    else:
        with pytest.raises(ProviderFailure, match="连接测试未通过"):
            connection.probe(get_settings())


def test_machine_config_encrypted_no_echo_live_effect_clear_and_conflicts(
    tmp_path, monkeypatch
):
    target = tmp_path / "connection.json"
    monkeypatch.setattr(connection_store, "path", lambda _: target)
    with TestClient(app) as c:
        h, _ = context(c)
        other, _ = context(c)
        assert c.get("/api/v1/api-connection").status_code == 401
        key = "isolated-secret-api-key-only"
        result = c.put(
            "/api/v1/api-connection",
            headers=h,
            json={"revision": 0, "key": key, "model": "glm-5.3-flash"},
        )
        assert result.status_code == 200, result.text
        assert key not in result.text and key not in target.read_text()
        assert get_settings().zhipu_api_key.get_secret_value() == key
        assert (
            c.get("/api/v1/api-connection", headers=other).json()["configured"] is True
        )
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
            connection, "probe", lambda settings: calls.append(settings.llm_model)
        )
        result = c.post(
            "/api/v1/api-connection/test",
            headers=h,
            json={"revision": 1, "confirm": True},
        )
        assert result.json()["test_status"] == "connected" and len(calls) == 1

        def failed(_):
            raise ProviderFailure("AUTH_FAILED", "密钥无效，请检查")

        monkeypatch.setattr(connection, "probe", failed)
        assert (
            c.post(
                "/api/v1/api-connection/test",
                headers=h,
                json={"revision": 1, "confirm": True},
            ).json()["test_status"]
            == "failed"
        )
        cleared = c.delete("/api/v1/api-connection?revision=1", headers=h)
        assert cleared.json()["configured"] is False
        assert not get_settings().zhipu_api_key.get_secret_value()
        assert json.loads(target.read_text())["encrypted_key"] is None


def test_connection_result_not_written_over_changed_configuration(
    tmp_path, monkeypatch
):
    target = tmp_path / "connection.json"
    monkeypatch.setattr(connection_store, "path", lambda _: target)
    from app.routers import connection

    with TestClient(app) as c:
        h, _ = context(c)
        c.put(
            "/api/v1/api-connection",
            headers=h,
            json={
                "revision": 0,
                "key": "isolated-secret-key",
                "model": "glm-5.3-flash",
            },
        )

        def changed(_):
            data = json.loads(target.read_text())
            data["revision"] = 2
            target.write_text(json.dumps(data))

        monkeypatch.setattr(connection, "probe", changed)
        assert (
            c.post(
                "/api/v1/api-connection/test",
                headers=h,
                json={"revision": 1, "confirm": True},
            ).status_code
            == 409
        )
        assert json.loads(target.read_text())["test_status"] == "not_tested"
