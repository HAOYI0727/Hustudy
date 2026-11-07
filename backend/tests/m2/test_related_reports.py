"""Related report goals: disposable accounts/materials and synthetic HTTP only."""

import json
from datetime import timedelta
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.main import app
from app.core.database import SessionLocal
from app.models import AIResult, ProcessingJob, RemoteQuery
from app.models.base import utc_now
from tests.m1.test_material_organization import setup_course, import_document
from tests.m2.test_remote_ai import adapter, envelope
from tests.m2.test_remote_ai import configured as configured  # noqa: F401
from tests.m2.test_ai_topics_reuse import submit
from tests.m2.test_study_reports import model_report

GOAL = "理解苹果数量的加法，整理计算步骤、例子与自测。"


@pytest.fixture
def prepared(monkeypatch, request):
    request.getfixturevalue("configured")
    with TestClient(app) as client:
        owner, course = setup_course(client)
        document, version = import_document(client, owner, course, "# 苹果\n\n两个苹果加三个苹果等于五个苹果。")
        calls = []

        def handler(request):
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            calls.append(sent)
            return httpx.Response(200, json=envelope(json.dumps(model_report(sent["sources"][0]))))

        adapter(monkeypatch, handler)

        def preview(goal=GOAL, **extra):
            response = client.post(f"/api/v1/courses/{course}/study-reports/preview", headers=owner,
                                   json={"goal": goal, "version_ids": [version], **extra})
            assert response.status_code == 201, response.text
            return response.json()

        original = submit(client, owner, preview())["result"]
        assert original["status"] == "grounded"
        yield client, owner, course, document, version, preview, original, calls


@pytest.mark.parametrize("goal", ["仅" + GOAL, "整理苹果数量加法的计算步骤、例子和自测，帮助理解。"])
def test_report_goal_suggestions_view_and_confirm_return_original_without_calls(prepared, goal):
    client, owner, _, _, _, preview, original, calls = prepared
    pending = preview(goal)
    assert pending["reusable_result"] is None
    assert pending["related_results"][0]["id"] == original["id"]
    assert pending["related_results"][0]["query"] == GOAL
    assert "hustudy:study-report" not in pending["related_results"][0]["query"]
    base = f"/api/v1/remote-queries/{pending['id']}/related-results/{original['id']}"
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(ProcessingJob))
    view = client.get(base, headers=owner)
    assert view.status_code == 200 and view.json()["query"] == GOAL
    assert view.json()["result"]["study_report"] == original["result"]["study_report"]
    for _ in range(2):
        used = client.post(base + "/reuse", headers=owner, json={"confirm_related_reuse": True})
        assert used.status_code == 200 and used.json() == view.json()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ProcessingJob)) == count
        assert db.get(RemoteQuery, pending["id"]).job_id is None
    assert len(calls) == 1


def test_report_exact_match_stays_first_and_unrelated_goal_not_ranked_by_envelope(prepared):
    client, owner, _, _, _, preview, original, calls = prepared
    pending = preview()
    assert pending["reusable_result"]["id"] == original["id"] and pending["related_results"] == []
    used = client.post(f"/api/v1/remote-queries/{pending['id']}/reuse", headers=owner,
                       json={"result_id": original["id"]})
    assert used.status_code == 200
    # Same large envelope and sources must not make unrelated goals appear similar.
    assert preview("解释TCP三次握手与网络拥塞控制")["related_results"] == []
    assert len(calls) == 1


@pytest.mark.parametrize("options", [{"study_mode": "preview"}, {"study_mode": "revision"},
                                         {"max_structure_repairs": 2}])
def test_report_mode_and_generation_settings_are_not_fuzzy(prepared, options):
    _, _, _, _, _, preview, _, calls = prepared
    assert preview("仅" + GOAL, **options)["related_results"] == []
    assert len(calls) == 1


@pytest.mark.parametrize("body", [{}, {"confirm_related_reuse": False},
                                   {"confirm_related_reuse": "true"}, {"confirm_related_reuse": 1}])
def test_report_adoption_requires_literal_confirmation(prepared, body):
    client, owner, _, _, _, preview, original, calls = prepared
    pending = preview("仅" + GOAL)
    response = client.post(f"/api/v1/remote-queries/{pending['id']}/related-results/{original['id']}/reuse",
                           headers=owner, json=body)
    assert response.status_code == 422 and len(calls) == 1


@pytest.mark.parametrize("change", ["expired", "partial", "old_prompt", "failed_job", "deleted_source",
                                   "key_cleared", "already_confirmed", "wrong_kind", "missing_report"])
