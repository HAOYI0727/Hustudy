from pathlib import Path
import json
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings
from app.ai.providers import ZhipuProvider, ProviderFailure
from app.services import bank_vision, bank_ai
from app.workers.bank_ocr import run_bank_ocr_once
from tests.m4.test_bank_pdf_ocr import setup, FIXTURES


def block(number="一", continuation=False):
    return dict(
        number=number,
        kind="solution",
        stem=r"数据 $D_8D_7=01$，求 $P=\bigoplus_{i=1}^{8}D_i$。\n(1) 解释 ∑、⊕、≤。",
        options=[],
        answer=None,
        explanation="",
        continuation=continuation,
        uncertainties=[],
    )


def configured(monkeypatch):
    # Provider/worker tests must not start real OCR subprocesses.
    monkeypatch.setattr(bank_vision, "local_preflight", lambda path: {})
    s = get_settings().model_copy(update={"llm_provider": "zhipu"})
    import tests.support.ai_account_test_support as support

    monkeypatch.setattr(support, "AUTO_ACCOUNT_KEYS", True)
    monkeypatch.setattr(support, "TEST_ACCOUNT_SETTINGS", s)
    return s


def test_preflight_next_page_overlaps_current_call_and_keeps_verified_context(monkeypatch):
    from threading import Event
    from app.core.database import SessionLocal
    from app.models import PastPaper
    configured(monkeypatch)
    next_ready = Event()
    scans, calls = [], []

    def preflight(path):
        scans.append(str(path))
        if len(scans) == 2:
            next_ready.set()
        return {"ocr_status": "test", "page": len(scans)}

    def transcribe(path, previous, questions_only, **kwargs):
        if not calls:
            assert next_ready.wait(2), "next local preflight must run before current network work finishes"
            assert previous is None
        else:
            assert previous["number"] == "一"
        assert kwargs["local_hints"]["ocr_status"] == "test"
        kwargs["before_verify"]()
        calls.append(str(path))
        return {"blocks": [block(continuation=bool(previous))], "empty": False}

    monkeypatch.setattr(bank_vision, "local_preflight", preflight)
    monkeypatch.setattr(bank_vision, "transcribe", transcribe)
    with TestClient(app) as client:
        h, course, version = setup(client)
        r = enqueue(client, h, course, version, questions_only=False)
        assert r.status_code == 202, r.text
        assert run_bank_ocr_once()
        with SessionLocal() as db:
            meta = json.loads(db.get(PastPaper, r.json()["paper_id"]).bank_meta_json)
            done = meta["vision_checkpoints"]
            assert len(done) == len(calls) == len(scans) == 2
            assert all("preflight_seconds" in page["timing"] for page in done)


def test_verification_prompt_whitelist_and_example_satisfy_required_schema():
    prompt = bank_vision.VERIFY_PROMPT
    fields = next(line for line in prompt.splitlines() if "blocks每项仅含" in line)
    assert "blocks每项仅含source_status," in fields
    example = next(
        line.removeprefix("例：")
        for line in prompt.splitlines()
        if line.startswith("例：")
    )
    parsed = bank_vision.VerifiedPage.model_validate_json(example)
    assert parsed.blocks[0].source_status == "visible"
    assert bank_vision.VerifiedBlock.model_fields["source_status"].is_required()


@pytest.mark.parametrize("include_status", [True, False])
def test_real_provider_boundary_requires_verification_status_without_retry(
    monkeypatch, include_status
):
    settings = configured(monkeypatch)
    monkeypatch.setattr(bank_vision, "local_preflight", lambda path: {})
    calls = []

    def transport(request):
        calls.append(json.loads(request.content))
        item = block() | ({"source_status": "visible"} if include_status else {})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps({"blocks": [item], "empty": False})
                        },
                    }
                ]
            },
        )

    adapter = ZhipuProvider(settings, httpx.MockTransport(transport))
    if include_status:
        assert bank_vision.transcribe(
            FIXTURES / "question_bank_scan_demo.png",
            questions_only=False,
            adapter=adapter,
        )["blocks"]
    else:
        with pytest.raises(ProviderFailure, match="source_status"):
            bank_vision.transcribe(
                FIXTURES / "question_bank_scan_demo.png",
                questions_only=False,
                adapter=adapter,
            )
    assert len(calls) == 2


