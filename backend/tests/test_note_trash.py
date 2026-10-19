"""Destructive lifecycle tests run only against conftest's disposable database."""

from datetime import datetime, timedelta
import pytest
from sqlalchemy import select, func
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import Note, NoteLink, Citation, AssetReference, Asset, User
from app.models.base import utc_now
from app.services.note_trash import cleanup_due
from test_materialhub import context
from test_note_tags import create as note, rewrite_manifest
from test_note_organization import folder
from test_note_exports import image, create, done
from test_note_citations import source
from test_account_backups import exported, restored, empty_account

BASE = "/api/v1/notes/trash"


def test_worker_maintenance_runs_on_start_and_is_throttled(monkeypatch):
    from app.workers import note_trash as worker

    clock = [1000.0]
    monkeypatch.setattr(worker.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(worker, "_next_run", 0)
    with TestClient(app) as client:
        owner, course = context(client)
        first, second = [note(client, owner, course) for _ in range(2)]

        def expire(row):
            batch(client, owner, "trash", [row])
            with SessionLocal() as db:
                current = db.get(Note, row["id"])
                current.deleted_at = utc_now() - timedelta(days=31)
                current.purge_after = current.deleted_at + timedelta(days=30)
                db.commit()

        expire(first)
        worker.run_trash_cleanup(force=True)
        assert entries(client, owner)["total"] == 0
        expire(second)
        worker.run_trash_cleanup()
        assert entries(client, owner)["total"] == 1
        clock[0] += 61
        worker.run_trash_cleanup()
        assert entries(client, owner)["total"] == 0


def entries(client, owner):
    result = client.get(BASE, headers=owner)
    assert result.status_code == 200, result.text
    return result.json()


def batch(client, owner, action, rows, **extra):
    return client.post(
        BASE + "/batch",
        headers=owner,
        json={
            "action": action,
            "notes": [{"id": row["id"], "revision": row["revision"]} for row in rows],
            **extra,
        },
    )


def test_restore_preserves_references_and_export_availability():
    with TestClient(app) as client:
        owner, course = context(client)
        f = folder(client, owner, course)
        asset = image(client, owner, course)
        version, citation = source(client, owner, course)
        target = note(
            client,
            owner,
            course,
            title="目标",
            folder_id=f["id"],
            tags=["重点"],
            content=f"![[asset:{asset['id']}|图片]]",
            citations=[citation],
        )
        link = note(client, owner, course, content=f"[[note:{target['id']}|目标]]")
        package = done(client, owner, create(client, owner, note_ids=[target["id"]]))
        assert batch(client, owner, "trash", [target]).status_code == 200
        row = entries(client, owner)["items"][0]
        assert datetime.fromisoformat(row["purge_after"]) - datetime.fromisoformat(
            row["deleted_at"]
        ) == timedelta(days=30)
        for suffix in ("", "/export", "/citations", "/backlinks"):
            assert (
                client.get(
                    f"/api/v1/notes/{target['id']}" + suffix, headers=owner
                ).status_code
                == 404
            )
        assert (
            client.get(
                f"/api/v1/courses/{course}/note-search?q=目标", headers=owner
            ).json()["total"]
            == 1
        )  # Source link text only.
        assert (
            client.get(
                f"/api/v1/note-exports/{package['id']}/download", headers=owner
            ).status_code
            == 404
        )
        assert (
            client.patch(
                f"/api/v1/notes/{link['id']}",
                headers=owner,
                json={"revision": 1, "title": "仍引用回收站"},
            ).status_code
            == 200
        )
        assert batch(client, owner, "restore", [row]).status_code == 200
        recovered = client.get(f"/api/v1/notes/{target['id']}", headers=owner).json()
        for key in ("id", "title", "content", "tags", "folder_id"):
            assert recovered[key] == target[key]
        assert recovered["revision"] == 3
        assert (
            client.get(f"/api/v1/notes/{target['id']}/backlinks", headers=owner).json()[
                0
            ]["id"]
            == link["id"]
        )
        assert (
            client.get(f"/api/v1/notes/{target['id']}/citations", headers=owner).json()[
                0
            ]["version_id"]
            == version["id"]
        )
        assert (
            client.get(
                f"/api/v1/note-exports/{package['id']}/download", headers=owner
            ).status_code
            == 200
        )
        assert batch(client, owner, "trash", [recovered]).status_code == 200
        assert (
            batch(client, owner, "purge", entries(client, owner)["items"]).status_code
            == 200
        )
        with SessionLocal() as db:
            assert db.get(Note, target["id"]) is None
            for model, field in (
                (Citation, Citation.note_id),
                (AssetReference, AssetReference.note_id),
                (NoteLink, NoteLink.target_note_id),
            ):
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(model)
                        .where(field == target["id"])
                    )
                    == 0
                )
            assert db.get(Asset, asset["id"]).deleted is False
        assert (
            client.get(
                f"/api/v1/versions/{version['id']}/original", headers=owner
            ).status_code
            == 200
        )


