"""Owned reuse and per-question topics, with synthetic input and no real network."""

import json
from datetime import timedelta
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.models import AIResult, RemoteQuery, ProcessingJob, Topic
from app.models.base import utc_now
from app.workers.ai_queries import run_ai_once
from test_question_drafts import setup, output
from test_remote_ai import adapter, envelope
from test_remote_ai import configured as configured  # noqa: F401
from test_study_reports import model_report
from test_material_organization import setup_course, import_document


def submit(client, owner, pending):
    base = f"/api/v1/remote-queries/{pending['id']}"
    response = client.post(base + "/confirm", headers=owner, json={"confirm_remote_send": True})
    assert response.status_code == 202, response.text
    for _ in range(50):
        assert run_ai_once()
        result = client.get(base, headers=owner).json()
        if result["job"]["status"] not in ("QUEUED", "RUNNING"):
            return result
    raise AssertionError("job did not finish")


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("kind", ["qa", "study_report", "question_drafts"])
def test_reuse_all_three_tasks_without_new_job_or_call(monkeypatch, kind):
    with TestClient(app) as client:
        owner, course, _, version, _, spec = setup(client)
        paths = {"qa": "remote-queries", "study_report": "study-reports", "question_drafts": "question-drafts"}
        path = f"/api/v1/courses/{course}/{paths[kind]}/preview"
        body = spec if kind == "question_drafts" else {"version_ids": [version], **({"query": "苹果"} if kind == "qa" else {})}
        calls = []

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            calls.append(sent)
            if kind == "question_drafts":
                result = output(sent["sources"], json.loads(sent["query"])["request"])
            elif kind == "study_report":
                result = model_report(sent["sources"][0])
            else:
                result = {"status": "grounded", "answer": "五个苹果", "evidence": [{"excerpt_id": sent["sources"][0]["excerpts"][0]["excerpt_id"]}]}
            return httpx.Response(200, json=envelope(json.dumps(result)))

        adapter(monkeypatch, handler)
        pending = client.post(path, headers=owner, json=body).json()
        assert pending["reusable_result"] is None
        finished = submit(client, owner, pending)
        assert finished["result"]["status"] == "grounded", finished
        same = client.post(path, headers=owner, json=body).json()
        saved_id = finished["result"]["id"]
        assert same["reusable_result"]["id"] == saved_id
        with SessionLocal() as db:
            count = db.scalar(select(func.count()).select_from(ProcessingJob))
        for _ in range(2):
            reused = client.post(f"/api/v1/remote-queries/{same['id']}/reuse", headers=owner, json={"result_id": saved_id})
            assert reused.status_code == 200, reused.text
            assert reused.json() == finished["result"]
        assert len(calls) == 1
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(ProcessingJob)) == count
        # A hit does not remove the user's ability to explicitly regenerate.
        assert submit(client, owner, same)["result"]["id"] != saved_id
        assert len(calls) == 2


