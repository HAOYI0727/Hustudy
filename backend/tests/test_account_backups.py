from test_question_bank import seed_choice
import hashlib
import io
import json
from uuid import uuid4
import zipfile

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models import User
from app.workers.materials import drain_jobs
from app.workers.account_archives import run_archive_once
from app.services import account_backups as service
from test_materialhub import context, upload
from test_preview_assets import png
from test_preview_assets import import_pdf
from test_manual_transcripts import draft, confirm


def empty_account(client):
    data = client.post(
        "/api/v1/auth/register",
        json={
            "username": "restore_" + uuid4().hex[:10],
            "password": "test-password-only",
        },
    ).json()
    return {"Authorization": "Bearer " + data["access_token"]}, data["user"]["id"]


def exported(client, headers):
    response = client.post("/api/v1/backups", headers=headers)
    assert response.status_code == 202, response.text
    record = response.json()
    assert run_archive_once()
    done = client.get("/api/v1/backups/" + record["id"], headers=headers).json()
    assert done["job"]["status"] == "SUCCEEDED", done
    raw = client.get("/api/v1/backups/" + record["id"] + "/download", headers=headers)
    assert raw.status_code == 200, raw.text
    assert hashlib.sha256(raw.content).hexdigest() == done["sha256"]
    return raw.content, done


def restored(client, headers, body):
    response = client.post(
        "/api/v1/backups/restore",
        headers=headers,
        data={"confirm": "RESTORE_EMPTY_ACCOUNT"},
        files={"file": ("account.zip", body, "application/zip")},
    )
    assert response.status_code == 202, response.text
    assert run_archive_once()
    return client.get(
        "/api/v1/backups/" + response.json()["id"], headers=headers
    ).json()


