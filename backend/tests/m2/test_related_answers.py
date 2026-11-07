"""Disposable QA histories and synthetic provider; no real material or API calls."""

import json
from datetime import timedelta
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.core.database import SessionLocal
from app.models import AIResult, ProcessingJob, RemoteQuery
from app.models.base import utc_now
from app.services.related_answers import similarity
from tests.m2.test_remote_ai import adapter, envelope
from tests.m2.test_remote_ai import configured as configured  # noqa: F401
from tests.m1.test_material_organization import setup_course, import_document
from tests.m2.test_ai_topics_reuse import submit

QUESTION = "依据所选资料，解释事务的ACID特性，并说明UNDO和REDO的区别。"
ANSWER = "事务具有原子性、一致性、隔离性、持久性。UNDO用于撤销，REDO用于重做。"


@pytest.fixture
def prepared(monkeypatch, request):
    request.getfixturevalue("configured")
    with TestClient(app) as client:
        owner, course = setup_course(client)
        doc, version = import_document(client, owner, course, "# 事务\n\n" + ANSWER)
        calls = []

        def handler(request):
            calls.append(request)
            sent = json.loads(json.loads(request.content)["messages"][1]["content"])
            output = {"status": "grounded", "answer": ANSWER, "evidence": [
                {"excerpt_id": sent["sources"][0]["excerpts"][0]["excerpt_id"]}
            ]}
            return httpx.Response(200, json=envelope(json.dumps(output)))

        adapter(monkeypatch, handler)
        path = f"/api/v1/courses/{course}/remote-queries/preview"

        def preview(query=QUESTION, **extra):
            response = client.post(path, headers=owner, json={"query": query, "version_ids": [version], **extra})
            assert response.status_code == 201, response.text
            return response.json()

        first = preview()
        result = submit(client, owner, first)["result"]
        yield client, owner, course, doc, version, preview, result, calls


@pytest.mark.parametrize("question", [
    "仅" + QUESTION,
    "事务的ACID是什么？UNDO与REDO有什么区别？",
    "请解释事务 ACID 四个特征，以及 UNDO 和 REDO 的差异。",
])
def test_related_view_and_explicit_adoption_never_generate(prepared, question):
    client, owner, _, _, _, preview, result, calls = prepared
    pending = preview(question)
    assert pending["reusable_result"] is None
    assert pending["related_results"][0]["id"] == result["id"]
    assert pending["related_results"][0]["query"] == QUESTION
    assert "similarity" not in pending["related_results"][0]
    base = f"/api/v1/remote-queries/{pending['id']}/related-results/{result['id']}"
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(ProcessingJob))
    view = client.get(base, headers=owner)
    assert view.status_code == 200 and view.json()["query"] == QUESTION
    for _ in range(2):
        adopted = client.post(base + "/reuse", headers=owner, json={"confirm_related_reuse": True})
        assert adopted.status_code == 200 and adopted.json() == view.json()
    assert len(calls) == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ProcessingJob)) == count
        assert db.get(RemoteQuery, pending["id"]).job_id is None


def test_exact_reuse_still_takes_precedence(prepared):
    client, owner, _, _, _, preview, result, calls = prepared
    pending = preview()
    assert pending["reusable_result"]["id"] == result["id"]
    assert pending["related_results"] == []
    assert client.post(f"/api/v1/remote-queries/{pending['id']}/reuse", headers=owner,
                       json={"result_id": result["id"]}).status_code == 200
    assert len(calls) == 1


@pytest.mark.parametrize("body", [{}, {"confirm_related_reuse": False},
                                   {"confirm_related_reuse": "true"}, {"confirm_related_reuse": 1}])
def test_confirmation_is_strict(prepared, body):
    client, owner, _, _, _, preview, result, calls = prepared
    pending = preview("仅" + QUESTION)
    response = client.post(f"/api/v1/remote-queries/{pending['id']}/related-results/{result['id']}/reuse",
                           headers=owner, json=body)
    assert response.status_code == 422
    assert len(calls) == 1


@pytest.mark.parametrize("change", ["expired", "deleted_source", "partial", "old_prompt", "failed_job", "key_cleared", "already_confirmed"])
def test_candidates_are_rechecked_when_viewed_and_adopted(prepared, change):
    client, owner, _, doc, _, preview, result, calls = prepared
    pending = preview("仅" + QUESTION)
    assert pending["related_results"]
    if change == "already_confirmed":
        response = client.post(f"/api/v1/remote-queries/{pending['id']}/confirm", headers=owner,
                               json={"confirm_remote_send": True})
        assert response.status_code == 202, response.text
    elif change == "deleted_source":
        assert client.delete(f"/api/v1/documents/{doc}", headers=owner).status_code in (200, 204)
    elif change == "key_cleared":
        current = client.get('/api/v1/api-connection', headers=owner).json()
        response = client.delete(f"/api/v1/api-connection?revision={current['revision']}", headers=owner)
        assert response.status_code == 200, response.text
    else:
        with SessionLocal() as db:
            row = db.get(RemoteQuery, pending["id"])
            saved = db.get(AIResult, result["id"])
            if change == "expired":
                row.expires_at = utc_now() - timedelta(seconds=1)
            elif change == "partial":
                saved.result_json = json.dumps(json.loads(saved.result_json) | {"partial": True})
            elif change == "old_prompt":
                saved.prompt_version = "zhipu-grounded-qa-v1"
            else:
                previous = db.scalar(select(RemoteQuery).where(RemoteQuery.result_id == saved.id))
                db.get(ProcessingJob, previous.job_id).status = "FAILED"
            db.commit()
    base = f"/api/v1/remote-queries/{pending['id']}/related-results/{result['id']}"
    assert client.get(base, headers=owner).status_code == 409
    assert client.post(base + "/reuse", headers=owner,
                       json={"confirm_related_reuse": True}).status_code == 409
    assert len(calls) == 1


