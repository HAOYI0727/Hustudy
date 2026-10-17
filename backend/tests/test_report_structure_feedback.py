"""Optional broken links never invent evidence or hide mandatory failures."""

from copy import deepcopy
import json

import httpx
import pytest

from app.ai.providers import ProviderFailure
from app.ai.study_reports import generate_report
from test_remote_ai import source, envelope
from test_study_reports import model_report, provider, request_for


def generate(output, item):
    return generate_report(
        provider(lambda _: httpx.Response(200, json=envelope(json.dumps(output)))),
        request_for(item),
        [item],
    )


def test_duplicate_topic_names_fail_with_safe_specific_diagnostic():
    item = source()
    output = model_report(item)
    topic = output["report"]["topics"][0]
    topic["name"] = "private-model-name"
    output["report"]["topics"].append(deepcopy(topic))
    with pytest.raises(ProviderFailure) as caught:
        generate(output, item)
    assert caught.value.code == "INVALID_OUTPUT"
    assert "知识点名称重复" in caught.value.message
    assert "private-model-name" not in caught.value.message


def test_duplicate_links_removed_but_valid_link_and_explanation_retained():
    item = source()
    output = model_report(item)
    topic = output["report"]["topics"][0]
    second = deepcopy(topic)
    second["name"] = "数量核对"
    output["report"]["topics"].append(second)
    topic["related_concepts"] = [
        {"target": "数量核对", "relation": "保留的关系"},
        {"target": "数量核对", "relation": "重复的关系"},
        {"target": "加法", "relation": "自指关系"},
        {"target": "不存在", "relation": "不能猜测目标"},
    ]
    result, status = generate(output, item)
    assert status == "grounded"
    report = result["study_report"]
    assert report["topics"][0]["related_concepts"] == [
        {"target": "数量核对", "relation": "保留的关系"}
    ]
    assert "已移除3条" in report["validation_notices"][0]
    assert "不能猜测目标" not in result["answer"]


def test_removing_optional_links_does_not_bypass_exact_evidence_validation():
    item = source()
    output = model_report(item)
    topic = output["report"]["topics"][0]
    topic["related_concepts"] = [{"target": "不存在", "relation": "不能采纳"}]
    topic["evidence"] = [{"source_id": item["source_id"], "quote": "伪造原文"}]
    with pytest.raises(ProviderFailure) as caught:
        generate(output, item)
    assert caught.value.code == "INVALID_CITATION"


def test_model_cannot_forge_server_validation_notices():
    item = source()
    output = model_report(item)
    output["report"]["validation_notices"] = ["假装程序已校验"]
    with pytest.raises(ProviderFailure) as caught:
        generate(output, item)
    assert caught.value.code == "INVALID_OUTPUT"
