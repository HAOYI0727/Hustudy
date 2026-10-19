import posixpath
import re
from urllib.parse import unquote
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import User
from test_materialhub import context
from test_note_tags import create as note, rewrite_manifest
from test_note_exports import create, done, downloaded, image
from test_account_backups import exported, restored, empty_account


def folder(client, owner, course, name="复习", parent=None):
    result = client.post(
        "/api/v1/note-folders",
        headers=owner,
        json={"course_id": course, "name": name, "parent_id": parent},
    )
    assert result.status_code == 201, result.text
    return result.json()


def test_folder_tree_scope_cycles_depth_and_cas():
    with TestClient(app) as client:
        owner, course = context(client)
        other, other_course = context(client)
        top = folder(client, owner, course)
        child = folder(client, owner, course, "第一章", top["id"])
        path = "/api/v1/note-folders/" + top["id"]
        assert (
            client.patch(
                path, headers=other, json={"revision": 1, "name": "他人"}
            ).status_code
            == 404
        )
        assert (
            client.patch(
                path, headers=owner, json={"revision": 1, "parent_id": child["id"]}
            ).status_code
            == 422
        )
        foreign = folder(client, other, other_course)
        assert (
            client.patch(
                path, headers=owner, json={"revision": 1, "parent_id": foreign["id"]}
            ).status_code
            == 404
        )
        assert (
            client.patch(
                path, headers=owner, json={"revision": 1, "name": "考前"}
            ).status_code
            == 200
        )
        assert (
            client.patch(
                path, headers=owner, json={"revision": 1, "name": "覆盖"}
            ).status_code
            == 409
        )
        assert client.delete(path + "?revision=2", headers=owner).status_code == 409
        parent = child
        for depth in range(3, 7):
            parent = folder(client, owner, course, str(depth), parent["id"])
        assert (
            client.post(
                "/api/v1/note-folders",
                headers=owner,
                json={"course_id": course, "name": "第七级", "parent_id": parent["id"]},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v1/note-folders",
                headers=owner,
                json={"course_id": course, "name": "考前"},
            ).status_code
            == 422
        )


def test_note_folder_patch_bulk_tags_are_atomic_and_links_stable():
    with TestClient(app) as client:
        owner, course = context(client)
        other, other_course = context(client)
        target = folder(client, owner, course)
        a = note(client, owner, course, tags=["旧标签"], folder_id=target["id"])
        b = note(client, owner, course, title="B", content=f"[[note:{a['id']}|原名]]")
        body = {
            "notes": [{"id": n["id"], "revision": n["revision"]} for n in [a, b]],
            "add_tags": ["新标签"],
            "remove_tags": ["旧标签"],
            "folder_id": target["id"],
        }
        stale = body | {
            "notes": [{"id": a["id"], "revision": 1}, {"id": b["id"], "revision": 2}]
        }
        assert (
            client.post("/api/v1/notes/batch", headers=owner, json=stale).status_code
            == 409
        )
        assert client.get("/api/v1/notes/" + a["id"], headers=owner).json() == a
        foreign = note(client, other, other_course)
        assert (
            client.post(
                "/api/v1/notes/batch",
                headers=owner,
                json=body | {"notes": [{"id": foreign["id"], "revision": 1}]},
            ).status_code
            == 404
        )
        changed = client.post("/api/v1/notes/batch", headers=owner, json=body)
        assert changed.status_code == 200, changed.text
        assert all(
            n["tags"] == ["新标签"]
            and n["revision"] == 2
            and n["folder_id"] == target["id"]
            for n in changed.json()
        )
        assert (
            client.get(f"/api/v1/notes/{a['id']}/backlinks", headers=owner).json()[0][
                "id"
            ]
            == b["id"]
        )
        assert (
            client.delete(
                f"/api/v1/note-folders/{target['id']}?revision=1", headers=owner
            ).status_code
            == 409
        )
        cleared = client.patch(
            f"/api/v1/notes/{a['id']}",
            headers=owner,
            json={"revision": 2, "folder_id": None},
        )
        assert cleared.status_code == 200 and cleared.json()["folder_id"] is None
        forbidden = folder(client, other, other_course)
        assert (
            client.patch(
                f"/api/v1/notes/{a['id']}",
                headers=owner,
                json={"revision": 3, "folder_id": forbidden["id"]},
            ).status_code
            == 404
        )
        maximum = note(client, owner, course, tags=[str(i) for i in range(12)])
        assert (
            client.post(
                "/api/v1/notes/batch",
                headers=owner,
                json={
                    "notes": [{"id": maximum["id"], "revision": 1}],
                    "add_tags": ["额外"],
                },
            ).status_code
            == 422
        )


