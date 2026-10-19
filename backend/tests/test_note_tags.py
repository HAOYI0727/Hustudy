"""M3 tags: persistence, CAS, filtering, isolation and archive compatibility."""

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models import User
from test_material_organization import setup_course
from test_account_backups import empty_account, exported, restored


def create(client, owner, course, **values):
    result = client.post(
        "/api/v1/notes",
        headers=owner,
        json={
            "title": "调度笔记",
            "content": "正文保持原样",
            "course_id": course,
            **values,
        },
    )
    assert result.status_code == 201, result.text
    return result.json()


def test_tag_persistence_partial_update_and_atomic_conflict():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        note = create(client, owner, course, tags=[" 期末 ", "期末", "重点"])
        assert note["tags"] == ["期末", "重点"]
        path = "/api/v1/notes/" + note["id"]
        assert client.get(path, headers=owner).json()["tags"] == note["tags"]
        updated = client.patch(
            path, headers=owner, json={"revision": 1, "content": "新正文"}
        ).json()
        assert updated["tags"] == note["tags"] and updated["revision"] == 2
        conflict = client.patch(
            path,
            headers=owner,
            json={"revision": 1, "tags": ["旧窗口"], "content": "覆盖"},
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["details"]["server_tags"] == note["tags"]
        assert client.get(path, headers=owner).json() == updated
        cleared = client.patch(
            path, headers=owner, json={"revision": 2, "tags": []}
        ).json()
        assert cleared["tags"] == [] and cleared["content"] == "新正文"
        # M2's existing createNote callers omit tags and retain their old semantics.
        assert create(client, owner, course)["tags"] == []


@pytest.mark.parametrize(
    "tags",
    [None, "期末", [" "], ["长" * 33], list(map(str, range(13))), [3], ["a\x00b"]],
)
def test_invalid_tags_do_not_change_saved_content(tags):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        note = create(client, owner, course, tags=["保留"])
        response = client.post(
            "/api/v1/notes", headers=owner, json={"title": "非法", "tags": tags}
        )
        assert response.status_code == 422
        path = "/api/v1/notes/" + note["id"]
        response = client.patch(
            path,
            headers=owner,
            json={"revision": 1, "tags": tags, "content": "不应保存"},
        )
        assert response.status_code == 422
        assert client.get(path, headers=owner).json() == note


def test_tag_search_exact_matching_permissions_and_retirement():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        foreign, other_course = setup_course(client)
        target = create(
            client, owner, course, tags=["期末", "100%", "a_b", 'a"b', "😀" * 32]
        )
        distractor = create(client, owner, course, tags=["期末复习", "1000", "axb"])
        create(client, foreign, other_course, tags=["期末"])

        def ids(**params):
            response = client.get(
                "/api/v1/notes", headers=owner, params={"course_id": course, **params}
            )
            assert response.status_code == 200
            return {row["id"] for row in response.json()}

        assert ids(tag="期末") == {target["id"]}
        assert ids(q="期末") == {target["id"], distractor["id"]}
        assert ids(q="调度", tag="期末") == {target["id"]}
        assert ids(q="不存在", tag="期末") == set()
        for literal in ("%", "_", 'a"b'):
            assert ids(q=literal) == {target["id"]}
        page = client.get(
            f"/api/v1/courses/{course}/note-search",
            headers=owner,
            params={"q": "期末", "limit": 1},
        ).json()
        assert page["total"] == 2 and len(page["items"]) == 1
        assert page["items"][0]["excerpt"]["highlights"] == []
        assert (
            client.get(
                "/api/v1/notes",
                headers=foreign,
                params={"course_id": course, "tag": "期末"},
            ).status_code
            == 404
        )
        assert (
            client.patch(
                "/api/v1/notes/" + target["id"],
                headers=foreign,
                json={"revision": 1, "tags": []},
            ).status_code
            == 404
        )
        assert (
            client.delete("/api/v1/notes/" + target["id"], headers=owner).status_code
            == 204
        )
        assert ids(tag="期末") == set()
        # Course list is the public read interface; course deletion withdraws all notes.
        rows = client.get("/api/v1/courses", headers=owner).json()
        current = next(row for row in rows if row["id"] == course)
        response = client.delete(
            f"/api/v1/courses/{course}",
            headers=owner,
            params={"revision": current["revision"]},
        )
        assert response.status_code == 204, response.text
        assert (
            client.get(
                f"/api/v1/courses/{course}/note-search",
                headers=owner,
                params={"q": "期末"},
            ).status_code
            == 404
        )
        assert (
            client.get("/api/v1/notes/" + distractor["id"], headers=owner).status_code
            == 404
        )


def rewrite_manifest(body, edit):
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(files["manifest.json"])
    edit(manifest)
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False).encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return out.getvalue()


