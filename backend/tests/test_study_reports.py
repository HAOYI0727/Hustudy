"""M2 reports use synthetic material, fake keys and deterministic transports only."""

import json
from datetime import timedelta
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from app.main import app
from app.ai.providers import ZhipuProvider, ProviderFailure
from app.ai.study_reports import generate_report
from app.core.config import Settings
from app.core.database import SessionLocal
from app.models import RemoteQuery, ProcessingJob, AIResult
from app.models.base import utc_now
from app.schemas.study_reports import ReportEnvelope, REQUEST_PREFIX
from app.workers.ai_queries import run_ai_once
from test_material_organization import setup_course, import_document
from test_remote_ai import source, envelope, adapter
from test_remote_ai import configured as configured  # noqa: F401


def model_report(s):
    evidence = [{"source_id": s["source_id"], "quote": s["text"][:100]}]
    exercise = {
        "question": "如何计算苹果数量？",
        "answer": "两个加三个等于五个。",
        "evidence": evidence,
    }
    return {
        "status": "grounded",
        "reason": None,
        "report": {
            "summary": "苹果数量的加法。",
            "learning_goals": ["理解数量相加"],
            "prerequisites": [],
            "learning_sequence": ["读原文", "做自测"],
            "topics": [
                {
                    "name": "加法",
                    "explanation": "两个加三个得到五个。",
                    "misconceptions": ["不要漏计"],
                    "labels": [
                        {
                            "kind": "key",
                            "origin": "ai_suggestion",
                            "reason": "资料直接说明数量关系",
                        }
                    ],
                    "evidence": evidence,
                }
            ],
            "examples": [exercise],
            "self_checks": [exercise.copy() for _ in range(3)],
            "evidence": evidence,
        },
    }


def provider(handler):
    return ZhipuProvider(
        Settings(
            llm_provider="zhipu", zhipu_api_key=SecretStr("synthetic-private-key")
        ),
        httpx.MockTransport(handler),
    )


def request_for(s):
    return ReportEnvelope(
        goal="学习加法",
        scope_version_ids=[s["version_id"]],
        study_mode="systematic",
        coverage={"truncated": False},
    )


@pytest.mark.parametrize(
    "case,code",
    [
        ("goals", "INVALID_OUTPUT"),
        ("checks", "INVALID_OUTPUT"),
        ("teacher", "INVALID_OUTPUT"),
        ("extra", "INVALID_OUTPUT"),
        ("topic_citation", "INVALID_CITATION"),
        ("exercise_citation", "INVALID_CITATION"),
        ("bad_json", "INVALID_JSON"),
        ("timeout", "TIMEOUT"),
        ("length", "INCOMPLETE_OUTPUT"),
    ],
)
def test_report_rejects_invalid_sections_and_transport(case, code):
    s = source()
    output = model_report(s)
    if case == "goals":
        output["report"]["learning_goals"] = []
    elif case == "checks":
        output["report"]["self_checks"] = output["report"]["self_checks"][:2]
    elif case == "teacher":
        output["report"]["topics"][0]["labels"][0]["origin"] = "teacher_mark"
    elif case == "extra":
        output["report"]["review_status"] = "REVIEWED"
    elif case == "topic_citation":
        output["report"]["topics"][0]["evidence"] = [
            {"source_id": str(uuid4()), "quote": "假引用"}
        ]
    elif case == "exercise_citation":
        output["report"]["self_checks"][0]["evidence"] = [
            {"source_id": s["source_id"], "quote": "不在原文"}
        ]

    def handler(http_request):
        body = json.loads(http_request.content)
        assert body["max_tokens"] == 6000
        if case == "timeout":
            raise httpx.ReadTimeout("private error", request=http_request)
        return httpx.Response(
            200,
            json=envelope(
                "bad" if case == "bad_json" else json.dumps(output),
                "length" if case == "length" else "stop",
            ),
        )

    with pytest.raises(ProviderFailure) as failure:
        generate_report(provider(handler), request_for(s), [s])
    assert failure.value.code == code


