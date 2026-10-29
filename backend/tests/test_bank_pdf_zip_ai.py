import io
import os
import stat
import zipfile
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr
from app.main import app
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import PastPaper, PastQuestion
from app.services import bank_ai
from app.services.bank_archives import members
from app.services.bank_parser import parse
from app.workers.bank_ai import run_bank_ai_once
from app.workers.materials import drain_jobs
from test_materialhub import context, upload
from test_preview_assets import png


GROUPED = "题目 1\n1. 什么是队头阻塞？它出现在哪里？\n这是原文提供的解答，不是模型推断。\n2. 哪种规则按到达顺序处理？\n原文写的是FIFO。\n题目 2\n1. 指出慢启动区间。\n原文区间是1—6。\n2. 说明跨页的统计方法？\n先计算第一项。\n再计算第二项，得出最终结果。"


def make_zip(items):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in items:
            z.writestr(name, body)
    return data.getvalue()


def test_grouped_unlabelled_answers_stay_out_of_stems():
    rows = parse(GROUPED)
    assert [q["number"] for q in rows] == ["1-1", "1-2", "2-1", "2-2"]
    assert rows[0]["stem"] == "什么是队头阻塞？它出现在哪里？"
    assert rows[0]["answer"] == "这是原文提供的解答，不是模型推断。"
    assert rows[-1]["answer"].endswith("得出最终结果。")
    assert "题目 2" not in rows[1]["stem"] + rows[1]["answer"]
    assert parse("题目1\n1. 说明任务。\n2. 说明协议。")[0]["answer"] is None


def test_zip_import_reports_members_and_images_do_not_start_ocr():
    with TestClient(app) as client:
        h, c = context(client)
        raw = make_zip(
            [
                ("unit/10.md", "1. 第十份资料。"),
                ("unit/2.md", GROUPED),
                ("unit/diagram.png", png()),
                ("__MACOSX/._file", b"junk"),
                ("readme.exe", b"not executed"),
            ]
        )
        response = client.post(
            f"/api/v1/courses/{c}/question-bank/archives",
            data={"mode": "ai"},
            headers=h,
            files={"file": ("bank.zip", raw, "application/zip")},
        )
        assert response.status_code == 201, response.text
        entries = response.json()["entries"]
        assert [r["path"] for r in entries if r["kind"] == "document"] == [
            "unit/2.md",
            "unit/10.md",
        ]
        assert sum(r["status"] == "skipped" for r in entries) == 2
        assert next(r for r in entries if r["kind"] == "image")["asset_id"]
        assert (
            client.get(
                f"/api/v1/courses/{c}/question-bank/image-jobs", headers=h
            ).json()
            == []
        )
        drain_jobs()
        for entry in entries:
            if entry["kind"] == "document":
                result = client.post(
                    f"/api/v1/courses/{c}/question-bank/import",
                    headers=h,
                    json={"title": entry["path"], "version_id": entry["version_id"]},
                )
                assert result.status_code == 201, result.text
        assert (
            client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()["total"]
            == 5
        )


@pytest.mark.parametrize(
    "items",
    [
        [("../escape.md", "bad")],
        [("/absolute.md", "bad")],
        [("C:/bad.md", "bad")],
        [("A.md", "ok"), ("a.md", "collision")],
        [("nested.zip", b"zip")],
        [("a.md", "a" * 100000)],
    ],
)
def test_zip_unsafe_members_are_rejected_before_upload(items):
    with pytest.raises(HTTPException) as exc:
        members(make_zip(items))
    assert exc.value.status_code == 422


def test_zip_symlink_and_too_many_files_are_rejected():
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        link = zipfile.ZipInfo("linked.md")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(link, "/etc/passwd")
    with pytest.raises(HTTPException):
        members(data.getvalue())
    with pytest.raises(HTTPException):
        members(make_zip([(f"{n}.md", "safe") for n in range(41)]))


def test_paper_filter_natural_group_order_and_parser_upgrade_keeps_old_attempts():
    with TestClient(app) as client:
        h, c = context(client)
        raw = "题目2\n" + "\n".join(
            f"{n}. 说明概念{n}。\n这是第{n}题参考解答。" for n in range(1, 12)
        )
        p = client.post(
            f"/api/v1/courses/{c}/question-bank/import",
            headers=h,
            json={"title": "分组", "content": raw},
        ).json()
        listed = client.get(
            f"/api/v1/courses/{c}/question-bank?paper_id={p['id']}", headers=h
        ).json()
        assert [q["number"] for q in listed["items"]] == [
            f"2-{n}" for n in range(1, 12)
        ]
        with SessionLocal() as db:
            old = db.get(PastPaper, p["id"])
            old.bank_meta_json = '{"parser":"bank-rules-v2"}'
            db.commit()
        new = client.post(
            f"/api/v1/courses/{c}/question-bank/import",
            headers=h,
            json={"title": "重识别", "content": raw},
        ).json()
        assert new["id"] != p["id"]
        assert len(new["questions"]) == 11
        with SessionLocal() as db:
            assert db.get(PastQuestion, p["questions"][0]["id"])
        assert (
            client.get(
                f"/api/v1/courses/{c}/question-bank?paper_id={uuid4()}", headers=h
            ).json()["items"]
            == []
        )


