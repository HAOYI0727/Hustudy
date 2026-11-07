"""Vendor diagnostics are allowlisted and never include raw responses or keys."""

import httpx
import pytest
from pydantic import SecretStr
from app.ai.providers import ZhipuProvider, ProviderFailure
from app.core.config import Settings
from tests.m2.test_remote_ai import source


@pytest.mark.parametrize(
    "vendor,expected",
    [
        ("1113", "QUOTA_EXHAUSTED"),
        ("1302", "RATE_LIMITED"),
        ("1303", "RATE_LIMITED"),
        ("1304", "DAILY_LIMIT"),
        ("1305", "SERVICE_BUSY"),
        ("1312", "SERVICE_BUSY"),
        ("9999", "RATE_LIMITED"),
        ("private-key-value", "RATE_LIMITED"),
    ],
)
def test_provider_classifies_codes_without_exposing_body(vendor, expected):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            429,
            json={
                "error": {"code": vendor, "message": "private-key-value or raw prompt"}
            },
            headers={"Retry-After": "999999"},
        )

    provider = ZhipuProvider(
        Settings(llm_provider="zhipu", zhipu_api_key=SecretStr("private-key-value")),
        httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderFailure) as failure:
        provider.answer("问题", [source()])
    assert failure.value.code == expected and len(calls) == 1
    assert failure.value.retry_after_seconds == 3600
    assert failure.value.provider_code == (
        None if vendor == "private-key-value" else vendor
    )
    assert "private-key-value" not in str(failure.value) and "raw prompt" not in str(
        failure.value
    )


def test_unknown_error_body_budget_and_non_numeric_retry_after():
    provider = ZhipuProvider(
        Settings(llm_provider="zhipu", zhipu_api_key=SecretStr("fake-key")),
        httpx.MockTransport(
            lambda _: httpx.Response(
                429, content=b"x" * 20000, headers={"Retry-After": "not-a-number"}
            )
        ),
    )
    with pytest.raises(ProviderFailure) as failure:
        provider.answer("问题", [source()])
    assert failure.value.code == "RATE_LIMITED"
    assert (
        failure.value.provider_code is None
        and failure.value.retry_after_seconds is None
    )


@pytest.mark.parametrize("content,code,detail", [
    ('not json private-key-value', 'INVALID_JSON', '不是合法JSON'),
    ('{"status":"grounded","answer":"private response","evidence":[]}', 'INVALID_OUTPUT', '输出对象'),
    ('{"status":"grounded","private-key-value":"private response"}', 'INVALID_OUTPUT', '缺少必填字段'),
])
def test_structured_errors_are_specific_without_exposing_model_content(content, code, detail):
    from tests.m2.test_remote_ai import envelope
    # Use a distinct credential so unknown field names also exercise redaction.
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=envelope(content))
    provider = ZhipuProvider(
        Settings(llm_provider="zhipu", zhipu_api_key=SecretStr("other-fake-credential")),
        httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderFailure) as failure:
        provider.answer("问题", [source()])
    assert failure.value.code == code
    assert detail in failure.value.message
    assert "private-key-value" not in failure.value.message
    assert "private response" not in failure.value.message
    assert len(calls) == 1


def test_candidate_missing_field_diagnostic_keeps_strict_schema():
    import json
    from tests.m2.test_remote_ai import envelope
    from app.schemas.question_drafts import CandidateOutput
    content = json.dumps({"status":"grounded", "reason":None, "questions":[{
        "stem":"测试问题", "options":[], "answer":True, "rubric":[],
        "explanation":"测试解析", "evidence":[{"source_id":source()["source_id"], "quote":"原文"}]
    }]})
    provider = ZhipuProvider(
        Settings(llm_provider="zhipu", zhipu_api_key=SecretStr("fake-credential")),
        httpx.MockTransport(lambda _: httpx.Response(200, json=envelope(content))),
    )
    with pytest.raises(ProviderFailure) as failure:
        provider.structured("问题", [source()], "schema", CandidateOutput)
    assert failure.value.code == "INVALID_OUTPUT"
    assert "questions.0.original_past_question_ids：缺少必填字段" in failure.value.message