def test_bulk_is_atomic_for_conflicts_ownership_duplicates_and_wrong_state():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, foreign_course = context(client)
        a, b = [note(client, owner, course) for _ in range(2)]
        foreign = note(client, stranger, foreign_course)
        assert batch(client, owner, "trash", [a, foreign]).status_code == 404
        assert batch(client, owner, "trash", [a, a]).status_code == 422
        assert batch(client, owner, "purge", [a]).status_code == 409
        assert (
            client.patch(
                f"/api/v1/notes/{b['id']}",
                headers=owner,
                json={"revision": 1, "title": "新版本"},
            ).status_code
            == 200
        )
        assert batch(client, owner, "trash", [a, b]).status_code == 409
        assert entries(client, owner)["total"] == 0
        assert client.get(f"/api/v1/notes/{a['id']}", headers=owner).status_code == 200
        b["revision"] = 2
        assert batch(client, owner, "trash", [a, b]).json() == {"affected": 2}
        rows = entries(client, owner)["items"]
        assert batch(client, stranger, "restore", rows).status_code == 404
        assert (
            batch(
                client, owner, "restore", [dict(rows[0], revision=99), rows[1]]
            ).status_code
            == 409
        )
        assert entries(client, owner)["total"] == 2
        assert batch(client, owner, "restore", rows).json() == {"affected": 2}


def test_empty_snapshot_excludes_new_deletions_and_other_accounts():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, foreign_course = context(client)
        a, b, active = [note(client, owner, course) for _ in range(3)]
        foreign = note(client, stranger, foreign_course)
        batch(client, stranger, "trash", [foreign])
        batch(client, owner, "trash", [a])
        snapshot = entries(client, owner)["snapshot"]
        batch(client, owner, "trash", [b])
        assert (
            client.post(
                BASE + "/empty", headers=owner, json={"snapshot": snapshot}
            ).status_code
            == 409
        )
        page = client.get(BASE + "?limit=1", headers=owner).json()
        assert page["total"] == 2 and len(page["items"]) == 1
        assert client.post(
            BASE + "/empty", headers=owner, json={"snapshot": page["snapshot"]}
        ).json() == {"affected": 2}
        assert entries(client, stranger)["total"] == 1
        assert (
            client.get(f"/api/v1/notes/{active['id']}", headers=owner).status_code
            == 200
        )


def test_policy_deadlines_disable_reenable_worker_boundaries_and_restore():
    with TestClient(app) as client:
        owner, course = context(client)
        a, b, c = [note(client, owner, course) for _ in range(3)]
        assert client.get(BASE + "/policy", headers=owner).json() == {
            "retention_days": 30,
            "revision": 0,
        }
        batch(client, owner, "trash", [a, b, c])
        start = datetime.fromisoformat(entries(client, owner)["items"][0]["deleted_at"])
        for bad in [0, 366, 1.5, True]:
            assert (
                client.put(
                    BASE + "/policy",
                    headers=owner,
                    json={"retention_days": bad, "revision": 0},
                ).status_code
                == 422
            )
        assert (
            client.put(
                BASE + "/policy",
                headers=owner,
                json={"retention_days": None, "revision": 0},
            ).status_code
            == 200
        )
        assert all(n["purge_after"] is None for n in entries(client, owner)["items"])
        with SessionLocal() as db:
            cleanup_due(db, start + timedelta(days=366))
            assert all(db.get(Note, n["id"]) is not None for n in (a, b, c))
        assert (
            client.put(
                BASE + "/policy",
                headers=owner,
                json={"retention_days": 7, "revision": 0},
            ).status_code
            == 409
        )
        assert (
            client.put(
                BASE + "/policy",
                headers=owner,
                json={"retention_days": 7, "revision": 1},
            ).status_code
            == 200
        )
        rows = entries(client, owner)["items"]
        assert batch(client, owner, "restore", rows[:1]).status_code == 200
        with SessionLocal() as db:
            # Restrict this helper's global due query by choosing the exact future boundary;
            # other tests only have future 30-day or newer entries at this point.
            assert (
                cleanup_due(db, start + timedelta(days=7) - timedelta(microseconds=1))
                == 0
            )
            assert cleanup_due(db, start + timedelta(days=7), limit=1) == 1
            assert cleanup_due(db, start + timedelta(days=7), limit=1) == 1
            assert cleanup_due(db, start + timedelta(days=7)) == 0
        assert (
            client.get(f"/api/v1/notes/{rows[0]['id']}", headers=owner).status_code
            == 200
        )