def configure(monkeypatch):
    settings = get_settings().model_copy(
        update={
            "llm_provider": "zhipu",
            "zhipu_api_key": SecretStr("isolated-fake-not-a-real-key"),
        }
    )
    import ai_account_test_support as support

    monkeypatch.setattr(support, "AUTO_ACCOUNT_KEYS", True)
    monkeypatch.setattr(support, "TEST_ACCOUNT_SETTINGS", settings)


def test_ai_consent_and_original_line_validation(monkeypatch):
    configure(monkeypatch)
    calls = []

    class Fake:
        def structured(self, *args, **kwargs):
            calls.append(args)
            return (
                bank_ai.Extraction.model_validate(
                    {
                        "questions": [
                            {
                                "number": "1",
                                "type": "solution",
                                "stem_lines": [1],
                                "answer_lines": [2],
                            }
                        ]
                    }
                ),
                {},
            )

    monkeypatch.setattr(bank_ai, "provider", lambda *args: Fake())
    with TestClient(app) as client:
        h, c = context(client)
        version = upload(
            client, h, c, "1. 说明协议。\n原文给定的解释。", name="source.md"
        )["resource_id"]
        drain_jobs()
        preview = client.post(
            f"/api/v1/courses/{c}/question-bank/ai-preview",
            headers=h,
            json={"title": "AI识别", "version_id": version},
        )
        assert preview.status_code == 201, preview.text
        pid = preview.json()["paper_id"]
        assert not calls and preview.json()["model"] == "glm-5.3-flash"
        assert not run_bank_ai_once() and not calls
        assert (
            client.post(
                f"/api/v1/past-papers/{pid}/ai-confirm",
                headers=h,
                json={"confirm_remote_send": False},
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"/api/v1/past-papers/{pid}/ai-confirm",
                headers=h,
                json={"confirm_remote_send": True},
            ).status_code
            == 202
        )
        assert run_bank_ai_once() and len(calls) == 1
        assert not run_bank_ai_once()
        row = client.get(
            f"/api/v1/courses/{c}/question-bank?paper_id={pid}", headers=h
        ).json()["items"][0]
        assert row["stem"] == "说明协议。" and row["answer"] == "原文给定的解释。"
        assert row["bank_data"]["citations"]


@pytest.mark.parametrize(
    "questions",
    [
        [{"number": "1", "type": "solution", "stem_lines": [999]}],
        [{"number": "1", "type": "solution", "stem_lines": [1, 2]}],
        [{"number": "1", "type": "solution", "stem_lines": [1]}],
    ],
)
def test_ai_invalid_or_incomplete_line_references_fail(questions):
    class Fake:
        def structured(self, *args, **kwargs):
            return (bank_ai.Extraction.model_validate({"questions": questions}), {})

    from app.ai.providers import ProviderFailure

    with pytest.raises(ProviderFailure):
        bank_ai.extract("1. 说明甲。\n2. 说明乙。", Fake())


def test_free_provider_http_contract_uses_structured_tuple_without_network(monkeypatch):
    import httpx
    from app.ai.providers import ZhipuProvider

    configure(monkeypatch)
    captured = []

    def respond(request):
        import json

        body = json.loads(request.content)
        captured.append(body)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "questions": [
                                        {
                                            "number": "1",
                                            "type": "solution",
                                            "stem_lines": [1],
                                            "answer_lines": [2],
                                            "explanation_lines": [],
                                        }
                                    ]
                                }
                            )
                        },
                    }
                ]
            },
        )

    from ai_account_test_support import TEST_ACCOUNT_SETTINGS

    settings = TEST_ACCOUNT_SETTINGS.model_copy(update={"llm_model": "glm-4.7-flash"})
    rows = bank_ai.extract(
        "1. 说明协议。\n原文提供的解答。",
        ZhipuProvider(settings, transport=httpx.MockTransport(respond)),
    )
    assert rows[0]["answer"] == "原文提供的解答。"
    assert captured[0]["model"] == "glm-4.7-flash"
    assert captured[0]["response_format"] == {"type": "json_object"}
    assert captured[0]["max_tokens"] == 8192


