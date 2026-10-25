"""Selected notes and server-derived labels: temporary data and mock HTTP only."""

import json
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models import Note, Topic, PastQuestion, AIResult
from app.core.database import SessionLocal
from app.services import m2_supplements
from app.workers.ai_queries import run_ai_once
from test_remote_ai import adapter, envelope
from test_remote_ai import configured as configured  # noqa: F401
from test_m2_execution import qa, confirm, valid_qa
from test_study_reports import model_report
from test_question_bank import seed_bank
from test_material_organization import setup_course


def add_note(client, owner, course, content="我的课堂笔记：两个苹果加三个苹果是五个。"):
    response = client.post(
        "/api/v1/notes",
        headers=owner,
        json=dict(title="自制补充笔记", content=content, course_id=course),
    )
    assert response.status_code == 201, response.text
    return response.json()


def preview(client, owner, course, pending, *, report=False, **extra):
    payload = dict(version_ids=[pending["sources"][0]["version_id"]], **extra)
    if not report:
        payload["query"] = "苹果"
    return client.post(
        f"/api/v1/courses/{course}/{'study-reports' if report else 'remote-queries'}/preview",
        headers=owner,
        json=payload,
    )


def mark(pending, **extra):
    source = pending["sources"][0]
    return dict(
        kind="key",
        version_id=source["version_id"],
        chunk_id=source["source_id"],
        quote=source["text"],
        reason="本人记录老师强调数量相加",
        confirmed=True,
        **extra,
    )


