from fastapi.testclient import TestClient

from app.main import create_app


def test_errors_have_one_trace_id():
    with TestClient(create_app()) as client:
        for path, payload in [("/api/v1/auth/register", {}), ("/missing-route", None)]:
            response = client.post(path, json=payload)
            assert response.status_code in (404, 422)
            assert (
                response.json()["error"]["request_id"]
                == response.headers["X-Request-ID"]
            )


def test_validation_value_error_is_serializable():
    from pydantic import BaseModel, field_validator

    class Payload(BaseModel):
        value: int

        @field_validator("value")
        @classmethod
        def positive(cls, value):
            if value < 0:
                raise ValueError("must be positive")
            return value

    app = create_app()

    @app.post("/validation-probe")
    def probe(payload: Payload):
        return payload

    with TestClient(app) as client:
        response = client.post("/validation-probe", json={"value": -1})
        assert response.status_code == 422
        assert response.json()["error"]["details"]["errors"]


def test_unhandled_error_trace_does_not_expose_exception():
    app = create_app()

    @app.get("/error-probe")
    def probe():
        raise RuntimeError("private-path-or-secret")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/error-probe")
        assert response.status_code == 500
        assert "private-path-or-secret" not in response.text
        assert (
            response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
        )
