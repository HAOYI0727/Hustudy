"""Reject semantic failures, not legitimate report detail beyond old UI limits."""

from copy import deepcopy
import json
import httpx
import pytest

from app.ai.providers import ProviderFailure
from app.ai.study_reports import generate_report
from test_remote_ai import source, envelope
from test_study_reports import model_report, provider, request_for


def rich_report():
    item = source()
    item["text"] = " ".join(f"原文{i}。" for i in range(12))
    body = model_report(item)
    report = body["report"]
    report["summary"] = "概述。" * 700
    report["learning_sequence"] = [f"学习步骤{i}" for i in range(12)]
    report["learning_goals"] = [f"学习目标{i}" for i in range(12)]
    report["prerequisites"] = [f"前置知识{i}" for i in range(12)]
    report["review_suggestions"] = [f"复习建议{i}" for i in range(12)]
    topic = report["topics"][0]
    topic["evidence"] = [
        {"source_id": item["source_id"], "quote": f"原文{i}。"} for i in range(6)
    ]
    topic["misconceptions"] = [f"误区{i}" for i in range(12)]
    topic["breakthrough_steps"] = [f"难点步骤{i}" for i in range(12)]
    report["topics"] = [{**deepcopy(topic), "name": f"知识点{i}"} for i in range(12)]
    report["topics"][0]["explanation"] = "解释。" * 1100
    report["examples"] = [
        {**deepcopy(report["examples"][0]), "question": f"例题{i}"} for i in range(4)
    ]
    return item, body


def run(body, item):
    return generate_report(
        provider(lambda _: httpx.Response(200, json=envelope(json.dumps(body)))),
        request_for(item),
        [item],
    )


def test_legitimate_longer_report_is_preserved_in_full_including_tail_citations():
    item, body = rich_report()
    result, status = run(body, item)
    assert status == "grounded"
    report = result["study_report"]
    for field in [
        "summary",
        "learning_sequence",
        "learning_goals",
        "prerequisites",
        "review_suggestions",
    ]:
        assert report[field] == body["report"][field]
    assert len(report["topics"]) == 12 and len(report["examples"]) == 4
    assert (
        report["topics"][0]["explanation"] == body["report"]["topics"][0]["explanation"]
    )
    assert len(report["topics"][0]["citations"]) == 6
    assert report["topics"][0]["citations"][-1]["quote"] == "原文5。"
    assert (
        report["topics"][0]["misconceptions"]
        == body["report"]["topics"][0]["misconceptions"]
    )
    assert (
        report["topics"][0]["breakthrough_steps"]
        == body["report"]["topics"][0]["breakthrough_steps"]
    )
    assert "学习步骤11" in result["answer"]


def test_false_tail_evidence_is_not_hidden_by_truncating_to_old_limit():
    item, body = rich_report()
    body["report"]["topics"][0]["evidence"][-1]["quote"] = "伪造的第六条引用"
    with pytest.raises(ProviderFailure) as caught:
        run(body, item)
    assert caught.value.code == "INVALID_CITATION"


def test_more_than_fifty_valid_citations_no_longer_discards_a_complete_report():
    item = source()
    item["text"] = " ".join(f"依据{i}。" for i in range(60))
    body = model_report(item)
    body["report"]["topics"][0]["evidence"] = [
        {"source_id": item["source_id"], "quote": f"依据{i}。"} for i in range(60)
    ]
    result, status = run(body, item)
    assert status == "grounded"
    assert len(result["citations"]) == 61
    assert result["study_report"]["topics"][0]["citations"][-1]["quote"] == "依据59。"


def test_real_capacity_error_shows_safe_report_field_and_counts():
    item, body = rich_report()
    body["report"]["learning_sequence"] = [f"private-step-{i}" for i in range(65)]
    with pytest.raises(ProviderFailure) as caught:
        run(body, item)
    assert caught.value.code == "INVALID_OUTPUT"
    assert "学习步骤" in caught.value.message
    assert "实际65项，上限64项" in caught.value.message
    assert "private-step" not in caught.value.message


@pytest.mark.parametrize("case", ["missing_goal", "invalid_label", "too_many_checks"])
def test_required_fields_label_origin_and_primary_check_budget_remain_strict(case):
    item, body = rich_report()
    if case == "missing_goal":
        body["report"].pop("learning_goals")
    elif case == "invalid_label":
        body["report"]["topics"][0]["labels"][0]["origin"] = "teacher_mark"
    else:
        body["report"]["self_checks"] *= 2
    with pytest.raises(ProviderFailure) as caught:
        run(body, item)
    assert caught.value.code == "INVALID_OUTPUT"
