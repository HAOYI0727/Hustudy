"""Owned reuse and per-question topics, with synthetic input and no real network."""

import json
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.core.database import SessionLocal
from app.models import ProcessingJob
from app.workers.ai_queries import run_ai_once
from test_question_drafts import setup, output
from test_remote_ai import adapter, envelope
from test_remote_ai import configured as configured  # noqa: F401
from test_study_reports import model_report
from test_material_organization import import_document


def submit(client, owner, pending):
    base = f"/api/v1/remote-queries/{pending['id']}"
    response = client.post(
        base + "/confirm", headers=owner, json={"confirm_remote_send": True}
    )
    assert response.status_code == 202, response.text
    for _ in range(50):
        assert run_ai_once()
        result = client.get(base, headers=owner).json()
        if result["job"]["status"] not in ("QUEUED", "RUNNING"):
            return result
    raise AssertionError("job did not finish")


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("kind", ["qa", "study_report"])
def test_reuse_active_qa_and_report_without_new_job_or_call(monkeypatch, kind):
    with TestClient(app) as client:
        owner, course, _, version, _, spec = setup(client)
        paths = {
            "qa": "remote-queries",
            "study_report": "study-reports",
            "question_drafts": "question-drafts",
        }
        path = f"/api/v1/courses/{course}/{paths[kind]}/preview"
        body = (
            spec
            if kind == "question_drafts"
            else {
                "version_ids": [version],
                **({"query": "苹果"} if kind == "qa" else {}),
            }
        )
        calls = []

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            calls.append(sent)
            if kind == "question_drafts":
                result = output(sent["sources"], json.loads(sent["query"])["request"])
            elif kind == "study_report":
                result = model_report(sent["sources"][0])
            else:
                result = {
                    "status": "grounded",
                    "answer": "五个苹果",
                    "evidence": [
                        {"excerpt_id": sent["sources"][0]["excerpts"][0]["excerpt_id"]}
                    ],
                }
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
            reused = client.post(
                f"/api/v1/remote-queries/{same['id']}/reuse",
                headers=owner,
                json={"result_id": saved_id},
            )
            assert reused.status_code == 200, reused.text
            assert reused.json() == finished["result"]
        assert len(calls) == 1
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(ProcessingJob)) == count
        # A hit does not remove the user's ability to explicitly regenerate.
        assert submit(client, owner, same)["result"]["id"] != saved_id
        assert len(calls) == 2


@pytest.mark.usefixtures("configured")
def test_qa_explicit_filter_and_new_versions_are_not_same_cache(monkeypatch):
    with TestClient(app) as client:
        owner, course, _, version, _, _ = setup(client)

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            return httpx.Response(
                200,
                json=envelope(
                    json.dumps(
                        {
                            "status": "grounded",
                            "answer": "五个",
                            "evidence": [
                                {
                                    "excerpt_id": sent["sources"][0]["excerpts"][0][
                                        "excerpt_id"
                                    ]
                                }
                            ],
                        }
                    )
                ),
            )

        adapter(monkeypatch, handler)
        path = f"/api/v1/courses/{course}/remote-queries/preview"
        body = {"query": "苹果", "version_ids": [version]}
        first = client.post(path, headers=owner, json=body).json()
        submit(client, owner, first)
        assert client.post(path, headers=owner, json=body).json()["reusable_result"]
        # Same retrieved text but different user selection is deliberately not a hit.
        assert (
            client.post(path, headers=owner, json={"query": "苹果"}).json()[
                "reusable_result"
            ]
            is None
        )
        _, new_version = import_document(
            client,
            owner,
            course,
            "# 苹果\n\n两个苹果加三个苹果等于五个苹果。\n\n新版本说明。",
        )
        assert (
            client.post(
                path, headers=owner, json={**body, "version_ids": [new_version]}
            ).json()["reusable_result"]
            is None
        )