def test_roundtrip_document_note_citation_image_and_source_hash():
    with TestClient(app) as client:
        headers, course = context(client)
        source_user = client.get("/api/v1/auth/me", headers=headers).json()["id"]
        document_job = upload(
            client, headers, course, "# 来源\n\n窗口机制限制发送速率。"
        )
        drain_jobs()
        chunk = client.get(
            f"/api/v1/versions/{document_job['resource_id']}/chunks", headers=headers
        ).json()[0]
        from docx import Document as WordDocument
        from pptx import Presentation

        word = WordDocument()
        word.add_paragraph("DOCX正文与顺序")
        buffer = io.BytesIO()
        word.save(buffer)
        upload(client, headers, course, buffer.getvalue(), "word.docx")
        slides = Presentation()
        slide = slides.slides.add_slide(slides.slide_layouts[6])
        slide.shapes.add_textbox(0, 0, 1000000, 1000000).text = "PPTX原文"
        buffer = io.BytesIO()
        slides.save(buffer)
        upload(client, headers, course, buffer.getvalue(), "slides.pptx")
        pdf = import_pdf(client, headers, course)
        first_manual = confirm(
            client, headers, draft(client, headers, pdf, text="人工第一版原文。")
        )
        confirm(
            client,
            headers,
            draft(
                client, headers, pdf, text="人工第二版原文。", parent=first_manual["id"]
            ),
        )
        drain_jobs()
        image = client.post(
            f"/api/v1/courses/{course}/assets",
            headers=headers,
            files={"file": ("image.png", png())},
        ).json()
        with SessionLocal() as db:
            db.get(User, source_user).timezone = "America/New_York"
            db.commit()
        note = client.post(
            "/api/v1/notes",
            headers=headers,
            json={
                "course_id": course,
                "title": "来源笔记",
                "content": f"原文与图片 ![[asset:{image['id']}|图]]",
                "citations": [
                    {
                        "version_id": chunk["version_id"],
                        "chunk_id": chunk["id"],
                        "quote": "窗口机制",
                    }
                ],
            },
        ).json()
        linked = []
        for index in range(2):
            assert (
                client.post(
                    f"/api/v1/courses/{course}/assets",
                    headers=headers,
                    files={"file": (f"extra{index}.png", png())},
                ).status_code
                == 201
            )
            linked_note = client.post(
                "/api/v1/notes",
                headers=headers,
                json={
                    "course_id": course,
                    "title": f"双链{index}",
                    "content": f"[[note:{note['id']}|来源笔记]]",
                },
            )
            assert linked_note.status_code == 201
            linked.append(linked_note.json()["id"])
        note = client.patch(
            f"/api/v1/notes/{note['id']}",
            headers=headers,
            json={
                "revision": note["revision"],
                "title": note["title"],
                "content": note["content"] + f"\n[[note:{linked[0]}|双链0]]",
            },
        ).json()
        assert (
            client.post(
                f"/api/v1/courses/{course}/ai-queries",
                headers=headers,
                json={"mode": "demo", "query": "窗口机制"},
            ).status_code
            == 201
        )
        seed_choice(client, headers, course)
        attempts = []
        for index in range(2):
            blueprint = client.post(
                f"/api/v1/exam-blueprints?course_id={course}",
                headers=headers,
                json={
                    "name": f"备份蓝图{index}",
                    "total_points": 5,
                    "duration_minutes": 10,
                    "question_types": [
                        {"type": "single_choice", "count": 1, "points": 5}
                    ],
                    "topics": [{"name": "综合", "count": 1}],
                },
            ).json()
            paper = client.post(
                f"/api/v1/exam-blueprints/{blueprint['id']}/generate", headers=headers
            ).json()
            correct = client.get(f"/api/v1/exam-papers/{paper['id']}?include_answers=true", headers=headers).json()["questions"][0]["answer"]
            wrong = next(c for c in "ABCD" if c != correct)
            assert (
                client.post(
                    f"/api/v1/exam-papers/{paper['id']}/review", headers=headers
                ).status_code
                == 200
            )
            attempt = client.post(
                f"/api/v1/exam-papers/{paper['id']}/attempts", headers=headers
            ).json()
            assert (
                client.put(
                    f"/api/v1/attempts/{attempt['id']}/answers/{paper['questions'][0]['id']}",
                    headers=headers,
                    json={"answer": wrong},
                ).status_code
                == 200
            )
            assert (
                client.post(
                    f"/api/v1/attempts/{attempt['id']}/submit", headers=headers
                ).status_code
                == 200
            )
            attempts.append(attempt["id"])
        original_mistakes = client.get("/api/v1/mistakes", headers=headers).json()
        assert original_mistakes
        body, archive = exported(client, headers)
        assert archive["counts"]["documents"] == 4
        assert archive["counts"]["assets"] == 3 and archive["counts"]["notes"] == 3
        assert (
            archive["counts"]["exam_papers"] == 2
            and archive["counts"]["exam_attempts"] == 2
        )
        target, target_id = empty_account(client)
        # UUID preservation deliberately forbids copying over source IDs in one database.
        conflict = restored(client, target, body)
        assert (
            conflict["job"]["status"] == "FAILED" and "UUID" in conflict["job"]["error"]
        )
        with SessionLocal() as db:
            db.delete(db.get(User, source_user))
            db.commit()
        done = restored(client, target, body)
        assert done["job"]["status"] == "SUCCEEDED", done
        assert done["counts"] == archive["counts"]
        assert client.get("/api/v1/courses", headers=target).json()[0]["id"] == course
        assert (
            client.get(f"/api/v1/notes/{note['id']}", headers=target).json()["content"]
            == note["content"]
        )
        citations = client.get(
            f"/api/v1/notes/{note['id']}/citations", headers=target
        ).json()
        assert (
            citations[0]["chunk_id"] == chunk["id"]
            and citations[0]["availability"] == "active"
        )
        assert (
            client.get(f"/api/v1/assets/{image['id']}", headers=target).content == png()
        )
        hits = client.get(
            f"/api/v1/courses/{course}/search", headers=target, params={"q": "窗口机制"}
        ).json()
        assert hits and hits[0]["version_id"] == chunk["version_id"]
        assert client.get("/api/v1/auth/me", headers=target).json()["id"] == target_id
        assert (
            client.get("/api/v1/auth/me", headers=target).json()["timezone"]
            == "America/New_York"
        )
        assert (
            len(
                client.get(
                    f"/api/v1/notes/{note['id']}/backlinks", headers=target
                ).json()
            )
            == 2
        )
        for attempt_id in attempts:
            assert (
                client.get(
                    f"/api/v1/attempts/{attempt_id}/result", headers=target
                ).status_code
                == 200
            )
        assert client.get("/api/v1/mistakes", headers=target).json() == original_mistakes
        assert (
            client.post(
                "/api/v1/backups/restore",
                headers=target,
                data={"confirm": "RESTORE_EMPTY_ACCOUNT"},
                files={"file": ("a.zip", body)},
            ).status_code
            == 409
        )


def test_backup_owner_active_job_and_deleted_source_guards():
    with TestClient(app) as client:
        headers, course = context(client)
        foreign, _ = empty_account(client)
        job = upload(client, headers, course, "# 来源\n\n不可越权。")
        assert client.post("/api/v1/backups", headers=headers).status_code == 409
        drain_jobs()
        body, row = exported(client, headers)
        for suffix in ("", "/download"):
            assert (
                client.get(
                    "/api/v1/backups/" + row["id"] + suffix, headers=foreign
                ).status_code
                == 404
            )
        assert (
            client.post(
                "/api/v1/backups/restore",
                headers=foreign,
                data={"confirm": "false"},
                files={"file": ("a.zip", body)},
            ).status_code
            == 422
        )
        version = client.get(
            "/api/v1/versions/" + job["resource_id"], headers=headers
        ).json()
        assert (
            client.delete(
                "/api/v1/documents/" + version["document_id"], headers=headers
            ).status_code
            == 204
        )
        assert (
            client.get(
                "/api/v1/backups/" + row["id"] + "/download", headers=headers
            ).status_code
            == 409
        )


