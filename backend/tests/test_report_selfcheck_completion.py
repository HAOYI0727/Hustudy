"""Missing exercise evidence is not guessed: unsupported questions are discarded."""

import json
import httpx
import pytest
from pydantic import ValidationError

from app.ai.providers import ProviderFailure
from app.ai.study_reports import generate_report
from app.schemas.study_reports import ReportOutput
from test_remote_ai import source, envelope
from test_study_reports import model_report, provider, request_for


@pytest.mark.parametrize("missing", [1, 3])
def test_missing_selfcheck_evidence_replaced_with_explicit_grounded_basics(missing):
    item = source()
    body = model_report(item)
    for index, check in enumerate(body["report"]["self_checks"][:missing]):
        check.pop("evidence")
        check["question"] = f"unsupported-private-question-{index}"
        check["answer"] = "unsupported-private-answer"
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=envelope(json.dumps(body)))

    result, status = generate_report(provider(handler), request_for(item), [item])
    assert status == "grounded" and len(calls) == 1
    report = result["study_report"]
    assert 3 <= len(report["self_checks"]) <= 5
    assert report["validation_notices"]
    assert "unsupported-private" not in result["answer"]
    for check in report["self_checks"]:
        assert check["citations"] and check["citations"][0]["quote"] in item["text"]
    assert any(
        check.get("generation_origin") == "rule_generated"
        for check in report["self_checks"]
    )
    assert "基础自测" in result["answer"]


def test_strict_report_contract_still_rejects_absent_evidence():
    body = model_report(source())
    body["report"]["self_checks"][0].pop("evidence")
    with pytest.raises(ValidationError):
        ReportOutput.model_validate_json(json.dumps(body))


@pytest.mark.parametrize(
    "bad",
    ["topic_evidence", "example_evidence", "selfcheck_evidence", "missing_answer"],
)
def test_completion_does_not_accept_false_citations_or_other_missing_fields(bad):
    item = source()
    body = model_report(item)
    body["report"]["self_checks"][0].pop("evidence")
    code = "INVALID_CITATION"
    if bad == "topic_evidence":
        body["report"]["topics"][0]["evidence"] = [
            {"source_id": item["source_id"], "quote": "not in source"}
        ]
    elif bad == "example_evidence":
        body["report"]["examples"][0]["evidence"] = [
            {"source_id": item["source_id"], "quote": "not in source"}
        ]
    elif bad == "selfcheck_evidence":
        body["report"]["self_checks"][1]["evidence"] = [
            {"source_id": item["source_id"], "quote": "not in source"}
        ]
    else:
        body["report"]["self_checks"][1].pop("answer")
        code = "INVALID_OUTPUT"
    with pytest.raises(ProviderFailure) as caught:
        generate_report(
            provider(lambda _: httpx.Response(200, json=envelope(json.dumps(body)))),
            request_for(item),
            [item],
        )
    assert caught.value.code == code