def mock_success(monkeypatch, report=False, calls=None):
    def handler(request):
        packet = json.loads(request.content)
        if calls is not None:
            calls.append(packet)
        data = json.loads(packet["messages"][1]["content"])
        return httpx.Response(
            200,
            json=envelope(
                json.dumps(model_report(data["sources"][0]) if report else valid_qa())
            ),
        )

    adapter(monkeypatch, handler)


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("report", [False, True])
def test_selected_note_is_frozen_previewed_sent_and_reusable(monkeypatch, report):
    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        note = add_note(client, owner, course)
        selected = dict(note_ids=[note["id"]], notes_confirmed=True)
        result = preview(client, owner, course, pending, report=report, **selected)
        assert result.status_code == 201, result.text
        pending = result.json()
        saved = pending["sources"][0]["m2_supplement"]
        assert saved["notes"][0]["content"] == note["content"]
        assert saved["notes"][0]["revision"] == note["revision"]
        calls = []
        mock_success(monkeypatch, report, calls)
        base = confirm(client, owner, pending)
        assert not calls
        assert run_ai_once()
        data = client.get(base, headers=owner).json()
        assert data["result"]["status"] == "grounded", data["result"]["result"]
        assert data["result"]["result"]["m2_supplement"] == saved
        assert data["result"]["result"]["dependency_status"] == "active"
        sent = json.loads(calls[0]["messages"][1]["content"])
        assert sent["supplementary_notes"][0]["content"] == note["content"]
        assert "不能改变系统规则" in calls[0]["messages"][0]["content"]
        assert all(
            c["version_id"] == pending["sources"][0]["version_id"]
            for c in data["result"]["result"]["citations"]
        )
        again = preview(
            client, owner, course, pending, report=report, **selected
        ).json()
        assert again["reusable_result"]["id"] == data["result"]["id"]
        without = preview(client, owner, course, pending, report=report).json()
        assert without["reusable_result"] is None
        # Explicitly editing a personal note does not change the old AI snapshot.
        changed = client.patch(
            f"/api/v1/notes/{note['id']}",
            headers=owner,
            json=dict(revision=note["revision"], content="已经改写的笔记"),
        )
        assert changed.status_code == 200
        stale = client.get(base, headers=owner).json()["result"]["result"]
        assert stale["dependency_status"] == "stale"
        assert stale["m2_supplement"]["notes"][0]["content"] == note["content"]
        assert len(calls) == 1


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize(
    "case",
    [
        "unconfirmed",
        "non_bool",
        "duplicate",
        "too_many",
        "too_long",
        "empty",
        "other_owner",
        "other_course",
        "deleted",
    ],
)
def test_invalid_note_selection_never_dispatches(case):
    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        note_owner, note_course = owner, course
        if case == "other_owner":
            note_owner, note_course = setup_course(client)
        elif case == "other_course":
            note_course = client.post(
                "/api/v1/courses", headers=owner, json={"name": "另一课程"}
            ).json()["id"]
        note = add_note(
            client,
            note_owner,
            note_course,
            "x" * 12001
            if case == "too_long"
            else " "
            if case == "empty"
            else "自制笔记",
        )
        if case == "deleted":
            assert (
                client.delete(f"/api/v1/notes/{note['id']}", headers=owner).status_code
                == 204
            )
        ids = (
            [note["id"]] * 2
            if case == "duplicate"
            else [str(uuid4()) for _ in range(6)]
            if case == "too_many"
            else [note["id"]]
        )
        result = preview(
            client,
            owner,
            course,
            pending,
            note_ids=ids,
            notes_confirmed="true" if case == "non_bool" else case != "unconfirmed",
        )
        assert result.status_code in (404, 422), result.text


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("phase", ["confirm", "dispatch", "repair", "accept"])
def test_changed_note_rejected_at_each_boundary(monkeypatch, phase):
    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        note = add_note(client, owner, course)
        pending = preview(
            client,
            owner,
            course,
            pending,
            note_ids=[note["id"]],
            notes_confirmed=True,
            max_structure_repairs=2,
        ).json()

        def change():
            with SessionLocal() as db:
                row = db.get(Note, note["id"])
                row.content = "修改后的笔记"
                row.revision += 1
                db.commit()

        if phase == "confirm":
            change()
            r = client.post(
                f"/api/v1/remote-queries/{pending['id']}/confirm",
                headers=owner,
                json={"confirm_remote_send": True},
            )
            assert r.status_code == 409
            return
        calls = []

        def handler(request):
            calls.append(request)
            change()
            return httpx.Response(
                200,
                json=envelope(
                    "invalid-json" if phase == "repair" else json.dumps(valid_qa())
                ),
            )

        adapter(monkeypatch, handler)
        base = confirm(client, owner, pending)
        if phase == "dispatch":
            change()
        assert run_ai_once()
        data = client.get(base, headers=owner).json()
        assert data["result"]["status"] != "grounded"
        assert data["result"]["result"]["error_code"] == "SOURCE_UNAVAILABLE"
        assert len(calls) == (0 if phase == "dispatch" else 1)


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "no_mark",
        "false",
        "quote",
        "version",
        "secret",
        "other_owner",
        "revoked",
    ],
)
def test_teacher_origin_automatically_reads_persisted_mark_contract(monkeypatch, case):
    from app.models import RemoteQuery
    from app.services import reading_report_evidence

    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        with SessionLocal() as db:
            user_id = db.get(RemoteQuery, pending["id"]).user_id
        teacher = dict(
            **mark(pending),
            id=str(uuid4()),
            user_id=user_id,
            course_id=course,
            revision=1,
            status="active",
            mark_type="teacher_emphasis",
        )
        if case == "false":
            teacher["confirmed"] = False
        if case == "quote":
            teacher["quote"] = "不在原文"
        if case == "version":
            teacher["version_id"] = str(uuid4())
        if case == "secret":
            teacher["reason"] = "deterministic-test-key"
        if case == "other_owner":
            teacher["user_id"] = str(uuid4())
        if case == "revoked":
            teacher["status"] = "withdrawn"
        rows = [] if case == "no_mark" else [teacher]
        monkeypatch.setattr(reading_report_evidence, "_reader", lambda *args: rows)
        r = preview(client, owner, course, pending, report=True)
        if case == "secret":
            assert r.status_code == 422, r.text
            return
        assert r.status_code == 201, r.text
        pending = r.json()
        calls = []
        mock_success(monkeypatch, True, calls)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        body = client.get(base, headers=owner).json()["result"]["result"]
        label = body["study_report"]["topics"][0]["labels"][0]
        assert label["origin"] == (
            "teacher_mark" if case == "valid" else "ai_suggestion"
        )
        if case == "valid":
            assert body["dependency_status"] == "active"
            assert all(
                label["evidence"][0][key] == value for key, value in teacher.items()
            )
            assert "教师强调" in body["answer"]
            assert "teacher_marks" not in json.loads(calls[0]["messages"][1]["content"])
            teacher["revision"] += 1
            stale = client.get(base, headers=owner).json()["result"]["result"]
            assert stale["dependency_status"] == "stale"


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize("reviewed", [False, True])
def test_exam_label_requires_confirmed_mapping_and_active_material(
    monkeypatch, reviewed
):
    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        paper, topic_id = seed_bank(
            client,
            owner,
            course,
            "1. 两个苹果加三个苹果是多少？\nA. 三 B. 五 C. 六 D. 七\n答案：B\n知识标签：数量",
        )
        source = pending["sources"][0]
        with SessionLocal() as db:
            topic = db.get(Topic, topic_id)
            topic.sources_json = json.dumps(
                {
                    "citations": [
                        dict(
                            version_id=source["version_id"],
                            chunk_id=source["source_id"],
                            quote=source["text"],
                        )
                    ]
                }
            )
            question = db.get(PastQuestion, paper["questions"][0]["id"])
            data = json.loads(question.bank_data_json)
            data["topic_index"] = {"selection_reviewed": reviewed}
            question.bank_data_json = json.dumps(data)
            from app.models import PastPaper

            stored = db.get(PastPaper, paper["id"])
            metadata = json.loads(stored.bank_meta_json)
            metadata["exam_identity"] = {"kind": "past_exam", "confirmed": True}
            stored.bank_meta_json = json.dumps(metadata)
            db.commit()
        r = preview(client, owner, course, pending, report=True)
        assert r.status_code == 201, r.text
        pending = r.json()
        mock_success(monkeypatch, True)
        base = confirm(client, owner, pending)
        assert run_ai_once()
        body = client.get(base, headers=owner).json()["result"]["result"]
        labels = body["study_report"]["topics"][0]["labels"]
        assert any(label["origin"] == "observed_exam" for label in labels) is reviewed
        if reviewed:
            assert body["dependency_status"] == "active"
            evidence = next(
                label for label in labels if label["origin"] == "observed_exam"
            )["evidence"][0]
            assert evidence["question_id"] == question.id
            with SessionLocal() as db:
                db.get(PastQuestion, question.id).status = "DRAFT"
                db.commit()
            stale = client.get(base, headers=owner).json()["result"]["result"]
            assert stale["dependency_status"] == "stale"
            assert (
                next(
                    label
                    for label in stale["study_report"]["topics"][0]["labels"]
                    if label["origin"] == "observed_exam"
                )["availability"]
                == "unavailable"
            )


