"""Legacy candidate schema compatibility; new practice uses the user bank.

Former generation endpoint success tests were replaced by test_question_bank.py
and explicit retirement/zero-provider-call assertions below (CR-M4-BANK-01).
"""

from pathlib import Path
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models import ProcessingJob, RemoteQuery
from app.core.database import SessionLocal
from app.schemas.question_drafts import CandidateRequest
from app.services.exam_ai_context import to_exam_enums
from app.workers.ai_queries import run_ai_once
from tests.m1.test_material_organization import setup_course, import_document
from tests.m2.test_remote_ai import adapter, envelope, configured as configured  # noqa: F401


def setup(client, *, fixture=False):
    owner, course = setup_course(client)
    body = (
        (
            Path(__file__).resolve().parents[3] / "fixtures/materialhub_demo.md"
        ).read_bytes()
        if fixture
        else "# 苹果\n\n两个苹果加三个苹果等于五个苹果。"
    )
    document, version = import_document(client, owner, course, body)
    topic = client.post(
        f"/api/v1/courses/{course}/topics",
        headers=owner,
        json={"name": "进程与线程" if fixture else "加法"},
    ).json()["id"]
    payload = {
        "version_ids": [version],
        "chapter_id": version,
        "topic_ids": [topic],
        "type": "single_choice",
        "count": 1,
        "points": "2.50",
        "mode": "historical",
    }
    return owner, course, document, version, topic, payload


def output(sources, spec):
    exercises = []
    for index in range(spec["count"]):
        exercise = {
            "topic_ids": [spec["topic_ids"][index % len(spec["topic_ids"])]],
            "stem": f"第{index + 1}种情形下，两个苹果加三个苹果共有多少？",
            "options": [],
            "answer": "五个",
            "rubric": [],
            "explanation": "依据原文加法关系计算。",
            "evidence": [
                {
                    "source_id": sources[0]["source_id"],
                    "quote": (
                        sources[0]["text"]
                        if "text" in sources[0]
                        else "".join(e["text"] for e in sources[0]["excerpts"])
                    )[:100],
                }
            ],
            "original_past_question_ids": spec.get("original_past_question_ids", []),
        }
        if spec["type"] == "single_choice":
            exercise.update(
                options=[{"id": "A", "text": "五个"}, {"id": "B", "text": "六个"}],
                answer="A",
            )
        elif spec["type"] == "boolean":
            exercise["answer"] = True
        else:
            exercise["rubric"] = [
                {"criterion": "正确计算数量", "points": spec["points"]}
            ]
        exercises.append(exercise)
    return {"status": "grounded", "reason": None, "questions": exercises}


def preview(client, owner, course, payload):
    response = client.post(
        f"/api/v1/courses/{course}/question-drafts/preview", headers=owner, json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("question_type", ["single_choice", "boolean", "short_answer"])
def test_retired_candidate_endpoints_do_not_create_remote_jobs(
    monkeypatch, question_type
):
    calls = []
    adapter(monkeypatch, lambda request: calls.append(request) or httpx.Response(500))
    with TestClient(app) as client:
        owner, course, _, _, _, payload = setup(client)
        payload["type"] = question_type
        for endpoint in ("preview", "demo"):
            response = client.post(
                f"/api/v1/courses/{course}/question-drafts/{endpoint}",
                headers=owner,
                json=payload,
            )
            assert response.status_code == 410, response.text
        with SessionLocal() as db:
            assert not db.scalar(
                select(ProcessingJob.id)
                .join(RemoteQuery, RemoteQuery.job_id == ProcessingJob.id)
                .where(RemoteQuery.course_id == course)
            )
        assert calls == []


@pytest.mark.usefixtures("configured")
def test_old_consented_candidate_job_is_retired_before_dispatch(monkeypatch):
    from app.services import question_drafts
    from app.schemas.question_drafts import CandidateRequest

    calls = []
    adapter(monkeypatch, lambda request: calls.append(request) or httpx.Response(500))
    with TestClient(app) as client:
        owner, course, _, _, _, payload = setup(client)
        user_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        with SessionLocal() as db:
            sources, envelope = question_drafts.prepare(
                db, user_id, course, CandidateRequest(**payload)
            )
            from app.models.base import utc_now
            from datetime import timedelta

            row = RemoteQuery(
                user_id=user_id,
                course_id=course,
                query=question_drafts.encode(envelope),
                sources=sources,
                model="glm-5.3-flash",
                endpoint="https://open.bigmodel.cn/api/paas/v4/chat/completions",
                expires_at=utc_now() + timedelta(minutes=5),
                consented_at=utc_now(),
            )
            db.add(row)
            db.flush()
            job = ProcessingJob(
                user_id=user_id, type="AI_ANALYSIS", resource_id=row.id, max_attempts=1
            )
            db.add(job)
            db.flush()
            row.job_id = job.id
            row_id = row.id
            db.commit()
        assert (
            client.post(
                f"/api/v1/remote-queries/{row_id}/confirm",
                headers=owner,
                json={"confirm_remote_send": True},
            ).status_code
            == 410
        )
        assert run_ai_once()
        result = client.get(f"/api/v1/remote-queries/{row_id}", headers=owner).json()
        assert result["job"]["status"] == "FAILED" and result["dispatched_at"] is None
        assert result["result"]["result"]["error_code"] == "RETIRED_GENERATION"
        assert calls == []


def test_candidate_contract_decimal_limits_and_enum_bridge():
    base = {"version_ids": [str(uuid4())], "topic_ids": [str(uuid4())]}
    base["chapter_id"] = base["version_ids"][0]
    for patch in (
        {"points": "0"},
        {"points": "2.501"},
        {"count": True},
        {"mode": "variant"},
        {"chapter_id": str(uuid4())},
    ):
        with pytest.raises(ValueError):
            CandidateRequest.model_validate({**base, **patch})
    request = CandidateRequest.model_validate(
        {**base, "type": "true_false", "mode": "weakness_practice", "points": "0.30"}
    )
    assert (
        str(request.points) == "0.30"
        and request.type == "boolean"
        and request.mode == "weakness"
    )
    assert to_exam_enums(request.type, request.mode) == (
        "true_false",
        "weakness_practice",
    )