def test_markdown_import_title_tags_folder_utf8_and_idempotency():
    with TestClient(app) as client:
        owner, course = context(client)
        target = folder(client, owner, course)
        data = {
            "request_id": str(uuid4()),
            "course_id": course,
            "folder_id": target["id"],
            "tags": '["复习", "统一标签"]',
        }
        content = "\ufeff# 正文标题不替换文件名\n\n中文 **重点**\n"

        def send(name="中文笔记.MD", raw=content.encode()):
            return client.post(
                "/api/v1/notes/import-markdown",
                headers=owner,
                data=data,
                files={"file": (name, raw, "text/markdown")},
            )

        first = send()
        assert first.status_code == 201, first.text
        row = first.json()
        assert row["title"] == "中文笔记" and row["content"] == content.lstrip("\ufeff")
        assert row["tags"] == ["复习", "统一标签"] and row["folder_id"] == target["id"]
        assert send().json()["id"] == row["id"]
        assert send(raw=b"changed").status_code == 409
        assert send("bad.txt").status_code == 422
        assert send(raw=b"\xff\xfe").status_code == 422
        assert send(raw=b"hello\x00world").status_code == 422
        assert send(raw=b"x" * (2 * 1024 * 1024 + 1)).status_code == 413
        assert len(client.get("/api/v1/notes", headers=owner).json()) == 1


def test_folder_zip_contains_only_selected_notes_and_resolves_links_images():
    with TestClient(app) as client:
        owner, course = context(client)
        top = folder(client, owner, course, "images")
        deep = folder(client, owner, course, "章节 #1", top["id"])
        asset = image(client, owner, course)
        plain = note(client, owner, course, title="未归档")
        a = note(
            client,
            owner,
            course,
            title="A",
            folder_id=deep["id"],
            content=f"[[note:{plain['id']}|根目录]] ![[asset:{asset['id']}|测试图]]",
        )
        note(client, owner, course, title="未选中", folder_id=deep["id"])
        row = done(
            client, owner, create(client, owner, note_ids=[a["id"], plain["id"]])
        )
        with downloaded(client, owner, row) as archive:
            names = set(archive.namelist())
            assert "未归档.md" in names
            member = next(n for n in names if n.endswith("/A.md"))
            assert member.startswith("images（2）/章节 #1/")
            assert len(names) == 3
            for target in re.findall(r"\]\(([^)]+)\)", archive.read(member).decode()):
                path = posixpath.normpath(
                    posixpath.join(posixpath.dirname(member), unquote(target))
                )
                assert path in names


@pytest.mark.parametrize("corrupt", [None, "cycle", "course"])
def test_folder_backup_roundtrip_and_reject_corrupt_tree(corrupt):
    with TestClient(app) as client:
        owner, course = context(client)
        top = folder(client, owner, course, "根")
        child = folder(client, owner, course, "子", top["id"])
        current = note(client, owner, course, folder_id=child["id"])
        other_course = client.post(
            "/api/v1/courses", headers=owner, json={"name": "另一课程"}
        ).json()["id"]
        source = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        body, _ = exported(client, owner)
        if corrupt:

            def edit(manifest):
                rows = {r["id"]: r for r in manifest["tables"]["note_folders"]}
                if corrupt == "cycle":
                    rows[top["id"]]["parent_id"] = child["id"]
                else:
                    rows[child["id"]]["course_id"] = other_course

            body = rewrite_manifest(body, edit)
        with SessionLocal() as db:
            db.delete(db.get(User, source))
            db.commit()
        recipient, _ = empty_account(client)
        result = restored(client, recipient, body)
        assert result["job"]["status"] == ("FAILED" if corrupt else "SUCCEEDED"), result
        if corrupt:
            assert client.get("/api/v1/notes", headers=recipient).json() == []
        else:
            assert (
                client.get(f"/api/v1/notes/{current['id']}", headers=recipient).json()[
                    "folder_id"
                ]
                == child["id"]
            )
            assert (
                len(
                    client.get(
                        "/api/v1/note-folders",
                        headers=recipient,
                        params={"course_id": course},
                    ).json()
                )
                == 2
            )
