import json
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ai.providers import ZhipuProvider, ProviderFailure
from app.core.config import get_user_settings
from app.services import bank_vision, bank_ai
from test_model_connections import model, owner
from test_material_organization import setup_course
from test_bank_pdf_ocr import FIXTURES
from test_bank_vision import block


def test_deepseek_image_transcription_and_verification_keep_provider_scope(monkeypatch):
    with TestClient(app) as client:
        h, _ = setup_course(client)
        model(client, h, vision=True, thinking=False)
        uid = owner(client, h)
        caps = bank_ai.capabilities(uid)
        assert caps["vendor"] == "deepseek" and caps["vision_configured"]
        assert caps["model"] == "deepseek-flash"
        settings = get_user_settings(uid)
        requests = []

        def respond(request):
            assert request.url.host == "api.deepseek.com"
            payload = json.loads(request.content)
            requests.append(payload)
            assert payload["model"] == "deepseek-flash"
            assert payload["thinking"] == {"type": "disabled"}
            assert payload["response_format"] == {"type": "json_object"}
            assert payload["messages"][1]["content"][1]["image_url"]["url"].startswith(
                "data:image/"
            )
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": json.dumps(
                                    {
                                        "blocks": [
                                            block() | {"source_status": "visible"}
                                        ],
                                        "empty": False,
                                    }
                                )
                            },
                        }
                    ]
                },
            )

        monkeypatch.setattr(bank_vision, "local_preflight", lambda path: {})
        result = bank_vision.transcribe(
            FIXTURES / "question_bank_scan_demo.png",
            questions_only=False,
            adapter=ZhipuProvider(settings, httpx.MockTransport(respond)),
        )
        assert len(requests) == 2 and len(result["blocks"]) == 1
        # Configuration changes cannot let a previously constructed adapter send.
        model(client, h, name="另一配置", vision=False)
        with pytest.raises(ProviderFailure):
            bank_vision.provider(uid, settings.credential_revision)