def test_report_suggestion_rechecked_at_read_and_adoption(prepared, change):
    client, owner, _, document, _, preview, original, calls = prepared
    pending = preview("仅" + GOAL)
    assert pending["related_results"]
    if change == "deleted_source":
        assert client.delete(f"/api/v1/documents/{document}", headers=owner).status_code in (200, 204)
    elif change == "key_cleared":
        config = client.get("/api/v1/api-connection", headers=owner).json()
        assert client.delete(f"/api/v1/api-connection?revision={config['revision']}", headers=owner).status_code == 200
    elif change == "already_confirmed":
        assert client.post(f"/api/v1/remote-queries/{pending['id']}/confirm", headers=owner,
                           json={"confirm_remote_send": True}).status_code == 202
    else:
        with SessionLocal() as db:
            saved = db.get(AIResult, original["id"])
            data = json.loads(saved.result_json)
            if change == "expired":
                db.get(RemoteQuery, pending["id"]).expires_at = utc_now() - timedelta(seconds=1)
            elif change == "partial":
                data["partial"] = True
            elif change == "old_prompt":
                saved.prompt_version = "zhipu-study-report-v1"
            elif change == "wrong_kind":
                data["result_kind"] = "qa"
            elif change == "missing_report":
                data.pop("study_report", None)
                data.pop("study_report_sections", None)
            else:
                old = db.scalar(select(RemoteQuery).where(RemoteQuery.result_id == saved.id))
                db.get(ProcessingJob, old.job_id).status = "FAILED"
            saved.result_json = json.dumps(data)
            db.commit()
    base = f"/api/v1/remote-queries/{pending['id']}/related-results/{original['id']}"
    assert client.get(base, headers=owner).status_code == 409
    assert client.post(base + "/reuse", headers=owner, json={"confirm_related_reuse": True}).status_code == 409
    assert len(calls) == 1


def test_report_scope_account_course_and_qa_results_are_separate(prepared):
    client, owner, course, _, version, preview, original, calls = prepared
    pending = preview("仅" + GOAL)
    base = f"/api/v1/remote-queries/{pending['id']}/related-results/{original['id']}"
    other, _ = setup_course(client)
    assert client.get(base, headers=other).status_code == 404
    assert client.post(base + "/reuse", headers=other, json={"confirm_related_reuse": True}).status_code == 404
    _, second = import_document(client, owner, course, "# 新资料\n\n两个苹果加三个苹果是五个。")
    assert preview("仅" + GOAL, version_ids=[version, second])["related_results"] == []
    qa = client.post(f"/api/v1/courses/{course}/remote-queries/preview", headers=owner,
                     json={"query": "仅" + GOAL, "version_ids": [version]}).json()
    assert qa["related_results"] == []
    assert client.get(base.replace(pending['id'], qa['id']), headers=owner).status_code == 409
    own_course = client.post("/api/v1/courses", headers=owner, json={"name": "本人另一门课程"}).json()["id"]
    _, own_version = import_document(client, owner, own_course, "# 苹果\n\n两个加三个是五个。")
    own = client.post(f"/api/v1/courses/{own_course}/study-reports/preview", headers=owner,
                      json={"goal": "仅" + GOAL, "version_ids": [own_version]}).json()
    assert own["related_results"] == []
    assert client.get(base.replace(pending['id'], own['id']), headers=owner).status_code == 409
    assert len(calls) == 1


def test_report_selected_notes_are_equal_and_revision_is_checked(prepared):
    from tests.m2.test_m2_supplements import add_note

    client, owner, course, _, _, preview, _, calls = prepared
    note = add_note(client, owner, course)
    selected = {"note_ids": [note["id"]], "notes_confirmed": True}
    assert preview("仅" + GOAL, **selected)["related_results"] == []
    saved = submit(client, owner, preview(**selected))["result"]
    pending = preview("仅" + GOAL, **selected)
    assert pending["related_results"][0]["id"] == saved["id"]
    response = client.patch(f"/api/v1/notes/{note['id']}", headers=owner,
                            json={"revision": note["revision"], "content": "补充笔记已修改"})
    assert response.status_code == 200
    base = f"/api/v1/remote-queries/{pending['id']}/related-results/{saved['id']}"
    assert client.get(base, headers=owner).status_code == 409
    assert client.post(base + "/reuse", headers=owner, json={"confirm_related_reuse": True}).status_code == 409
    assert len(calls) == 2


def test_complete_multibatch_report_is_recommended_without_regenerating_parts(prepared):
    client, owner, course, _, _, preview, _, calls = prepared
    text = "\n\n".join(f"# 苹果第{i}节\n\n" + "两个苹果加三个苹果等于五个苹果。" * 160 for i in range(5))
    _, version = import_document(client, owner, course, text)
    first = preview(version_ids=[version])
    assert first["batch_progress"]["total"] > 1
    saved = submit(client, owner, first)["result"]
    assert saved["status"] == "grounded" and len(saved["result"]["study_report_sections"]) > 1
    previous_calls = len(calls)
    pending = preview("仅" + GOAL, version_ids=[version])
    assert pending["related_results"][0]["id"] == saved["id"]
    base = f"/api/v1/remote-queries/{pending['id']}/related-results/{saved['id']}"
    used = client.post(base + "/reuse", headers=owner, json={"confirm_related_reuse": True})
    assert used.status_code == 200 and used.json()["result"]["study_report_sections"] == saved["result"]["study_report_sections"]
    assert len(calls) == previous_calls