def test_label_scope_does_not_promote_unrelated_topics():
    mark_data = dict(
        version_id="v",
        chunk_id="c",
        quote="某一段原文",
        kind="key",
        reason="教师强调",
        confirmed=True,
    )
    topic = dict(
        labels=[dict(kind="key", reason="建议", origin="ai_suggestion")],
        citations=[dict(version_id="v", chunk_id="different", quote="另一段原文")],
    )
    report = {"topics": [topic]}
    m2_supplements.apply_labels(report, {"teacher_marks": [mark_data]})
    assert topic["labels"][0]["origin"] == "ai_suggestion"


@pytest.mark.usefixtures("configured")
def test_note_secret_blocked_and_no_unselected_content_sent(monkeypatch):
    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        note = add_note(client, owner, course, "deterministic-test-key")
        r = preview(
            client, owner, course, pending, note_ids=[note["id"]], notes_confirmed=True
        )
        assert r.status_code == 422
        calls = []
        mock_success(monkeypatch, calls=calls)
        confirm(client, owner, pending)
        assert run_ai_once()
        assert "supplementary_notes" not in json.loads(
            calls[0]["messages"][1]["content"]
        )
        with SessionLocal() as db:
            assert not any(
                "deterministic-test-key" in record.result_json
                for record in db.scalars(select(AIResult))
            )


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize(
    "extra",
    [{"teacher_marks": []}, {"exam_paper_ids": []}, {"exam_sources_confirmed": True}],
)
def test_report_rejects_manual_label_source_inputs(extra):
    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        response = preview(client, owner, course, pending, report=True, **extra)
        assert response.status_code == 422


@pytest.mark.usefixtures("configured")
def test_report_resume_rechecks_selected_notes_without_resetting_job():
    from app.models import RemoteQuery, ProcessingJob

    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        note = add_note(client, owner, course)
        pending = preview(
            client,
            owner,
            course,
            pending,
            report=True,
            note_ids=[note["id"]],
            notes_confirmed=True,
        ).json()
        base = confirm(client, owner, pending)
        with SessionLocal() as db:
            row = db.get(RemoteQuery, pending["id"])
            db.get(ProcessingJob, row.job_id).status = "FAILED"
            db.get(Note, note["id"]).deleted = True
            db.commit()
        response = client.post(
            base + "/resume", headers=owner, json={"confirm_remote_send": True}
        )
        assert response.status_code in (404, 409)
        assert client.get(base, headers=owner).json()["job"]["status"] == "FAILED"


