import io
import json
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import DocumentVersion, PastPaper, PastQuestion, User, ProcessingJob
from app.workers.materials import drain_jobs
from tests.m1.test_materialhub import context, upload
from tests.m4.test_question_bank import seed_choice, draw, start


def bank_upload(client, h, c, text="1. 解释独立题库术语。", name="questions.md"):
    r = client.post(
        f"/api/v1/courses/{c}/question-bank/files",
        data={"mode": "ai"},
        headers=h,
        files={"file": (name, text.encode(), "text/markdown")},
    )
    assert r.status_code == 202, r.text
    drain_jobs()
    return r.json()["resource_id"]


def import_text(client, h, c):
    r = client.post(
        f"/api/v1/courses/{c}/question-bank/import",
        headers=h,
        json={
            "title": "可删题库",
            "content": "1. 说明第一题。\n知识标签：复习\n2. 说明第二题。\n知识标签：复习",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def delete_paper(client, h, c, pid):
    p = next(
        p
        for p in client.get(
            f"/api/v1/courses/{c}/question-bank/papers", headers=h
        ).json()
        if p["id"] == pid
    )
    return client.post(
        f"/api/v1/past-papers/{pid}/delete",
        headers=h,
        json={
            "revision": p["metadata"].get("revision", 1),
            "question_snapshot": p["question_snapshot"],
        },
    )


def restore(client, h, c, action):
    body = {
        key: action[key]
        for key in ["revisions", "paper_id", "paper_revision"]
        if key in action
    }
    return client.post(
        f"/api/v1/courses/{c}/question-bank/restore", headers=h, json=body
    )


def test_bank_files_are_separate_from_material_list_search_and_storage():
    with TestClient(app) as client:
        h, c = context(client)
        version = bank_upload(client, h, c)
        files = client.get(f"/api/v1/courses/{c}/question-bank/files", headers=h).json()
        assert len(files) == 1 and files[0]["library_scope"] == "question_bank"
        assert client.get(f"/api/v1/courses/{c}/documents", headers=h).json() == []
        assert (
            client.get(f"/api/v1/courses/{c}/documents/page", headers=h).json()["total"]
            == 0
        )
        assert (
            client.get(f"/api/v1/courses/{c}/search?q=独立题库术语", headers=h).json()
            == []
        )
        assert (
            client.get(f"/api/v1/documents/{files[0]['id']}", headers=h).status_code
            == 200
        )
        assert client.get(f"/api/v1/versions/{version}/original", headers=h).is_success
        with SessionLocal() as db:
            v = db.get(DocumentVersion, version)
            assert Path(v.source_path).parent.name == "question_bank"
        material = upload(client, h, c, "1. 解释独立题库术语。", name="lesson.md")[
            "resource_id"
        ]
        assert material != version
        drain_jobs()
        assert len(client.get(f"/api/v1/courses/{c}/documents", headers=h).json()) == 1


def test_zip_files_and_material_export_are_isolated():
    from app.workers.material_exports import run_export_once

    with TestClient(app) as client:
        h, c = context(client)
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w") as z:
            z.writestr("exams/q.md", "1. 解释题目。")
        r = client.post(
            f"/api/v1/courses/{c}/question-bank/archives",
            data={"mode": "ai"},
            headers=h,
            files={"file": ("q.zip", raw.getvalue(), "application/zip")},
        )
        assert r.status_code == 201
        upload(client, h, c, "# 普通课件\n独立课堂内容", name="lesson.md")
        drain_jobs()
        package = client.post(
            f"/api/v1/courses/{c}/material-exports",
            headers=h,
            json={"request_id": str(uuid4())},
        ).json()
        assert run_export_once()
        payload = client.get(
            f"/api/v1/material-exports/{package['id']}/download", headers=h
        )
        assert payload.status_code == 200, payload.text
        with zipfile.ZipFile(io.BytesIO(payload.content)) as z:
            m = json.loads(z.read("manifest.json"))
        assert len(m["documents"]) == 1 and m["documents"][0]["name"] == "lesson"


def test_legacy_source_move_is_explicit_and_keeps_version_identity():
    with TestClient(app) as client:
        h, c = context(client)
        v = upload(client, h, c, "1. 简述旧题目。", name="old.md")["resource_id"]
        drain_jobs()
        p = client.post(
            f"/api/v1/courses/{c}/question-bank/import",
            headers=h,
            json={"title": "旧来源", "version_id": v},
        ).json()
        files = client.get(f"/api/v1/courses/{c}/question-bank/files", headers=h).json()
        assert files[0]["library_scope"] == "material"
        assert (
            client.post(
                f"/api/v1/courses/{c}/question-bank/files/{files[0]['id']}/move",
                headers=h,
            ).status_code
            == 200
        )
        assert client.get(f"/api/v1/courses/{c}/documents", headers=h).json() == []
        q = client.get(
            f"/api/v1/courses/{c}/question-bank?paper_id={p['id']}", headers=h
        ).json()["items"][0]
        assert q["bank_data"]["citations"][0]["version_id"] == v


def test_single_and_batch_delete_undo_atomic_and_stale_revision():
    with TestClient(app) as client:
        h, c = context(client)
        p = import_text(client, h, c)
        q1, q2 = p["questions"]
        result = client.delete(
            f"/api/v1/past-questions/{q1['id']}?revision={q1['revision']}", headers=h
        )
        assert result.status_code == 200
        assert (
            client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()["total"]
            == 1
        )
        assert restore(client, h, c, result.json()).status_code == 200
        assert restore(client, h, c, result.json()).status_code == 409
        rows = client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()[
            "items"
        ]
        revisions = {q["id"]: q["revision"] for q in rows}
        wrong = revisions | {q2["id"]: 999}
        r = client.post(
            f"/api/v1/courses/{c}/question-bank/batch",
            headers=h,
            json={"question_ids": list(wrong), "revisions": wrong, "action": "delete"},
        )
        assert r.status_code == 409
        assert (
            client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()["total"]
            == 2
        )
        r = client.post(
            f"/api/v1/courses/{c}/question-bank/batch",
            headers=h,
            json={
                "question_ids": list(revisions),
                "revisions": revisions,
                "action": "delete",
            },
        )
        assert (
            r.status_code == 200 and restore(client, h, c, r.json()).status_code == 200
        )


def test_whole_bank_delete_checks_snapshot_and_can_undo_without_touching_original():
    with TestClient(app) as client:
        h, c = context(client)
        version = bank_upload(client, h, c)
        p = client.post(
            f"/api/v1/courses/{c}/question-bank/import",
            headers=h,
            json={"title": "有原件", "version_id": version},
        ).json()
        r = delete_paper(client, h, c, p["id"])
        assert r.status_code == 200, r.text
        assert (
            client.get(f"/api/v1/courses/{c}/question-bank/papers", headers=h).json()
            == []
        )
        from app.services.exam_analysis import inputs

        owner = client.get("/api/v1/auth/me", headers=h).json()["id"]
        with SessionLocal() as db:
            assert inputs(db, owner, c)[0] == []
        assert client.get(f"/api/v1/versions/{version}/original", headers=h).is_success
        assert restore(client, h, c, r.json()).status_code == 200
        assert (
            len(
                client.get(
                    f"/api/v1/courses/{c}/question-bank/papers", headers=h
                ).json()
            )
            == 1
        )


def test_split_parent_cannot_be_restored_and_cross_account_delete_is_hidden():
    with TestClient(app) as client:
        h, c = context(client)
        p = import_text(client, h, c)
        q = p["questions"][0]
        r = client.post(
            f"/api/v1/past-questions/{q['id']}/split",
            headers=h,
            json={"revision": q["revision"], "parts": ["第一小题。", "第二小题。"]},
        )
        assert r.status_code == 200, r.text
        assert (
            restore(
                client, h, c, {"revisions": {q["id"]: q["revision"] + 1}}
            ).status_code
            == 409
        )
        h2, c2 = context(client)
        assert delete_paper(client, h, c, p["id"]).status_code == 200
        assert (
            client.post(
                f"/api/v1/past-papers/{p['id']}/delete",
                headers=h2,
                json={"revision": 1, "question_snapshot": "0" * 64},
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/v1/courses/{c}/question-bank/files", headers=h2
            ).status_code
            == 404
        )


def test_old_attempt_snapshot_unchanged_by_question_deletion():
    with TestClient(app) as client:
        h, c = context(client)
        p, tid = seed_choice(client, h, c)
        exam = draw(client, h, c, tid, count=1)
        attempt = start(client, h, exam)
        # In-progress attempts prohibit answer-bearing management.
        assert delete_paper(client, h, c, p["id"]).status_code == 409
        assert (
            client.post(
                f"/api/v1/attempts/{attempt['id']}/submit", headers=h
            ).status_code
            == 200
        )
        before = client.get(f"/api/v1/attempts/{attempt['id']}", headers=h).json()
        assert delete_paper(client, h, c, p["id"]).status_code == 200
        assert (
            client.get(f"/api/v1/attempts/{attempt['id']}", headers=h).json() == before
        )


def test_empty_pending_bank_delete_cancels_job_and_restores_empty_bank():
    with TestClient(app) as client:
        h, c = context(client)
        with SessionLocal() as db:
            owner = client.get("/api/v1/auth/me", headers=h).json()["id"]
            p = PastPaper(
                user_id=owner,
                course_id=c,
                title="待识别",
                content="",
                content_hash="test-pending",
            )
            db.add(p)
            db.flush()
            job = ProcessingJob(user_id=owner, type="BANK_OCR", resource_id=p.id)
            db.add(job)
            db.flush()
            p.bank_meta_json = json.dumps(
                {
                    "image_job_id": job.id,
                    "image_import": {"asset_ids": [], "layout": "single"},
                }
            )
            db.commit()
            pid, jid = p.id, job.id
        r = delete_paper(client, h, c, pid)
        assert r.status_code == 200 and r.json()["changed"] == 0
        assert (
            client.get(
                f"/api/v1/courses/{c}/question-bank/image-jobs", headers=h
            ).json()
            == []
        )
        with SessionLocal() as db:
            assert db.get(ProcessingJob, jid).status == "CANCELLED"
        assert restore(client, h, c, r.json()).status_code == 200


def test_full_backup_preserves_two_libraries_and_old_0020_defaults():
    from tests.shared.test_account_backups import exported, restored, empty_account
    from tests.m3.test_note_tags import rewrite_manifest

    with TestClient(app) as client:
        h, c = context(client)
        bank_upload(client, h, c)
        upload(client, h, c, "普通资料", name="lesson.md")
        drain_jobs()
        body, _ = exported(client, h)
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            manifest = json.loads(z.read("manifest.json"))
        assert manifest["schema_revision"] == "0021_bank_library"
        source = client.get("/api/v1/auth/me", headers=h).json()["id"]
        with SessionLocal() as db:
            db.delete(db.get(User, source))
            db.commit()
        target, _ = empty_account(client)
        assert restored(client, target, body)["job"]["status"] == "SUCCEEDED"
        assert (
            len(client.get(f"/api/v1/courses/{c}/documents", headers=target).json())
            == 1
        )
        assert (
            len(
                client.get(
                    f"/api/v1/courses/{c}/question-bank/files", headers=target
                ).json()
            )
            == 1
        )

        # A genuine pre-0021 row lacks the scope field.
        def legacy(m):
            m["schema_revision"] = "0020_exam_analysis"
            for row in m["tables"]["documents"]:
                row.pop("library_scope")

        old = rewrite_manifest(body, legacy)
        owner2 = client.get("/api/v1/auth/me", headers=target).json()["id"]
        with SessionLocal() as db:
            db.delete(db.get(User, owner2))
            db.commit()
        fresh, _ = empty_account(client)
        assert restored(client, fresh, old)["job"]["status"] == "SUCCEEDED"
        assert (
            len(client.get(f"/api/v1/courses/{c}/documents", headers=fresh).json()) == 2
        )


def test_whole_delete_rejects_changed_question_snapshot():
    with TestClient(app) as client:
        h, c = context(client)
        p = import_text(client, h, c)
        meta = client.get(
            f"/api/v1/courses/{c}/question-bank/papers", headers=h
        ).json()[0]
        with SessionLocal() as db:
            db.get(PastQuestion, p["questions"][0]["id"]).revision += 1
            db.commit()
        result = client.post(
            f"/api/v1/past-papers/{p['id']}/delete",
            headers=h,
            json={"revision": 1, "question_snapshot": meta["question_snapshot"]},
        )
        assert result.status_code == 409
        assert (
            client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()["total"]
            == 2
        )
