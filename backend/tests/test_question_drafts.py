"""M2 candidates: deterministic output, source consent, M4 bridge, no formal exams."""

import json
from pathlib import Path
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models import Topic, PastQuestion, ExamPaper, ProcessingJob, RemoteQuery, User
from app.core.database import SessionLocal
from app.schemas.question_drafts import CandidateRequest, CANDIDATE_PREFIX
from app.services.exam_ai_context import to_exam_enums
from app.workers.ai_queries import run_ai_once
from test_material_organization import setup_course, import_document
from test_remote_ai import adapter, envelope, configured as configured  # noqa: F401


def setup(client, *, fixture=False):
    owner, course = setup_course(client)
    body = (
        (
            Path(__file__).resolve().parents[2] / "fixtures/materialhub_demo.md"
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
            "stem": f"第{index + 1}种情形下，两个苹果加三个苹果共有多少？",
            "options": [],
            "answer": "五个",
            "rubric": [],
            "explanation": "依据原文加法关系计算。",
            "evidence": [
                {
                    "source_id": sources[0]["source_id"],
                    "quote": sources[0]["text"][:100],
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
def test_candidates_all_types_consent_persistence_and_no_exam_write(
    monkeypatch, question_type
):
    with TestClient(app) as client:
        owner, course, document, version, topic, payload = setup(client)
        payload.update(type=question_type, count=2)
        calls = []

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            calls.append(sent)
            return httpx.Response(
                200,
                json=envelope(
                    json.dumps(
                        output(
                            sent["sources"],
                            sent["query"] and json.loads(sent["query"])["request"],
                        )
                    )
                ),
            )

        adapter(monkeypatch, handler)
        pending = preview(client, owner, course, payload)
        assert pending["request_kind"] == "question_drafts" and not calls
        base = f"/api/v1/remote-queries/{pending['id']}"
        for bad in (
            {},
            {"confirm_remote_send": False},
            {"confirm_remote_send": True, "count": 1},
        ):
            assert (
                client.post(base + "/confirm", headers=owner, json=bad).status_code
                == 422
            )
        queued = client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        ).json()
        assert not calls and queued["job"]["status"] == "QUEUED"
        assert (
            client.post(
                base + "/confirm", headers=owner, json={"confirm_remote_send": True}
            ).json()["job"]["id"]
            == queued["job"]["id"]
        )
        assert run_ai_once() and len(calls) == 1
        result = client.get(base, headers=owner).json()["result"]
        assert result["status"] == "grounded", result
        candidates = result["result"]["question_drafts"]
        assert len(candidates) == 2 and len({q["question_id"] for q in candidates}) == 2
        assert all(
            q["type"] == question_type
            and q["points"] == 2.5
            and q["chapter_id"] == version
            and q["topic_ids"] == [topic]
            and q["generation_status"] == "draft"
            for q in candidates
        )
        if question_type == "boolean":
            assert type(candidates[0]["answer"]) is bool
        saved = f"/api/v1/question-drafts/{result['id']}"
        assert client.get(saved, headers=owner).json() == result
        assert (
            client.get(
                f"/api/v1/courses/{course}/question-drafts", headers=owner
            ).json()[0]["id"]
            == result["id"]
        )
        other, _ = setup_course(client)
        assert client.get(saved, headers=other).status_code == 404
        with SessionLocal() as db:
            assert not db.scalars(
                select(ExamPaper).where(ExamPaper.course_id == course)
            ).all()
        client.delete(f"/api/v1/documents/{document}", headers=owner)
        assert (
            client.get(saved, headers=owner).json()["result"]["question_drafts"][0][
                "material_citations"
            ][0]["availability"]
            == "unavailable"
        )


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize(
    "case,expected",
    [
        ("count", "INVALID_COUNT"),
        ("duplicate", "DUPLICATE_QUESTION"),
        ("options", "INVALID_ANSWER"),
        ("answer", "INVALID_ANSWER"),
        ("fake_source", "INVALID_CITATION"),
        ("fake_quote", "INVALID_CITATION"),
        ("reference", "INVALID_REFERENCE"),
        ("rubric", "INVALID_RUBRIC"),
        ("boolean", "INVALID_ANSWER"),
        ("bad_json", "INVALID_JSON"),
    ],
)
def test_candidates_reject_entire_invalid_batch(monkeypatch, case, expected):
    with TestClient(app) as client:
        owner, course, _, _, _, payload = setup(client)
        payload.update(
            count=2,
            type="short_answer"
            if case == "rubric"
            else "boolean"
            if case == "boolean"
            else "single_choice",
        )

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            body = output(sent["sources"], json.loads(sent["query"])["request"])
            q = body["questions"][0]
            if case == "count":
                body["questions"].pop()
            elif case == "duplicate":
                body["questions"][1]["stem"] = q["stem"] + "！"
            elif case == "options":
                q["options"][1]["id"] = "A"
            elif case == "answer":
                q["answer"] = "Z"
            elif case == "fake_source":
                q["evidence"][0]["source_id"] = str(uuid4())
            elif case == "fake_quote":
                q["evidence"][0]["quote"] = "不在原文"
            elif case == "reference":
                q["original_past_question_ids"] = [str(uuid4())]
            elif case == "rubric":
                q["rubric"][0]["points"] = "2.49"
            elif case == "boolean":
                q["answer"] = "true"
            return httpx.Response(
                200,
                json=envelope("not-json" if case == "bad_json" else json.dumps(body)),
            )

        adapter(monkeypatch, handler)
        pending = preview(client, owner, course, payload)
        base = f"/api/v1/remote-queries/{pending['id']}"
        client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        )
        assert run_ai_once()
        result = client.get(base, headers=owner).json()["result"]
        assert result["status"] == "provider_error"
        assert result["result"]["error_code"] == expected
        assert result["result"]["question_drafts"] == []


@pytest.mark.usefixtures("configured")
def test_candidate_dependencies_reference_snapshot_and_late_change(monkeypatch):
    with TestClient(app) as client:
        owner, course, _, _, topic, payload = setup(client)
        paper = client.post(
            f"/api/v1/courses/{course}/past-papers",
            headers=owner,
            json={"title": "自制原题", "content": "1. 两个加三个苹果有几个？"},
        ).json()
        extracted = client.post(
            f"/api/v1/past-papers/{paper['id']}/extract", headers=owner
        ).json()
        reference = extracted["questions"][0]["id"]
        payload.update(
            mode="topic_variant",
            type="true_false",
            original_past_question_ids=[reference],
        )
        assert (
            client.post(
                f"/api/v1/courses/{course}/question-drafts/preview",
                headers=owner,
                json=payload,
            ).status_code
            == 404
        )
        client.post(f"/api/v1/past-papers/{paper['id']}/confirm", headers=owner)
        pending = preview(client, owner, course, payload)
        assert pending["candidate_scope"]["request"]["mode"] == "variant"
        assert pending["candidate_scope"]["request"]["type"] == "boolean"
        base = f"/api/v1/remote-queries/{pending['id']}"
        with SessionLocal() as db:
            db.get(Topic, topic).name = "修改后的Topic"
            db.commit()
        assert (
            client.post(
                base + "/confirm", headers=owner, json={"confirm_remote_send": True}
            ).status_code
            == 409
        )
        pending = preview(client, owner, course, payload)
        base = f"/api/v1/remote-queries/{pending['id']}"
        client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        )
        calls = []

        def handler(request):
            calls.append(request)
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            with SessionLocal() as db:
                db.get(PastQuestion, reference).stem += "已修改"
                db.commit()
            return httpx.Response(
                200,
                json=envelope(
                    json.dumps(
                        output(sent["sources"], json.loads(sent["query"])["request"])
                    )
                ),
            )

        adapter(monkeypatch, handler)
        assert run_ai_once() and len(calls) == 1
        result = client.get(base, headers=owner).json()["result"]
        assert (
            result["status"] == "provider_error"
            and result["result"]["question_drafts"] == []
        )


@pytest.mark.parametrize("question_type", ["single_choice", "boolean", "short_answer"])
def test_fixed_demo_only_authorized_fixture_no_jobs(question_type):
    with TestClient(app) as client:
        owner, course, _, _, _, payload = setup(client, fixture=True)
        payload.update(type=question_type, count=2)
        response = client.post(
            f"/api/v1/courses/{course}/question-drafts/demo",
            headers=owner,
            json=payload,
        )
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["model_mode"] == "demo" and result["status"] == "grounded"
        assert len(result["result"]["question_drafts"]) == 2
        with SessionLocal() as db:
            user_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
            assert not db.scalars(
                select(ProcessingJob).where(
                    ProcessingJob.user_id == user_id,
                    ProcessingJob.type == "AI_ANALYSIS",
                )
            ).all()
            assert not db.scalars(
                select(RemoteQuery).where(RemoteQuery.user_id == user_id)
            ).all()
        payload["count"] = 3
        limited = client.post(
            f"/api/v1/courses/{course}/question-drafts/demo",
            headers=owner,
            json=payload,
        ).json()
        assert limited["status"] == "insufficient_evidence"


def test_demo_unknown_input_and_foreign_scope_are_not_understood():
    with TestClient(app) as client:
        owner, course, _, _, _, payload = setup(client)
        assert (
            client.post(
                f"/api/v1/courses/{course}/question-drafts/demo",
                headers=owner,
                json=payload,
            ).json()["status"]
            == "insufficient_evidence"
        )
        other, _, _, other_version, other_topic, _ = setup(client)
        bad = {**payload, "topic_ids": [other_topic]}
        assert (
            client.post(
                f"/api/v1/courses/{course}/question-drafts/demo",
                headers=owner,
                json=bad,
            ).status_code
            == 404
        )
        bad = {**payload, "version_ids": [other_version], "chapter_id": other_version}
        assert (
            client.post(
                f"/api/v1/courses/{course}/question-drafts/demo",
                headers=owner,
                json=bad,
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/v1/courses/{course}/question-draft-context", headers=other
            ).status_code
            == 404
        )


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


@pytest.mark.usefixtures("configured")
def test_candidate_backup_roundtrip_without_dispatch(monkeypatch):
    from test_account_backups import exported, restored, empty_account

    with TestClient(app) as client:
        owner, course, _, _, _, payload = setup(client, fixture=True)
        result = client.post(
            f"/api/v1/courses/{course}/question-drafts/demo",
            headers=owner,
            json=payload,
        ).json()
        pending = preview(client, owner, course, payload)
        body, _ = exported(client, owner)
        target, _ = empty_account(client)
        uid = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        with SessionLocal() as db:
            db.delete(db.get(User, uid))
            db.commit()
        assert restored(client, target, body)["job"]["status"] == "SUCCEEDED"
        restored_result = client.get(
            f"/api/v1/question-drafts/{result['id']}", headers=target
        ).json()
        assert (
            restored_result["result"]["question_drafts"]
            == result["result"]["question_drafts"]
        )
        recovered = client.get(
            f"/api/v1/remote-queries/{pending['id']}", headers=target
        ).json()
        assert (
            recovered["candidate_scope"] == pending["candidate_scope"]
            and recovered["job"] is None
        )
        assert not run_ai_once()


@pytest.mark.usefixtures("configured")
def test_candidate_reserved_prefix_and_unselected_chunks():
    with TestClient(app) as client:
        owner, course, _, version, _, payload = setup(client)
        assert (
            client.post(
                f"/api/v1/courses/{course}/remote-queries/preview",
                headers=owner,
                json={"query": CANDIDATE_PREFIX + "{}"},
            ).status_code
            == 422
        )
        _, other_version = import_document(
            client, owner, course, "# 不选范围\n\n不允许发出的内容。"
        )
        chunk = client.get(
            f"/api/v1/versions/{other_version}/chunks", headers=owner
        ).json()[0]["id"]
        assert (
            client.post(
                f"/api/v1/courses/{course}/question-drafts/preview",
                headers=owner,
                json={**payload, "chunk_ids": [chunk]},
            ).status_code
            == 404
        )
        selected = client.get(
            f"/api/v1/versions/{version}/chunks", headers=owner
        ).json()[0]["id"]
        assert (
            preview(client, owner, course, {**payload, "chunk_ids": [selected]})[
                "sources"
            ][0]["source_id"]
            == selected
        )


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("case", ["variant", "copy", "cancel", "insufficient", "quota"])
def test_candidate_variant_and_terminal_outcomes(monkeypatch, case):
    with TestClient(app) as client:
        owner, course, _, _, _, payload = setup(client)
        paper = client.post(
            f"/api/v1/courses/{course}/past-papers",
            headers=owner,
            json={"title": "自制参考", "content": "1. 原题：苹果如何相加？"},
        ).json()
        extracted = client.post(
            f"/api/v1/past-papers/{paper['id']}/extract", headers=owner
        ).json()
        reference = extracted["questions"][0]
        client.post(f"/api/v1/past-papers/{paper['id']}/confirm", headers=owner)
        payload.update(
            mode="variant" if case in ("variant", "copy") else "weakness",
            original_past_question_ids=[reference["id"]]
            if case in ("variant", "copy")
            else [],
        )
        pending = preview(client, owner, course, payload)
        base = f"/api/v1/remote-queries/{pending['id']}"
        client.post(
            base + "/confirm", headers=owner, json={"confirm_remote_send": True}
        )
        calls = []

        def handler(request):
            calls.append(request)
            if case == "quota":
                return httpx.Response(
                    429,
                    json={"error": {"code": "1113", "message": "do not leak"}},
                    headers={"Retry-After": "60"},
                )
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            body = output(sent["sources"], json.loads(sent["query"])["request"])
            if case == "copy":
                body["questions"][0]["stem"] = reference["stem"] + "！"
            elif case == "cancel":
                assert client.post(base + "/cancel", headers=owner).status_code == 200
            elif case == "insufficient":
                body = {
                    "status": "insufficient_evidence",
                    "reason": "材料不足以支撑答案",
                    "questions": [],
                }
            return httpx.Response(200, json=envelope(json.dumps(body)))

        adapter(monkeypatch, handler)
        assert run_ai_once() and len(calls) == 1
        value = client.get(base, headers=owner).json()
        if case == "cancel":
            assert value["result"] is None and value["job"]["status"] == "CANCELLED"
        elif case == "variant":
            assert value["result"]["status"] == "grounded"
            assert value["result"]["result"]["question_drafts"][0][
                "original_past_question_ids"
            ] == [reference["id"]]
        elif case == "insufficient":
            assert (
                value["result"]["status"] == "insufficient_evidence"
                and not value["result"]["result"]["question_drafts"]
            )
        else:
            result = value["result"]["result"]
            assert result["error_code"] == (
                "DUPLICATE_QUESTION" if case == "copy" else "QUOTA_EXHAUSTED"
            )
            if case == "quota":
                assert (
                    result["provider_code"] == "1113"
                    and result["retry_after_seconds"] == 60
                )
                assert "do not leak" not in json.dumps(value)