def test_restore_when_folder_or_course_removed_requires_explicit_fallback():
    with TestClient(app) as client:
        owner, course = context(client)
        f = folder(client, owner, course)
        a = note(client, owner, course, folder_id=f["id"])
        assert (
            client.delete(
                f"/api/v1/notes/{a['id']}?revision=1", headers=owner
            ).status_code
            == 204
        )
        assert (
            client.delete(
                f"/api/v1/note-folders/{f['id']}?revision=1", headers=owner
            ).status_code
            == 204
        )
        rows = entries(client, owner)["items"]
        assert batch(client, owner, "restore", rows).status_code == 200
        assert (
            client.get(f"/api/v1/notes/{a['id']}", headers=owner).json()["folder_id"]
            is None
        )
        assert (
            client.delete(
                f"/api/v1/courses/{course}?revision=1", headers=owner
            ).status_code
            == 204
        )
        rows = entries(client, owner)["items"]
        assert rows[0]["restore_requires_course"] and rows[0]["deleted_at"]
        assert batch(client, owner, "restore", rows).status_code == 422
        target = client.post(
            "/api/v1/courses", headers=owner, json={"name": "恢复目标"}
        ).json()["id"]
        assert (
            batch(client, owner, "restore", rows, fallback_course_id=target).status_code
            == 200
        )
        assert (
            client.get(f"/api/v1/notes/{a['id']}", headers=owner).json()["course_id"]
            == target
        )


@pytest.mark.parametrize("mode", ["current", "legacy", "invalid"])
def test_trash_backup_roundtrip_legacy_and_invalid_deadline(mode):
    with TestClient(app) as client:
        owner, course = context(client)
        a = note(client, owner, course)
        batch(client, owner, "trash", [a])
        client.put(
            BASE + "/policy",
            headers=owner,
            json={"retention_days": None, "revision": 0},
        )
        source_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        body, _ = exported(client, owner)

        def edit(manifest):
            if mode == "legacy":
                manifest["schema_revision"] = "0015_note_folders"
                del manifest["tables"]["note_trash_policies"]
                for row in manifest["tables"]["notes"]:
                    del row["deleted_at"], row["purge_after"]
            else:
                manifest["tables"]["notes"][0]["deleted_at"] = None

        if mode != "current":
            body = rewrite_manifest(body, edit)
        with SessionLocal() as db:
            db.delete(db.get(User, source_id))
            db.commit()
        recipient, _ = empty_account(client)
        result = restored(client, recipient, body)
        assert result["job"]["status"] == (
            "FAILED" if mode == "invalid" else "SUCCEEDED"
        ), result
        if mode == "invalid":
            assert entries(client, recipient)["total"] == 0
        else:
            rows = entries(client, recipient)["items"]
            assert rows[0]["id"] == a["id"]
            assert (rows[0]["purge_after"] is None) == (mode == "current")
            assert batch(client, recipient, "restore", rows).status_code == 200


@pytest.mark.parametrize("change", ["restore", "disable"])
def test_worker_rechecks_restore_and_policy_after_candidate_read(monkeypatch, change):
    from app.services import note_trash as service

    with TestClient(app) as client:
        owner, course = context(client)
        a = note(client, owner, course)
        batch(client, owner, "trash", [a])
        original_lock = service.lock_owner

        def restore_before_lock(db, user_id):
            rows = entries(client, owner)["items"]
            if change == "restore":
                assert batch(client, owner, "restore", rows).status_code == 200
            else:
                assert (
                    client.put(
                        BASE + "/policy",
                        headers=owner,
                        json={"retention_days": None, "revision": 0},
                    ).status_code
                    == 200
                )
            original_lock(db, user_id)

        monkeypatch.setattr(service, "lock_owner", restore_before_lock)
        # Avoid selecting unrelated test data by clearing only this owner's deadline into the past.
        with SessionLocal() as db:
            row = db.get(Note, a["id"])
            row.purge_after = utc_now() - timedelta(seconds=1)
            db.commit()
            assert cleanup_due(db, utc_now()) == 0
        if change == "restore":
            assert (
                client.get(f"/api/v1/notes/{a['id']}", headers=owner).status_code == 200
            )
        else:
            assert entries(client, owner)["total"] == 1
