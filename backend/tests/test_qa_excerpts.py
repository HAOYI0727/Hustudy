"""No live requests: citations are selected, never reconstructed by a model."""

import hashlib
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.ai.providers import ProviderFailure, ZhipuProvider, qa_excerpts
from app.core.config import Settings
from app.schemas.remote_ai import GroundedAnswer
from test_remote_ai import source, envelope


def test_selected_excerpt_preserves_punctuation_newlines_and_original_offsets():
    item, other = source(), source()
    item["text"] = (
        "前" * 400
        + "  Higher-order function:\n函数作为参数；或返回函数。\n保留空格。  "
    )
    other["text"] = "不能误引的另一份资料。"
    calls = []

    def handler(request):
        sent = json.loads(json.loads(request.content)["messages"][1]["content"])
        calls.append(sent)
        options = sent["sources"][0]["excerpts"]
        assert "".join(o["text"] for o in options) == item["text"]
        assert options[1]["text"] == item["text"][400:]
        return httpx.Response(
            200,
            json=envelope(
                json.dumps(
                    {
                        "status": "grounded",
                        "answer": "高阶函数接受函数参数或返回函数。",
                        "evidence": [{"excerpt_id": options[1]["excerpt_id"]}],
                    }
                )
            ),
        )

    result, status = ZhipuProvider(
        Settings(llm_provider="zhipu", zhipu_api_key=SecretStr("fake-secret")),
        httpx.MockTransport(handler),
    ).answer("什么是高阶函数？", [item, other])
    assert status == "grounded" and len(calls) == 1
    (citation,) = result["citations"]
    assert citation["chunk_id"] == item["source_id"]
    assert citation["version_id"] == item["version_id"]
    assert (
        item["text"][citation["start_offset"] : citation["end_offset"]]
        == citation["quote"]
    )
    assert (
        citation["quote_hash"] == hashlib.sha256(citation["quote"].encode()).hexdigest()
    )
    assert citation["quote"] == item["text"][400:].strip()


def test_unknown_excerpt_is_not_mapped_to_an_arbitrary_source_or_retried():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json=envelope(
                json.dumps(
                    {
                        "status": "grounded",
                        "answer": "不能采纳",
                        "evidence": [{"excerpt_id": "E999"}],
                    }
                )
            ),
        )

    with pytest.raises(ProviderFailure) as caught:
        ZhipuProvider(
            Settings(llm_provider="zhipu", zhipu_api_key=SecretStr("fake-secret")),
            httpx.MockTransport(handler),
        ).answer("问题", [source()])
    assert caught.value.code == "INVALID_CITATION"
    assert len(calls) == 1


def test_excerpt_ids_are_global_within_request_and_do_not_add_source_text():
    items = [source() for _ in range(6)]
    for item in items:
        item["text"] = ("原文\n " * 500)[:1333]
    prepared, lookup = qa_excerpts(items)
    assert len(lookup) == 24
    for original, sent in zip(items, prepared):
        assert "".join(e["text"] for e in sent["excerpts"]) == original["text"]
        assert all(len(e["text"]) <= 400 for e in sent["excerpts"])
    assert len({e["excerpt_id"] for s in prepared for e in s["excerpts"]}) == 24


def test_mixed_reference_fields_are_rejected_instead_of_ignoring_fake_quote():
    with pytest.raises(ValidationError):
        GroundedAnswer.model_validate_json(
            json.dumps(
                {
                    "status": "grounded",
                    "answer": "回答",
                    "evidence": [
                        {"excerpt_id": "E1", "source_id": str(uuid4()), "quote": "伪造"}
                    ],
                }
            )
        )