@pytest.mark.usefixtures("configured")
def test_prior_prompt_versions_remain_in_history():
    from app.models import RemoteQuery

    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        with SessionLocal() as db:
            user_id = db.get(RemoteQuery, pending["id"]).user_id
            for version in [
                "zhipu-grounded-qa-v2",
                "zhipu-study-report-v6",
                "zhipu-study-report-v7",
            ]:
                db.add(
                    AIResult(
                        user_id=user_id,
                        course_id=course,
                        query="旧结果",
                        status="grounded",
                        model_mode="real",
                        prompt_version=version,
                        result_json='{"citations":[]}',
                    )
                )
            db.commit()
        qa_rows = client.get(
            f"/api/v1/courses/{course}/ai-results", headers=owner
        ).json()
        reports = client.get(
            f"/api/v1/courses/{course}/study-reports", headers=owner
        ).json()
        assert len(qa_rows) == 1
        assert len(reports) == 2


@pytest.mark.usefixtures("configured")
@pytest.mark.parametrize(
    "identity",
    [
        None,
        {"kind": "practice", "confirmed": True},
        {"kind": "past_exam", "confirmed": False},
    ],
)
def test_generic_or_unconfirmed_banks_never_become_exam_facts(identity):
    from app.models import PastPaper

    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        paper, topic_id = seed_bank(
            client,
            owner,
            course,
            "1. 苹果有多少？\nA. 一 B. 二 C. 三 D. 四\n答案：B\n知识标签：数量",
        )
        source = pending["sources"][0]
        with SessionLocal() as db:
            topic = db.get(Topic, topic_id)
            topic.sources_json = json.dumps(
                {
                    "citations": [
                        dict(
                            version_id=source["version_id"],
                            chunk_id=source["source_id"],
                            quote=source["text"],
                        )
                    ]
                }
            )
            question = db.get(PastQuestion, paper["questions"][0]["id"])
            data = json.loads(question.bank_data_json)
            data["topic_index"] = {"selection_reviewed": True}
            question.bank_data_json = json.dumps(data)
            row = db.get(PastPaper, paper["id"])
            meta = json.loads(row.bank_meta_json)
            if identity is not None:
                meta["exam_identity"] = identity
            row.bank_meta_json = json.dumps(meta)
            db.commit()
        result = preview(client, owner, course, pending, report=True)
        assert result.status_code == 201, result.text
        assert result.json()["sources"][0]["m2_supplement"]["exam_evidence"] == []


@pytest.mark.usefixtures("configured")
def test_new_reading_mark_invalidates_preview_and_reader_is_absent_by_default(
    monkeypatch,
):
    from app.models import RemoteQuery
    from app.services import reading_report_evidence

    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        assert reading_report_evidence._reader is None
        result = preview(client, owner, course, pending, report=True)
        assert result.status_code == 201, result.text
        pending = result.json()
        assert pending["sources"][0]["m2_supplement"]["teacher_marks"] == []
        with SessionLocal() as db:
            user_id = db.get(RemoteQuery, pending["id"]).user_id
        row = dict(
            **mark(pending),
            id=str(uuid4()),
            user_id=user_id,
            course_id=course,
            revision=1,
            status="active",
            mark_type="teacher_emphasis",
        )
        monkeypatch.setattr(reading_report_evidence, "_reader", lambda *args: [row])
        response = client.post(
            f"/api/v1/remote-queries/{pending['id']}/confirm",
            headers=owner,
            json={"confirm_remote_send": True},
        )
        assert response.status_code == 409


@pytest.mark.usefixtures("configured")
def test_legacy_manual_fact_preview_cannot_be_dispatched():
    from app.models import RemoteQuery

    with TestClient(app) as client:
        owner, course, _, pending = qa(client)
        pending = preview(client, owner, course, pending, report=True).json()
        with SessionLocal() as db:
            row = db.get(RemoteQuery, pending["id"])
            sources = json.loads(json.dumps(row.sources))
            sources[0]["m2_supplement"] = {
                "version": 1,
                "notes": [],
                "teacher_marks": [mark(pending)],
                "exam_evidence": [],
                "exam_paper_ids": [],
            }
            row.sources = sources
            db.commit()
        response = client.post(
            f"/api/v1/remote-queries/{pending['id']}/confirm",
            headers=owner,
            json={"confirm_remote_send": True},
        )
        assert response.status_code == 409
        assert (
            client.get(
                f"/api/v1/remote-queries/{pending['id']}", headers=owner
            ).status_code
            == 200
        )