def test_vision_transport_keeps_latex_and_uses_base64_without_mutating_text_model(
    monkeypatch,
):
    settings = configured(monkeypatch)
    seen = []

    def transport(req):
        payload = json.loads(req.content)
        seen.append(payload)
        assert payload["model"] == "glm-5.3-flash"
        assert payload["messages"][1]["content"][1]["type"] == "image_url"
        assert payload["messages"][1]["content"][1]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )
        assert payload["thinking"]["type"] == "enabled"
        assert payload["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps({"blocks": [block()], "empty": False})
                        },
                    }
                ]
            },
        )

    adapter = ZhipuProvider(
        settings.model_copy(update={"llm_model": bank_vision.MODEL}),
        httpx.MockTransport(transport),
    )
    result = bank_vision.transcribe(
        FIXTURES / "question_bank_scan_demo.png", adapter=adapter
    )
    assert result["blocks"][0]["stem"] == block()["stem"]
    assert settings.llm_model == get_settings().llm_model and len(seen) == 1


def test_questions_only_rejects_model_answers_and_cross_page_unknown_number(
    monkeypatch,
):
    class Fake:
        def structured(self, *args, **kwargs):
            return bank_vision.Page(
                blocks=[block() | {"answer": "猜测答案"}], empty=False
            ), {}

    with pytest.raises(ProviderFailure, match="返回了答案"):
        bank_vision.transcribe(FIXTURES / "question_bank_scan_demo.png", adapter=Fake())
    with pytest.raises(ValueError, match="跨页续题"):
        bank_vision.assemble(
            [
                {
                    "asset_id": "x",
                    "result": {"blocks": [block(continuation=True)], "empty": False},
                }
            ]
        )
    text, parsed = bank_vision.assemble(
        [
            {"asset_id": "x", "result": {"blocks": [block()], "empty": False}},
            {
                "asset_id": "y",
                "result": {"blocks": [block(continuation=True)], "empty": False},
            },
        ]
    )
    assert (
        len(parsed) == 1
        and len(parsed[0]["source_images"]) == 2
        and r"\bigoplus" in text
    )
    assert parsed[0]["answer"] is None


def enqueue(client, h, c, v, **extra):
    return client.post(
        f"/api/v1/courses/{c}/question-bank/pdf/{v}/ocr",
        headers=h,
        json={
            "request_id": str(uuid4()),
            "title": "公式转写",
            "engine": "ai",
            "force_ocr": True,
            "confirm_remote_send": True,
            **extra,
        },
    )


def test_pdf_ai_requires_consent_persists_pages_and_resumes_without_resending(
    monkeypatch,
):
    configured(monkeypatch)
    calls = []

    def transcribe(path, previous, questions_only, **kwargs):
        calls.append((str(path), previous))
        if len(calls) == 2:
            raise ProviderFailure("TIMEOUT", "模拟断网")
        return {"blocks": [block(continuation=bool(previous))], "empty": False}

    monkeypatch.setattr(bank_vision, "transcribe", transcribe)
    with TestClient(app) as client:
        h, c, v = setup(client)
        assert enqueue(client, h, c, v, confirm_remote_send=False).status_code == 422
        assert not calls
        r = enqueue(client, h, c, v)
        assert r.status_code == 202, r.text
        pid = r.json()["paper_id"]
        assert run_bank_ocr_once()
        jobs = client.get(
            f"/api/v1/courses/{c}/question-bank/image-jobs", headers=h
        ).json()
        assert jobs[0]["status"] == "FAILED" and jobs[0]["completed_pages"] == 1, jobs
        r = client.post(
            f"/api/v1/past-papers/{pid}/vision-resume",
            headers=h,
            json={"confirm_remote_send": True},
        )
        assert r.status_code == 202, r.text
        assert run_bank_ocr_once()
        jobs = client.get(
            f"/api/v1/courses/{c}/question-bank/image-jobs", headers=h
        ).json()
        assert jobs[0]["status"] == "SUCCEEDED", jobs
        assert (
            len(calls) == 3
            and calls[0][0] != calls[1][0]
            and calls[1][0] == calls[2][0]
        )
        rows = client.get(
            f"/api/v1/courses/{c}/question-bank?paper_id={pid}", headers=h
        ).json()["items"]
        assert (
            len(rows) == 1
            and rows[0]["answer"] is None
            and rows[0]["status"] == "DRAFT"
        )
        assert len(rows[0]["bank_data"]["source_images"]) == 2
        assert (
            client.post(
                f"/api/v1/past-papers/{pid}/vision-resume",
                headers=h,
                json={"confirm_remote_send": True},
            ).status_code
            == 409
        )