def preview(client, owner, course, version, **options):
    response = client.post(
        f"/api/v1/courses/{course}/study-reports/preview",
        headers=owner,
        json={"goal": "理解加法", "version_ids": [version], **options},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.usefixtures("configured")
def test_report_consent_history_nested_citations_note_and_scope(monkeypatch):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        other, other_course = setup_course(client)
        document, version = import_document(
            client, owner, course, "# 苹果\n\n两个苹果加三个苹果等于五个苹果。"
        )
        _, foreign = import_document(
            client, other, other_course, "# 秘密\n\n其他人的秘密。"
        )
        calls = []

        def handler(request):
            body = json.loads(request.content)
            sent = json.loads(body["messages"][1]["content"])
            assert "秘密" not in request.content.decode()
            calls.append(sent)
            return httpx.Response(
                200, json=envelope(json.dumps(model_report(sent["sources"][0])))
            )

        adapter(monkeypatch, handler)
        assert (
            client.post(
                f"/api/v1/courses/{course}/study-reports/preview",
                headers=owner,
                json={"version_ids": [foreign]},
            ).status_code
            == 404
        )
        pending = preview(client, owner, course, version, study_mode="revision")
        assert (
            pending["request_kind"] == "study_report"
            and not pending["job"]
            and not calls
        )
        assert pending["report_scope"]["coverage"]["truncated"] is False
        base = f"/api/v1/remote-queries/{pending['id']}"
        for bad in (
            {},
            {"confirm_remote_send": False},
            {"confirm_remote_send": 1},
            {"confirm_remote_send": True, "goal": "replace"},
        ):
            assert (
                client.post(base + "/confirm", headers=owner, json=bad).status_code
                == 422
            )
        assert (
            client.post(
                base + "/confirm", headers=other, json={"confirm_remote_send": True}
            ).status_code
            == 404
        )
        queued = client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        ).json()
        assert not calls and queued["job"]["status"] == "QUEUED"
        replay = client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        ).json()
        assert replay["job"]["id"] == queued["job"]["id"]
        assert run_ai_once() and len(calls) == 1
        result = client.get(base, headers=owner).json()["result"]
        assert result["status"] == "grounded"
        report = result["result"]["study_report"]
        assert report["scope_version_ids"] == [version]
        assert len(report["self_checks"]) == 3 and report["learning_goals"]
        assert result["result"]["study_mode"] == "revision"
        assert report["review_status"] == "UNREVIEWED"
        citation = report["topics"][0]["citations"][0]
        assert citation["availability"] == "active" and citation["quote_hash"]
        assert "自测" in result["result"]["answer"]
        saved = f"/api/v1/study-reports/{result['id']}"
        assert client.get(saved, headers=owner).json() == result
        assert client.get(saved, headers=other).status_code == 404
        assert (
            client.get(f"/api/v1/courses/{course}/study-reports", headers=owner).json()[
                0
            ]["id"]
            == result["id"]
        )
        note_payload = {
            "course_id": course,
            "title": "待核实报告",
            "content": result["result"]["answer"],
            "citations": [
                {k: citation[k] for k in ("version_id", "chunk_id", "quote")}
            ],
        }
        assert (
            client.post("/api/v1/notes", headers=owner, json=note_payload).status_code
            == 201
        )
        assert (
            client.delete(f"/api/v1/documents/{document}", headers=owner).status_code
            == 204
        )
        stale = client.get(saved, headers=owner).json()["result"]
        assert stale["citations"][0]["availability"] == "unavailable"
        assert (
            stale["study_report"]["self_checks"][0]["citations"][0]["availability"]
            == "unavailable"
        )
        assert client.post(
            "/api/v1/notes", headers=owner, json=note_payload
        ).status_code in (404, 409, 422)


@pytest.mark.parametrize(
    "case", ["insufficient", "invalid", "cancel", "source_delete", "expiry"]
)
@pytest.mark.usefixtures("configured")
def test_report_failure_and_cancellation(monkeypatch, case):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        document, version = import_document(
            client, owner, course, "# 苹果\n\n苹果数量。"
        )
        pending = preview(client, owner, course, version)
        base = f"/api/v1/remote-queries/{pending['id']}"
        calls = []

        def handler(request):
            calls.append(request)
            if case == "cancel":
                assert client.post(base + "/cancel", headers=owner).status_code == 200
            output = {
                "status": "insufficient_evidence",
                "reason": "资料未说明运算规则",
                "report": None,
            }
            return httpx.Response(
                200, json=envelope("bad" if case == "invalid" else json.dumps(output))
            )

        adapter(monkeypatch, handler)
        if case == "expiry":
            with SessionLocal() as db:
                db.get(RemoteQuery, pending["id"]).expires_at = utc_now() - timedelta(
                    seconds=1
                )
                db.commit()
            assert (
                client.post(
                    base + "/confirm", headers=owner, json={"confirm_remote_send": True}
                ).status_code
                == 409
            )
            assert not calls
            return
        client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        )
        if case == "source_delete":
            client.delete(f"/api/v1/documents/{document}", headers=owner)
            assert not run_ai_once() and not calls
        else:
            assert run_ai_once() and len(calls) == 1
        value = client.get(base, headers=owner).json()
        if case in ("cancel", "source_delete"):
            assert value["job"]["status"] == "CANCELLED" and value["result"] is None
        else:
            assert value["result"]["status"] == (
                "provider_error" if case == "invalid" else "insufficient_evidence"
            )
            assert "study_report" not in value["result"]["result"]
            assert (
                client.get(
                    f"/api/v1/courses/{course}/study-reports", headers=owner
                ).json()[0]["id"]
                == value["result"]["id"]
            )