def mutate(body, mode):
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        files = {info.filename: archive.read(info) for info in archive.infolist()}
    manifest = json.loads(files["manifest.json"])
    if mode == "schema":
        manifest["schema_revision"] = "future"
    elif mode == "hash":
        manifest["files"][0]["sha256"] = "0" * 64
    elif mode == "foreign":
        manifest["tables"]["documents"][0]["user_id"] = str(uuid4())
    elif mode == "path":
        files["../escape"] = "forbidden".encode()
    elif mode == "extra":
        manifest["tables"]["unknown_table"] = []
    elif mode == "citation":
        citation = manifest["tables"]["citations"][0]
        citation["quote"] = "不在原文里的伪造摘录"
        citation["quote_hash"] = hashlib.sha256(citation["quote"].encode()).hexdigest()
    elif mode == "reference":
        manifest["tables"]["citations"][0]["chunk_id"] = str(uuid4())
    elif mode == "bytes":
        member = manifest["files"][0]["member"]
        content = files[member]
        files[member] = bytes([content[0] ^ 255]) + content[1:]
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False).encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return out.getvalue()


def test_tampered_archive_rolls_back_all_business_rows_and_files():
    with TestClient(app) as client:
        owner, course = context(client)
        source_user = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        job = upload(client, owner, course, "# 备份\n\n校验原文。")
        drain_jobs()
        chunk = client.get(
            f"/api/v1/versions/{job['resource_id']}/chunks", headers=owner
        ).json()[0]
        assert (
            client.post(
                "/api/v1/notes",
                headers=owner,
                json={
                    "course_id": course,
                    "title": "引用完整性",
                    "citations": [
                        {
                            "version_id": chunk["version_id"],
                            "chunk_id": chunk["id"],
                            "quote": "校验原文",
                        }
                    ],
                },
            ).status_code
            == 201
        )
        body, _ = exported(client, owner)
        with SessionLocal() as db:
            db.delete(db.get(User, source_user))
            db.commit()
        target, target_id = empty_account(client)
        for mode in [
            "schema",
            "hash",
            "foreign",
            "path",
            "extra",
            "citation",
            "reference",
            "bytes",
        ]:
            done = restored(client, target, mutate(body, mode))
            assert done["job"]["status"] == "FAILED", (mode, done)
            assert client.get("/api/v1/courses", headers=target).json() == []
            assert not list((service.storage().root / target_id).rglob("restore-*"))
        assert restored(client, target, body)["job"]["status"] == "SUCCEEDED"


def test_restore_commit_fault_rolls_back_import_and_cleans_files(monkeypatch):
    from sqlalchemy.orm import Session

    with TestClient(app) as client:
        owner, course = context(client)
        source_user = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        upload(client, owner, course, "# 回滚\n\n恢复提交失败不保留半份数据。")
        drain_jobs()
        body, _ = exported(client, owner)
        with SessionLocal() as db:
            db.delete(db.get(User, source_user))
            db.commit()
        target, target_id = empty_account(client)
        original_restore, original_commit = service.restore_package, Session.commit

        def tagged(db, *args):
            result = original_restore(db, *args)
            db.info["fail_restore_commit"] = True
            return result

        def failing_commit(db):
            if db.info.pop("fail_restore_commit", False):
                raise RuntimeError("injected commit fault")
            return original_commit(db)

        with monkeypatch.context() as patch:
            patch.setattr(service, "restore_package", tagged)
            patch.setattr(Session, "commit", failing_commit)
            done = restored(client, target, body)
        assert done["job"]["status"] == "FAILED"
        assert client.get("/api/v1/courses", headers=target).json() == []
        assert not list((service.storage().root / target_id).rglob("restore-*"))
        assert restored(client, target, body)["job"]["status"] == "SUCCEEDED"


def test_expired_restore_is_not_replayed_and_only_terminal_records_can_remove():
    from datetime import timedelta
    from app.models import ProcessingJob
    from app.models.base import utc_now
    from app.workers.account_archives import claim

    with TestClient(app) as client:
        headers, user_id = empty_account(client)
        queued = client.post(
            "/api/v1/backups/restore",
            headers=headers,
            data={"confirm": "RESTORE_EMPTY_ACCOUNT"},
            files={"file": ("invalid.zip", b"not a zip")},
        ).json()
        assert (
            client.delete(
                "/api/v1/backups/" + queued["id"], headers=headers
            ).status_code
            == 409
        )
        with SessionLocal() as db:
            running = claim(db)
            assert running.id == queued["job"]["id"]
            running.lease_until = utc_now() - timedelta(seconds=1)
            db.commit()
        assert not run_archive_once()
        failed = client.get("/api/v1/backups/" + queued["id"], headers=headers).json()
        assert failed["job"]["status"] == "FAILED"
        assert not service.archive_path(user_id, queued["id"], ".input.zip").exists()
        stranger, _ = empty_account(client)
        assert (
            client.delete(
                "/api/v1/backups/" + queued["id"], headers=stranger
            ).status_code
            == 404
        )
        assert (
            client.delete(
                "/api/v1/backups/" + queued["id"], headers=headers
            ).status_code
            == 204
        )
        assert (
            client.get("/api/v1/backups/" + queued["id"], headers=headers).status_code
            == 404
        )
        with SessionLocal() as db:
            assert db.get(ProcessingJob, queued["job"]["id"]) is None