@pytest.mark.parametrize("legacy", [False, True, "0013", "0014", "0015"])
def test_account_archive_preserves_tags_and_upgrades_0012(legacy):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        note = create(client, owner, course, tags=["复习", "定义"])
        source_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        body, _ = exported(client, owner)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
        assert manifest["schema_revision"] == "0016_note_trash"
        assert manifest["tables"]["notes"][0]["tags"] == note["tags"]
        if legacy is True:

            def make_legacy(manifest):
                manifest["schema_revision"] = "0012_account_archives"
                for row in manifest["tables"]["notes"]:
                    del row["tags"]

            body = rewrite_manifest(body, make_legacy)
        elif legacy in {"0013", "0014"}:
            body = rewrite_manifest(
                body,
                lambda manifest: manifest.update(
                    schema_revision="0013_note_tags"
                    if legacy == "0013"
                    else "0014_note_exports"
                ),
            )
        elif legacy == "0015":
            body = rewrite_manifest(
                body,
                lambda manifest: manifest.update(schema_revision="0015_note_folders"),
            )
        if legacy:

            def remove_trash(manifest):
                del manifest["tables"]["note_trash_policies"]
                for row in manifest["tables"]["notes"]:
                    del row["deleted_at"]
                    del row["purge_after"]

            body = rewrite_manifest(body, remove_trash)
        if legacy and legacy != "0015":

            def remove_folders(manifest):
                del manifest["tables"]["note_folders"]
                for row in manifest["tables"]["notes"]:
                    del row["folder_id"]

            body = rewrite_manifest(body, remove_folders)
        with SessionLocal() as db:
            db.delete(db.get(User, source_id))
            db.commit()
        recipient, _ = empty_account(client)
        done = restored(client, recipient, body)
        assert done["job"]["status"] == "SUCCEEDED", done
        recovered = client.get("/api/v1/notes/" + note["id"], headers=recipient).json()
        assert recovered["tags"] == ([] if legacy is True else note["tags"])
        assert recovered["content"] == note["content"] and recovered["revision"] == 1


@pytest.mark.parametrize("mode", ["missing", "invalid", "unnormalized"])
def test_new_archive_rejects_invalid_tags_without_partial_restore(mode):
    with TestClient(app) as client:
        owner, course = setup_course(client)
        create(client, owner, course, tags=["复习"])
        source_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        body, _ = exported(client, owner)

        def corrupt(manifest):
            row = manifest["tables"]["notes"][0]
            if mode == "missing":
                del row["tags"]
            else:
                row["tags"] = ["x" * 33] if mode == "invalid" else [" 重复 ", "重复"]

        body = rewrite_manifest(body, corrupt)
        with SessionLocal() as db:
            db.delete(db.get(User, source_id))
            db.commit()
        recipient, _ = empty_account(client)
        done = restored(client, recipient, body)
        assert done["job"]["status"] == "FAILED"
        assert client.get("/api/v1/notes", headers=recipient).json() == []
        assert client.get("/api/v1/courses", headers=recipient).json() == []
