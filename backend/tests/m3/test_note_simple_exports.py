from pathlib import Path
import hashlib
import re
from urllib.parse import unquote
from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import Asset, NoteExport
from tests.m1.test_materialhub import context
from tests.m3.test_note_tags import create as note
from tests.m3.test_note_exports import create, done, downloaded, image


def test_selected_plain_markdown_only_and_unselected_data_excluded():
    with TestClient(app) as client:
        owner, course = context(client)
        hidden = note(client, owner, course, title="不导出", content="不应进入包的正文")
        asset = image(client, owner, course)
        first = note(
            client,
            owner,
            course,
            title="复习总结",
            content=f"[[note:{hidden['id']}|相关概念]] ![[asset:{asset['id']}|状态图]]",
        )
        second = note(
            client,
            owner,
            course,
            title="复习总结",
            content=f"[[note:{first['id']}|第一篇]]",
        )
        row = done(
            client,
            owner,
            create(
                client,
                owner,
                note_ids=[first["id"], second["id"]],
                include_images=False,
            ),
        )
        assert (
            row["layout"] == "simple"
            and row["counts"]["notes"] == 2
            and row["counts"]["assets"] == 0
        )
        with downloaded(client, owner, row) as archive:
            assert set(archive.namelist()) == {"复习总结.md", "复习总结（2）.md"}
            content = "\n".join(
                archive.read(name).decode() for name in archive.namelist()
            )
            assert "未随包导出" in content and "未附带图片" in content
            assert "不应进入包的正文" not in content
            assert hidden["id"] not in content and asset["id"] not in content
            assert ".md)" in content


def test_selection_validation_idempotency_and_default_freezes_all_ids():
    with TestClient(app) as client:
        owner, course = context(client)
        stranger, other = context(client)
        first = note(client, owner, course)
        second = note(client, owner, course, title="第二篇")
        foreign = note(client, stranger, other)
        for ids, status in [
            ([], 422),
            ([first["id"], first["id"]], 422),
            ([first["id"], foreign["id"]], 404),
        ]:
            result = client.post(
                "/api/v1/note-exports",
                headers=owner,
                json={"request_id": str(uuid4()), "note_ids": ids},
            )
            assert result.status_code == status
        request_id = str(uuid4())
        payload = {"request_id": request_id, "note_ids": [first["id"], second["id"]]}
        row = client.post("/api/v1/note-exports", headers=owner, json=payload).json()
        assert (
            client.post(
                "/api/v1/note-exports",
                headers=owner,
                json=payload | {"note_ids": list(reversed(payload["note_ids"]))},
            ).status_code
            == 202
        )
        for change in [{"note_ids": [first["id"]]}, {"include_images": False}]:
            assert (
                client.post(
                    "/api/v1/note-exports", headers=owner, json=payload | change
                ).status_code
                == 409
            )
        done(client, owner, row)
        all_row = client.post(
            "/api/v1/note-exports", headers=owner, json={"request_id": str(uuid4())}
        ).json()
        note(client, owner, course, title="提交后新增", content="不加入已确认范围")
        all_row = done(client, owner, all_row)
        with downloaded(client, owner, all_row) as archive:
            assert set(archive.namelist()) == {"调度笔记.md", "第二篇.md"}
        assert all_row["counts"]["assets"] == 0


def test_plain_export_does_not_read_optional_image_and_selection_survives_retry():
    with TestClient(app) as client:
        owner, course = context(client)
        asset = image(client, owner, course)
        first = note(
            client, owner, course, title="所选", content=f"![[asset:{asset['id']}|图]]"
        )
        with SessionLocal() as db:
            path = Path(db.get(Asset, asset["id"]).storage_path)
        original = path.read_bytes()
        path.write_bytes(b"corrupt")
        plain = done(
            client,
            owner,
            create(client, owner, note_ids=[first["id"]], include_images=False),
        )
        assert plain["job"]["status"] == "SUCCEEDED"
        with downloaded(client, owner, plain) as archive:
            assert archive.namelist() == ["所选.md"]
        full = done(
            client,
            owner,
            create(client, owner, note_ids=[first["id"]], include_images=True),
        )
        assert full["job"]["status"] == "FAILED"
        note(client, owner, course, title="后新增")
        path.write_bytes(original)
        assert (
            client.post(
                f"/api/v1/note-exports/{full['id']}/retry", headers=owner
            ).status_code
            == 202
        )
        full = done(client, owner, full)
        with downloaded(client, owner, full) as archive:
            names = archive.namelist()
            assert len(names) == 2 and "所选.md" in names
            assert any(name.startswith("images/") for name in names)
        with SessionLocal() as db:
            assert db.get(NoteExport, full["id"]).sources_json["request"][
                "selected_ids"
            ] == [first["id"]]