def test_cancel_during_vision_call_prevents_checkpoint_and_next_page(monkeypatch):
    configured(monkeypatch)
    with TestClient(app) as client:
        h, c, v = setup(client)
        r = enqueue(client, h, c, v)
        pid = r.json()["paper_id"]
        calls = []

        def transcribe(*args, **kwargs):
            calls.append(1)
            assert (
                client.post(
                    f"/api/v1/past-papers/{pid}/recognition-cancel", headers=h
                ).status_code
                == 200
            )
            return {"blocks": [block()], "empty": False}

        monkeypatch.setattr(bank_vision, "transcribe", transcribe)
        assert run_bank_ocr_once() and len(calls) == 1
        jobs = client.get(
            f"/api/v1/courses/{c}/question-bank/image-jobs", headers=h
        ).json()
        assert jobs[0]["status"] == "CANCELLED" and jobs[0]["completed_pages"] == 0


def test_zip_inspection_and_selected_upload_excludes_answers_and_handles_gbk():
    import io
    import zipfile

    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        z.writestr("2021-试卷.md", "1. 解释 $D_8$。")
        z.writestr("2021-答案.md", "1. 参考解答")
    with TestClient(app) as client:
        h, c, _ = setup(client)
        route = f"/api/v1/courses/{c}/question-bank/archives"
        r = client.post(
            route + "/inspect", headers=h, files={"file": ("a.zip", data.getvalue())}
        )
        assert r.status_code == 200 and len(r.json()["entries"]) == 2
        r = client.post(
            route,
            headers=h,
            files={"file": ("a.zip", data.getvalue())},
            data={"mode": "ai", "selected_paths": json.dumps(["2021-试卷.md"])},
        )
        assert r.status_code == 201 and [x["path"] for x in r.json()["entries"]] == [
            "2021-试卷.md"
        ]
        r = client.post(
            route,
            headers=h,
            files={"file": ("a.zip", data.getvalue())},
            data={"mode": "ai", "selected_paths": json.dumps(["不存在.md"])},
        )
        assert r.status_code == 422


def test_vision_upload_automatically_schedules_semantic_topics(monkeypatch):
    from app.workers.bank_ai import run_bank_ai_once
    from app.services import bank_topic_ai

    configured(monkeypatch)
    monkeypatch.setattr(
        bank_vision,
        "transcribe",
        lambda path, previous, questions_only, **kwargs: {
            "blocks": [block(continuation=bool(previous))],
            "empty": False,
        },
    )

    class Fake:
        def structured(self, query, sources, prompt, schema, **kwargs):
            data = json.loads(sources[0]["text"])
            return bank_topic_ai.Output(
                questions=[
                    {
                        "question_id": q["question_id"],
                        "topic_ids": [data["topics"][0]["id"]],
                        "candidates": [],
                        "reason": "题目考查奇偶校验与海明码",
                    }
                    for q in data["questions"]
                ]
            ), {}

    monkeypatch.setattr(bank_ai, "provider", lambda *args: Fake())
    with TestClient(app) as client:
        h, c, v = setup(client)
        topic = client.post(
            f"/api/v1/courses/{c}/topics", headers=h, json={"name": "校验码"}
        ).json()
        r = enqueue(client, h, c, v, classify_topics=True)
        assert r.status_code == 202, r.text
        pid = r.json()["paper_id"]
        assert run_bank_ocr_once()
        assert run_bank_ai_once()
        rows = client.get(
            f"/api/v1/courses/{c}/question-bank?paper_id={pid}", headers=h
        ).json()["items"]
        assert (
            rows[0]["bank_data"]["topic_index"]["existing"][0]["topic_id"]
            == topic["id"]
        )
        assert rows[0]["bank_data"]["topic_ids"] == []
        assert rows[0]["bank_data"]["topic_index"]["auto_assigned"] is False


def test_private_zip_trial_inventory_only_when_explicitly_provided():
    import os
    import io
    from pypdf import PdfReader
    from app.services.bank_archives import members

    path = os.environ.get("HUSTUDY_TEST_BANK_ZIP")
    if not path:
        pytest.skip("private ZIP not configured")
    data = members(Path(path).read_bytes())
    papers = [(n, b) for n, k, b in data if "试卷" in n]
    answers = [n for n, k, b in data if "答案" in n]
    assert len(papers) == len(answers) == 5
    assert sum(len(PdfReader(io.BytesIO(b)).pages) for _, b in papers) == 43
    assert all(
        not p.extract_text().strip()
        for _, b in papers
        for p in PdfReader(io.BytesIO(b)).pages
    )