def test_ai_preview_revoked_source_and_expiry_are_not_dispatched(monkeypatch):
    import json
    from datetime import timedelta
    from app.models.base import utc_now

    configure(monkeypatch)
    with TestClient(app) as client:
        h, c = context(client)
        version = upload(client, h, c, "1. 说明内容。\n已有解答。", name="scope.md")[
            "resource_id"
        ]
        drain_jobs()
        payload = {"title": "撤权", "version_id": version}
        expired = client.post(
            f"/api/v1/courses/{c}/question-bank/ai-preview", headers=h, json=payload
        ).json()
        with SessionLocal() as db:
            row = db.get(PastPaper, expired["paper_id"])
            meta = __import__("json").loads(row.bank_meta_json)
            meta["ai_extract"]["expires_at"] = (
                utc_now() - timedelta(seconds=1)
            ).isoformat()
            row.bank_meta_json = json.dumps(meta)
            db.commit()
        assert (
            client.post(
                f"/api/v1/past-papers/{expired['paper_id']}/ai-confirm",
                headers=h,
                json={"confirm_remote_send": True},
            ).status_code
            == 409
        )
        p = client.post(
            f"/api/v1/courses/{c}/question-bank/ai-preview", headers=h, json=payload
        ).json()
        metadata = client.get(
            f"/api/v1/courses/{c}/question-bank/papers", headers=h
        ).json()
        assert all("ai_extract" not in row["metadata"] for row in metadata)
        document = client.get(f"/api/v1/versions/{version}", headers=h).json()[
            "document_id"
        ]
        assert (
            client.delete(f"/api/v1/documents/{document}", headers=h).status_code == 204
        )
        detail = client.get(
            f"/api/v1/past-papers/{p['paper_id']}/ai-preview", headers=h
        ).json()
        assert detail["status"] == "SOURCE_UNAVAILABLE" and detail["sources"] == []
        assert (
            client.post(
                f"/api/v1/past-papers/{p['paper_id']}/ai-confirm",
                headers=h,
                json={"confirm_remote_send": True},
            ).status_code
            == 404
        )
        assert not run_bank_ai_once()


def test_ai_terminal_job_and_sources_survive_account_restore(monkeypatch):
    from app.models import User
    from test_account_backups import exported, restored, empty_account

    configure(monkeypatch)

    class Fake:
        def structured(self, *args, **kwargs):
            return bank_ai.Extraction.model_validate(
                {
                    "questions": [
                        {
                            "number": "1",
                            "type": "solution",
                            "stem_lines": [1],
                            "answer_lines": [2],
                        }
                    ]
                }
            ), {}

    monkeypatch.setattr(bank_ai, "provider", lambda *args: Fake())
    with TestClient(app) as client:
        h, c = context(client)
        owner = client.get("/api/v1/auth/me", headers=h).json()["id"]
        version = upload(
            client, h, c, "1. 说明协议。\n原文提供的解答。", name="restore-ai.md"
        )["resource_id"]
        drain_jobs()
        p = client.post(
            f"/api/v1/courses/{c}/question-bank/ai-preview",
            headers=h,
            json={"title": "AI备份", "version_id": version},
        ).json()
        assert (
            client.post(
                f"/api/v1/past-papers/{p['paper_id']}/ai-confirm",
                headers=h,
                json={"confirm_remote_send": True},
            ).status_code
            == 202
        )
        assert run_bank_ai_once()
        body, _ = exported(client, h)
        with SessionLocal() as db:
            db.delete(db.get(User, owner))
            db.commit()
        target, _ = empty_account(client)
        result = restored(client, target, body)
        assert result["job"]["status"] == "SUCCEEDED", result
        questions = client.get(
            f"/api/v1/courses/{c}/question-bank?paper_id={p['paper_id']}",
            headers=target,
        ).json()["items"]
        assert len(questions) == 1 and questions[0]["answer"] == "原文提供的解答。"
        detail = client.get(
            f"/api/v1/past-papers/{p['paper_id']}/ai-preview", headers=target
        ).json()
        assert detail["status"] == "SUCCEEDED" and detail["sources"]


@pytest.mark.skipif(
    not os.environ.get("HUSTUDY_TEST_BANK_PDF"),
    reason="User PDF remains private; set explicit local path for acceptance",
)
def test_user_pdf_end_to_end_17_questions_and_cross_page_answers():
    with TestClient(app) as client:
        h, c = context(client)
        source = Path(os.environ["HUSTUDY_TEST_BANK_PDF"])
        version = upload(client, h, c, source.read_bytes(), name="6-ans.pdf")[
            "resource_id"
        ]
        drain_jobs()
        result = client.post(
            f"/api/v1/courses/{c}/question-bank/import",
            headers=h,
            json={"title": "用户PDF核对", "version_id": version},
        )
        assert result.status_code == 201, result.text
        questions = result.json()["questions"]
        assert len(questions) == 17
        lookup = {q["number"]: q for q in questions}
        assert set(lookup) == {
            f"{g}-{n}"
            for g, count in [(1, 3), (2, 11), (3, 3)]
            for n in range(1, count + 1)
        }
        assert all(q["question_type"] == "solution" and q["answer"] for q in questions)
        assert "阻塞是指" not in lookup["1-1"]["stem"]
        assert "第 7 个传输轮回" in lookup["2-8"]["answer"]
        assert "75 Mbps" in lookup["3-2"]["answer"]
        assert len(lookup["2-8"]["bank_data"]["citations"]) == 2