def test_deleted_selection_fails_instead_of_silently_exporting_others():
    with TestClient(app) as client:
        owner, course = context(client)
        first = note(client, owner, course)
        second = note(client, owner, course, title="保留")
        row = create(client, owner, note_ids=[first["id"], second["id"]])
        assert (
            client.delete(
                f"/api/v1/notes/{first['id']}?revision=1", headers=owner
            ).status_code
            == 204
        )
        row = done(client, owner, row)
        assert row["job"]["status"] == "FAILED" and "所选笔记" in row["job"]["error"]


def test_single_markdown_download_uses_safe_readable_title():
    with TestClient(app) as client:
        owner, course = context(client)
        for title, expected in [
            ("进程与线程", "进程与线程.md"),
            ("CON.txt", "_CON.txt.md"),
            ("概念/步骤:一?", "概念_步骤_一_.md"),
        ]:
            current = note(client, owner, course, title=title)
            response = client.get(
                f"/api/v1/notes/{current['id']}/export", headers=owner
            )
            assert response.status_code == 200
            assert (
                unquote(response.headers["content-disposition"].split("UTF-8''")[1])
                == expected
            )
            assert title in response.text


def test_default_includes_only_selected_notes_images_deduplicated(tmp_path):
    with TestClient(app) as client:
        owner, course = context(client)
        shared, extra, unused = [image(client, owner, course) for _ in range(3)]
        with SessionLocal() as db:
            original_hash = hashlib.sha256(
                Path(db.get(Asset, shared["id"]).storage_path).read_bytes()
            ).hexdigest()
        for asset, name in [
            (shared, "共用 图 #1"),
            (extra, "未选笔记专用"),
            (unused, "图库闲置"),
        ]:
            assert (
                client.patch(
                    f"/api/v1/assets/{asset['id']}",
                    headers=owner,
                    json={"revision": asset["revision"], "name": name},
                ).status_code
                == 200
            )
        third = note(
            client, owner, course, title="C", content=f"![[asset:{extra['id']}|C的图]]"
        )
        first = note(
            client,
            owner,
            course,
            title="A",
            content=f"![[asset:{shared['id']}|共用]]\n[[note:{third['id']}|C]]",
        )
        second = note(
            client,
            owner,
            course,
            title="B",
            content=f"![[asset:{shared['id']}|再次引用]]\n[[note:{first['id']}|A]]",
        )
        response = client.post(
            "/api/v1/note-exports",
            headers=owner,
            json={
                "request_id": str(uuid4()),
                "note_ids": [first["id"], second["id"]],
            },
        )
        assert response.status_code == 202
        row = done(client, owner, response.json())
        assert row["job"]["status"] == "SUCCEEDED"
        assert row["counts"]["assets"] == 1
        with downloaded(client, owner, row) as archive:
            assert set(archive.namelist()) == {"A.md", "B.md", "images/共用 图 #1.png"}
            archive.extractall(tmp_path)
        for name in ["A.md", "B.md"]:
            markdown = (tmp_path / name).read_text(encoding="utf-8")
            paths = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
            assert len(paths) == 1 and "%20" in paths[0] and "%23" in paths[0]
            local_image = tmp_path / unquote(paths[0])
            assert hashlib.sha256(local_image.read_bytes()).hexdigest() == original_hash
        with SessionLocal() as db:
            sources = db.get(NoteExport, row["id"]).sources_json
            assert set(sources["notes"]) == {first["id"], second["id"]}
            assert sources["assets"] == [shared["id"]]