def test_colored_fill_answers_kept_per_blank_and_continuations():
    first = block("二.1") | {
        "kind": "fill_blank",
        "stem": "给定x=1100110、y=1100011，结果____，十六进制____。",
        "blank_answers": ["001011110010", "2F2"],
        "answer": "001011110010 || 2F2",
    }
    pages = [{"asset_id": "first", "result": {"blocks": [first], "empty": False}}]
    _, parsed = bank_vision.assemble(pages)
    assert parsed[0]["blank_answers"] == ["001011110010", "2F2"]
    assert parsed[0]["unique_answer"] is None
    assert "1100110" in parsed[0]["stem"] and "2F2" not in parsed[0]["stem"]
    follow = block("二.1", True) | {
        "kind": "fill_blank",
        "stem": "另一个空____。",
        "blank_answers": ["原文第三空"],
        "answer": "原文第三空",
    }
    pages.append({"asset_id": "second", "result": {"blocks": [follow], "empty": False}})
    assert bank_vision.assemble(pages)[1][0]["blank_answers"] == [
        "001011110010",
        "2F2",
        "原文第三空",
    ]
    follow["kind"] = "solution"
    pages[1]["result"]["blocks"] = [follow]
    assert "原文第三空" in bank_vision.assemble(pages)[1][0]["answer"]


def test_separation_prompt_and_control_characters_are_strict(monkeypatch):
    monkeypatch.setattr(
        bank_vision, "local_preflight", lambda path: {"ocr_status": "test"}
    )

    class Fake:
        def structured(self, *args, **kwargs):
            assert args[2] == bank_vision.ANSWER_PROMPT
            return bank_vision.Page(
                blocks=[block() | {"stem": "数字\x11不能损坏"}], empty=False
            ), {}

    with pytest.raises(ProviderFailure, match="控制字符"):
        bank_vision.transcribe(
            FIXTURES / "question_bank_scan_demo.png",
            questions_only=False,
            adapter=Fake(),
        )


@pytest.mark.parametrize(
    "profile,answer",
    [
        ("questions_only", None),
        ("with_answers", "原文黑白答案"),
        ("with_explanations", "原文彩色答案"),
    ],
)
def test_auto_classifies_input_and_visual_verifies_without_solving(
    monkeypatch, profile, answer
):
    monkeypatch.setattr(
        bank_vision,
        "local_preflight",
        lambda path: {
            "ocr_status": "available",
            "ocr_lines": [{"text": "1. 原文问题", "y": 0.2, "low": False}],
        },
    )
    seen = []

    class Fake:
        def structured(self, *args, **kwargs):
            seen.append(args[2])
            value = block("1") | {
                "stem": "原文问题",
                "answer": answer,
                "source_status": "visible",
            }
            if len(seen) == 1:
                return bank_vision.Page(
                    blocks=[value], empty=False, content_profile=profile
                ), {}
            assert "ocr_lines" in args[1][0]["text"]
            invented = block("2") | {
                "stem": "本页不存在的题",
                "source_status": "absent",
            }
            return bank_vision.VerifiedPage(
                blocks=[value, invented], empty=False, content_profile=profile
            ), {}

    checked = []
    result = bank_vision.transcribe(
        FIXTURES / "question_bank_scan_demo.png",
        questions_only=False,
        adapter=Fake(),
        before_verify=lambda: checked.append(True),
    )
    assert seen == [bank_vision.ANSWER_PROMPT, bank_vision.VERIFY_PROMPT]
    assert checked == [True] and len(result["blocks"]) == 1
    assert result["blocks"][0]["answer"] == answer


def test_cancel_after_first_pass_prevents_second_model_request(monkeypatch):
    monkeypatch.setattr(bank_vision, "local_preflight", lambda path: {})
    calls = []

    class Fake:
        def structured(self, *args, **kwargs):
            calls.append(True)
            return bank_vision.Page(blocks=[block()], empty=False), {}

    def cancelled():
        raise ValueError("任务已取消")

    with pytest.raises(ValueError, match="任务已取消"):
        bank_vision.transcribe(
            FIXTURES / "question_bank_scan_demo.png",
            questions_only=False,
            adapter=Fake(),
            before_verify=cancelled,
        )
    assert calls == [True]


def test_answer_only_without_question_is_explicit_failure(monkeypatch):
    monkeypatch.setattr(bank_vision, "local_preflight", lambda path: {})

    class Fake:
        def structured(self, *args, **kwargs):
            kind = (
                bank_vision.VerifiedPage
                if args[2] == bank_vision.VERIFY_PROMPT
                else bank_vision.Page
            )
            return kind(blocks=[], empty=False, content_profile="answer_only"), {}

    with pytest.raises(ProviderFailure, match="缺少对应题目"):
        bank_vision.transcribe(
            FIXTURES / "question_bank_scan_demo.png",
            questions_only=False,
            adapter=Fake(),
        )
