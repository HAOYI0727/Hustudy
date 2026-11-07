from datetime import datetime, timezone
import posixpath
import re
from urllib.parse import unquote

from fastapi.testclient import TestClient
from app.main import app
from app.services.note_export_names import safe_name, allocate_names, archive_filename
from tests.m1.test_materialhub import context
from tests.m3.test_note_tags import create as note
from tests.m3.test_note_exports import create, done, downloaded


def test_portable_names_handle_windows_collisions_controls_and_unicode():
    names = allocate_names(
        [
            ("a", "CON.txt", ".md"),
            ("b", "../目录:标题?", ".md"),
            ("c", "重复", ".md"),
            ("d", "重复", ".md"),
            ("e", "重复（2）", ".md"),
            ("f", "ABC", ".md"),
            ("g", "abc", ".md"),
            ("h", "长" * 240, ".md"),
            ("i", " \x00\n... ", ".md"),
            ("j", "ＣＯＭ１", ".md"),
            ("k", "../../", ".md"),
        ]
    )
    assert names["a"] == "_CON.txt.md"
    assert names["c"] == "重复.md" and names["d"] == "重复（2）.md"
    assert names["j"] == "_COM1.md"
    assert len(set(name.casefold() for name in names.values())) == len(names)
    assert all(
        not re.search(r'[<>:"/\\|?*\x00-\x1f]', name) and not name.endswith((" ", "."))
        for name in names.values()
    )
    assert len(names["h"]) <= 64
    assert safe_name("... ") == "未命名"
    assert len(safe_name("😀" * 60).encode("utf-8")) <= 220
    assert (
        archive_filename(
            datetime(2026, 10, 17, 14, 30, 1, 123000, tzinfo=timezone.utc),
            "Asia/Shanghai",
        )
        == "Hustudy-笔记知识库-2026-10-17_22-30-01-123.zip"
    )


def test_duplicate_course_titles_and_url_characters_keep_links_and_hashes():
    with TestClient(app) as client:
        owner, course = context(client)
        other = client.post(
            "/api/v1/courses", headers=owner, json={"name": "资料测试"}
        ).json()["id"]
        first = note(client, owner, course, title="概念 [1] #50%", content="甲")
        second = note(client, owner, course, title="概念 [1] #50%", content="乙")
        third = note(client, owner, other, title="概念 [1] #50%", content="丙")
        for index, current in enumerate((first, second, third)):
            target = (first, second, third)[(index + 1) % 3]
            result = client.patch(
                "/api/v1/notes/" + current["id"],
                headers=owner,
                json={"revision": 1, "content": f"[[note:{target['id']}|相关概念]]"},
            )
            assert result.status_code == 200
        row = done(client, owner, create(client, owner))
        with downloaded(client, owner, row) as archive:
            paths = archive.namelist()
            assert len(set(paths)) == 3
            assert all(posixpath.dirname(path) == "" for path in paths)
            assert any("（2）" in path for path in paths)
            assert all("概念 [1] #50%" in path for path in paths)
            for path in paths:
                markdown = archive.read(path).decode()
                link = re.search(r"\]\(([^)]+)\)", markdown)[1]
                assert "%23" in link and "%25" in link
                resolved = posixpath.normpath(
                    posixpath.join(posixpath.dirname(path), unquote(link))
                )
                assert resolved in paths and resolved != path
                assert archive.read(resolved)