def saved_candidate(client, monkeypatch):
    owner, course, document, version, topic, spec = setup(client)

    def handler(request):
        sent = json.loads(json.loads(request.content)["messages"][1]["content"])
        return httpx.Response(200, json=envelope(json.dumps(output(sent["sources"], json.loads(sent["query"])["request"]))))

    adapter(monkeypatch, handler)
    path = f"/api/v1/courses/{course}/question-drafts/preview"
    first = client.post(path, headers=owner, json=spec).json()
    finished = submit(client, owner, first)
    assert finished["result"]["status"] == "grounded", finished
    return owner, course, document, version, topic, spec, path, finished


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("change", ["prompt", "partial", "failed", "model", "mode", "source", "settings", "other_result", "expired", "topic", "owner"])
def test_reuse_rejects_stale_or_different_inputs(monkeypatch, change):
    with TestClient(app) as client:
        owner, course, document, _, topic, spec, path, finished = saved_candidate(client, monkeypatch)
        same = client.post(path, headers=owner, json=spec).json()
        result_id = finished["result"]["id"]
        if change in ("prompt", "partial", "failed", "mode", "expired", "topic"):
            with SessionLocal() as db:
                row = db.get(AIResult, result_id)
                if change == "prompt":
                    row.prompt_version = "zhipu-question-drafts-v4"
                elif change == "partial":
                    row.result_json = json.dumps({**json.loads(row.result_json), "partial": True})
                elif change == "failed":
                    row.status = "provider_error"
                elif change == "mode":
                    row.model_mode = "demo"
                elif change == "expired":
                    db.get(RemoteQuery, same["id"]).expires_at = utc_now() - timedelta(seconds=1)
                else:
                    db.get(Topic, topic).name = "改名后的考点"
                db.commit()
        elif change == "source":
            assert client.delete(f"/api/v1/documents/{document}", headers=owner).status_code == 204
        elif change == "model":
            monkeypatch.setenv("HUSTUDY_LLM_MODEL", "glm-4.7-flash")
            get_settings.cache_clear()
        elif change == "settings":
            changed = client.post(path, headers=owner, json={**spec, "count": 2}).json()
            assert changed["reusable_result"] is None
            same = changed
        elif change == "other_result":
            result_id = str(uuid4())
        elif change == "owner":
            owner, _ = setup_course(client)
        reply = client.post(f"/api/v1/remote-queries/{same['id']}/reuse", headers=owner, json={"result_id": result_id})
        assert reply.status_code == (404 if change == "owner" else 409), reply.text


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("case", ["distinct", "multiple", "missing", "empty", "duplicate", "foreign"])
def test_topics_are_per_question_and_must_be_selected(monkeypatch, case):
    with TestClient(app) as client:
        owner, course, _, _, first, spec = setup(client)
        second = client.post(f"/api/v1/courses/{course}/topics", headers=owner, json={"name": "加法应用"}).json()["id"]
        spec.update(topic_ids=[first, second], count=2)

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            result = output(sent["sources"], json.loads(sent["query"])["request"])
            if case == "multiple":
                result["questions"][0]["topic_ids"] = [first, second]
            elif case == "missing":
                result["questions"][1].pop("topic_ids")
            elif case != "distinct":
                result["questions"][1]["topic_ids"] = {"empty": [], "duplicate": [first, first], "foreign": [str(uuid4())]}[case]
            return httpx.Response(200, json=envelope(json.dumps(result)))

        adapter(monkeypatch, handler)
        pending = client.post(f"/api/v1/courses/{course}/question-drafts/preview", headers=owner, json=spec).json()
        result = submit(client, owner, pending)["result"]
        if case in ("distinct", "multiple"):
            questions = result["result"]["question_drafts"]
            assert questions[0]["topic_ids"] == ([first, second] if case == "multiple" else [first])
            assert questions[1]["topic_ids"] == [second]
        else:
            assert result["status"] == "provider_error"
            assert result["result"]["error_code"] == "INVALID_TOPICS"
            assert result["result"]["question_drafts"] == []
            assert "第2题" in result["result"]["message"]


@pytest.mark.usefixtures("configured")
def test_qa_explicit_filter_and_new_versions_are_not_same_cache(monkeypatch):
    with TestClient(app) as client:
        owner, course, _, version, _, _ = setup(client)

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            return httpx.Response(200, json=envelope(json.dumps({"status": "grounded", "answer": "五个", "evidence": [{"excerpt_id": sent["sources"][0]["excerpts"][0]["excerpt_id"]}]})))

        adapter(monkeypatch, handler)
        path = f"/api/v1/courses/{course}/remote-queries/preview"
        body = {"query": "苹果", "version_ids": [version]}
        first = client.post(path, headers=owner, json=body).json()
        submit(client, owner, first)
        assert client.post(path, headers=owner, json=body).json()["reusable_result"]
        # Same retrieved text but different user selection is deliberately not a hit.
        assert client.post(path, headers=owner, json={"query": "苹果"}).json()["reusable_result"] is None
        _, new_version = import_document(client, owner, course, "# 苹果\n\n两个苹果加三个苹果等于五个苹果。\n\n新版本说明。")
        assert client.post(path, headers=owner, json={**body, "version_ids": [new_version]}).json()["reusable_result"] is None


@pytest.mark.usefixtures("configured")
def test_old_candidate_envelope_can_finish_without_topic_field(monkeypatch):
    with TestClient(app) as client:
        owner, course, _, _, topic, spec = setup(client)

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            result = output(sent["sources"], json.loads(sent["query"])["request"])
            result["questions"][0].pop("topic_ids")
            return httpx.Response(200, json=envelope(json.dumps(result)))

        adapter(monkeypatch, handler)
        first = client.post(f"/api/v1/courses/{course}/question-drafts/preview", headers=owner, json=spec).json()
        with SessionLocal() as db:
            row = db.get(RemoteQuery, first["id"])
            row.query = row.query.replace('"per_question_topics":true,', '')
            db.commit()
        result = submit(client, owner, first)["result"]
        assert result["status"] == "grounded", result
        assert result["result"]["question_drafts"][0]["topic_ids"] == [topic]
