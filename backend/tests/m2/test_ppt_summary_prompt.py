"""Current-PPT prompt uses the existing strict report pipeline, never a real API."""

import json
import httpx
import pytest
from app.ai.providers import ProviderFailure
from app.ai.study_reports import generate_report
from app.schemas.study_reports import REPORT_PROMPT_VERSION
from tests.m2.test_study_reports import provider, model_report, request_for
from tests.m2.test_remote_ai import source, envelope


@pytest.mark.parametrize("invalid", [False, True])
def test_ppt_prompt_keeps_real_pages_and_strict_evidence(invalid):
    s = source()
    s["locator"] = {"type": "slide", "value": "3"}
    output = model_report(s)
    if invalid:
        output["report"]["self_checks"][-1]["evidence"] = [
            {"source_id": s["source_id"], "quote": "not in this slide"}
        ]

    def handler(request):
        payload = json.loads(request.content)
        prompt = payload["messages"][0]["content"]
        assert "按sources的既有顺序（所选原文页序）" in prompt
        assert "不把间隔页补成连续范围" in prompt
        assert "知识点数量以实际输入的主题为准" in prompt
        return httpx.Response(200, json=envelope(json.dumps(output)))

    if invalid:
        with pytest.raises(ProviderFailure) as error:
            generate_report(provider(handler), request_for(s), [s])
        assert error.value.code == "INVALID_CITATION"
    else:
        result, status = generate_report(provider(handler), request_for(s), [s])
        assert status == "grounded"
        assert result["prompt_version"] == REPORT_PROMPT_VERSION == "zhipu-study-report-v11"
        assert result["study_report"]["topics"][0]["citations"][0]["locator"] == s["locator"]