def test_foreign_account_course_selection_and_unrelated_question_excluded(prepared):
    client, owner, _, _, _, preview, result, calls = prepared
    other, other_course = setup_course(client)
    pending = preview("仅" + QUESTION)
    base = f"/api/v1/remote-queries/{pending['id']}/related-results/{result['id']}"
    assert client.get(base, headers=other).status_code == 404
    assert client.post(base + "/reuse", headers=other, json={"confirm_related_reuse": True}).status_code == 404
    _, different = import_document(client, owner, pending["course_id"], "# 事务另一版\n\n" + ANSWER)
    assert preview("仅" + QUESTION, version_ids=[different])["related_results"] == []
    assert preview("依据所选资料，解释TCP三次握手的概念。")["related_results"] == []
    assert client.get(base.replace(result['id'], str(uuid4())), headers=owner).status_code == 409
    own_course = client.post('/api/v1/courses', headers=owner, json={"name": "本人另一门课程"}).json()['id']
    _, own_version = import_document(client, owner, own_course, "# 事务\n\n" + ANSWER)
    own_pending = client.post(f"/api/v1/courses/{own_course}/remote-queries/preview", headers=owner,
                             json={"query": "仅" + QUESTION, "version_ids": [own_version]}).json()
    assert own_pending['related_results'] == []
    assert client.get(base.replace(pending['id'], own_pending['id']), headers=owner).status_code == 409
    foreign = client.post(f"/api/v1/courses/{other_course}/remote-queries/preview", headers=other,
                         json={"query": "仅" + QUESTION})
    # No foreign source can be used to construct a preview or leak candidates.
    assert foreign.status_code == 409
    assert len(calls) == 1


def test_settings_and_report_requests_do_not_broaden_reuse(prepared):
    client, owner, course, _, version, preview, _, calls = prepared
    assert preview("仅" + QUESTION, max_structure_repairs=2)["related_results"] == []
    report = client.post(f"/api/v1/courses/{course}/study-reports/preview", headers=owner,
                         json={"version_ids": [version], "goal": QUESTION})
    assert report.status_code == 201 and report.json()["related_results"] == []
    assert len(calls) == 1


def test_related_ranking_is_not_semantic_equivalence():
    assert similarity(QUESTION, "仅" + QUESTION) > .8
    assert similarity(QUESTION, "请说明TCP三次握手") < .42
    # Do not drop negation or silently rewrite one request into another.
    assert similarity("只解释UNDO，不讨论REDO", "解释UNDO和REDO") < 1


def test_selected_note_revision_invalidates_existing_suggestion(prepared):
    from tests.m2.test_m2_supplements import add_note

    client, owner, course, _, _, preview, _, calls = prepared
    note = add_note(client, owner, course, "事务ACID的课堂总结。")
    selected = {"note_ids": [note["id"]], "notes_confirmed": True}
    saved = submit(client, owner, preview(**selected))["result"]
    pending = preview("仅" + QUESTION, **selected)
    assert pending["related_results"][0]["id"] == saved["id"]
    changed = client.patch(f"/api/v1/notes/{note['id']}", headers=owner,
                           json={"revision": note["revision"], "content": "笔记已重新核对改写。"})
    assert changed.status_code == 200, changed.text
    base = f"/api/v1/remote-queries/{pending['id']}/related-results/{saved['id']}"
    assert client.get(base, headers=owner).status_code == 409
    assert client.post(base + '/reuse', headers=owner, json={"confirm_related_reuse": True}).status_code == 409
    assert len(calls) == 2


def test_related_list_bounded_and_original_question_deduplicated(prepared):
    client, owner, _, _, _, preview, _, calls = prepared
    for question in ["请解释事务ACID特性与UNDO、REDO的区别。", "事务ACID与UNDO及REDO分别指什么？",
                     "介绍ACID，并说明UNDO和REDO。", QUESTION]:
        submit(client, owner, preview(question))
    pending = preview("仅" + QUESTION)
    assert 1 < len(pending["related_results"]) <= 3
    questions = [item["query"] for item in pending["related_results"]]
    assert len(set(questions)) == len(questions)
    assert len(calls) == 5
