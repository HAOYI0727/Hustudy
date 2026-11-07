"""Explicit synthetic account provisioning for existing AI test scenarios only."""

AUTO_ACCOUNT_KEYS = False
TEST_ACCOUNT_SETTINGS = None


def maybe_seed_account(client, headers):
    if not AUTO_ACCOUNT_KEYS:
        return
    from app.core.config import get_settings

    settings = TEST_ACCOUNT_SETTINGS or get_settings()
    current = client.get("/api/v1/api-connection", headers=headers).json()
    response = client.put(
        "/api/v1/api-connection",
        headers=headers,
        json={
            "revision": current["revision"],
            "model": settings.llm_model,
            "key": settings.zhipu_api_key.get_secret_value(),
        },
    )
    assert response.status_code == 200, response.text


def change_model(client, headers, model):
    current = client.get("/api/v1/api-connection", headers=headers).json()
    response = client.put(
        "/api/v1/api-connection",
        headers=headers,
        json={"revision": current["revision"], "model": model},
    )
    assert response.status_code == 200, response.text