@pytest.mark.usefixtures("configured")
def test_report_budget_empty_scope_and_reserved_prefix():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        _, version = import_document(
            client, owner, course, "# 长文\n\n" + "苹果原文。" * 2400
        )
        pending = preview(client, owner, course, version)
        coverage = pending["report_scope"]["coverage"]
        assert coverage["truncated"] and len(pending["sources"]) <= 6
        assert sum(len(s["text"]) for s in pending["sources"]) <= 8000
        for body in (
            {"version_ids": []},
            {"version_ids": [version], "study_mode": "invalid"},
        ):
            assert (
                client.post(
                    f"/api/v1/courses/{course}/study-reports/preview",
                    headers=owner,
                    json=body,
                ).status_code
                == 422
            )
        assert (
            client.post(
                f"/api/v1/courses/{course}/remote-queries/preview",
                headers=owner,
                json={"query": REQUEST_PREFIX + "{}"},
            ).status_code
            == 422
        )
        from test_preview_assets import blank_pdf
        from app.workers.materials import drain_jobs

        empty = client.post(
            f"/api/v1/courses/{course}/documents",
            headers=owner,
            files={"file": ("empty.pdf", blank_pdf(), "application/pdf")},
        ).json()
        drain_jobs()
        response = client.post(
            f"/api/v1/courses/{course}/study-reports/preview",
            headers=owner,
            json={"version_ids": [empty["resource_id"]]},
        )
        assert response.status_code == 409
        assert response.json()["error"]["details"]["status"] == "insufficient_evidence"
        with SessionLocal() as db:
            assert not db.scalars(
                select(AIResult).where(AIResult.course_id == course)
            ).all()
            assert not db.scalars(
                select(ProcessingJob).where(
                    ProcessingJob.type == "AI_ANALYSIS",
                    ProcessingJob.user_id
                    == client.get("/api/v1/auth/me", headers=owner).json()["id"],
                )
            ).all()


@pytest.mark.usefixtures("configured")
def test_report_backup_restore_preserves_request_and_does_not_dispatch(monkeypatch):
    from app.models import User
    from test_account_backups import exported, restored, empty_account

    with TestClient(app) as client:
        owner, course = setup_course(client)
        source_user = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        _, version = import_document(
            client, owner, course, "# 苹果\n\n两个苹果加三个苹果等于五个苹果。"
        )
        calls = []

        def handler(request):
            calls.append(request)
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            return httpx.Response(
                200, json=envelope(json.dumps(model_report(sent["sources"][0])))
            )

        adapter(monkeypatch, handler)
        pending = preview(client, owner, course, version)
        base = f"/api/v1/remote-queries/{pending['id']}"
        client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        )
        assert run_ai_once() and len(calls) == 1
        original = client.get(base, headers=owner).json()
        body, _ = exported(client, owner)
        target, _ = empty_account(client)
        with SessionLocal() as db:
            db.delete(db.get(User, source_user))
            db.commit()
        done = restored(client, target, body)
        assert done["job"]["status"] == "SUCCEEDED", done
        recovered = client.get(base, headers=target).json()
        assert recovered["request_kind"] == "study_report"
        assert recovered["report_scope"] == original["report_scope"]
        assert (
            recovered["result"]["result"]["study_report"]
            == original["result"]["result"]["study_report"]
        )
        assert not run_ai_once() and len(calls) == 1


def test_report_teaching_structure_and_markdown_preserve_validated_sources():
    from copy import deepcopy
    s = source()
    output = model_report(s)
    first = output["report"]["topics"][0]
    first.update(concept_group="基础概念", breakthrough_steps=["先列出两个数量", "再计算相加结果"],
                 related_concepts=[{"target":"数量核对", "relation":"用数量核对检查加法结果"}])
    second = deepcopy(first)
    second.update(name="数量核对", related_concepts=[])
    output["report"]["topics"].append(second)
    output["report"]["review_suggestions"] = ["合上资料重新计算再核对"]
    result, status = generate_report(
        provider(lambda _: httpx.Response(200, json=envelope(json.dumps(output)))),
        request_for(s), [s],
    )
    assert status == "grounded"
    topic = result["study_report"]["topics"][0]
    assert topic["related_concepts"][0]["target"] == "数量核对"
    assert topic["citations"][0]["chunk_id"] == s["source_id"]
    for text in ["基础概念", "难点突破步骤", "用数量核对检查加法结果", "合上资料重新计算再核对"]:
        assert text in result["answer"]


@pytest.mark.parametrize("target", ["不存在的概念", "加法"])
def test_report_rejects_nonexistent_and_self_concept_links(target):
    s = source()
    output = model_report(s)
    output["report"]["topics"][0]["related_concepts"] = [{"target":target, "relation":"关系"}]
    with pytest.raises(ProviderFailure) as failure:
        generate_report(
            provider(lambda _: httpx.Response(200, json=envelope(json.dumps(output)))),
            request_for(s), [s],
        )
    assert failure.value.code == "INVALID_OUTPUT"


def test_legacy_report_without_teaching_additions_remains_compatible():
    from app.schemas.study_reports import ReportOutput
    old = ReportOutput.model_validate_json(json.dumps(model_report(source())))
    assert old.report.review_suggestions == []
    assert old.report.topics[0].concept_group is None
    assert old.report.topics[0].related_concepts == []
