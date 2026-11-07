from fastapi.testclient import TestClient
from app.main import app
from tests.m1.test_preview_assets import account, png, capture, import_pdf


def upload(client, owner, course, name="figure.png"):
    response = client.post(
        f"/api/v1/courses/{course}/assets",
        headers=owner,
        files={"file": (name, png(), "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_rename_keeps_bytes_source_uuid_and_note_refs_and_rejects_stale_edits():
    with TestClient(app) as c:
        h, course = account(c)
        version = import_pdf(c, h, course)
        image = capture(c, h, course, version["id"]).json()
        url = f"/api/v1/assets/{image['id']}"
        meta = c.get(url + "/metadata", headers=h).json()
        note = c.post(
            "/api/v1/notes",
            headers=h,
            json={
                "title": "图表笔记",
                "course_id": course,
                "content": f"![[asset:{image['id']}|原说明]]",
            },
        ).json()
        saved = c.patch(
            url,
            headers=h,
            json={
                "revision": 1,
                "name": " 状态转换图 ",
                "alt": "人工整理的图示",
                "tags": [" 重点 ", "图表", "重点"],
            },
        )
        assert saved.status_code == 200, saved.text
        data = saved.json()
        assert data["name"] == "状态转换图" and data["tags"] == ["重点", "图表"]
        assert data["revision"] == 2 and data["updated_at"] != image["updated_at"]
        conflict = c.patch(
            url, headers=h, json={"revision": 1, "alt": "另一个窗口的输入"}
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["details"]["server_asset"] == data
        assert c.get(url, headers=h).content == png()
        after = c.get(url + "/metadata", headers=h).json()
        for field in (
            "id",
            "sha256",
            "original_filename",
            "source_version_id",
            "source_page",
            "source_locator_type",
        ):
            assert after[field] == meta[field]
        assert c.get(url + "/references", headers=h).json()[0]["id"] == note["id"]
        assert (
            c.get(f"/api/v1/notes/{note['id']}", headers=h).json()["content"]
            == note["content"]
        )
        assert (
            c.get(f"/api/v1/courses/{course}/assets", headers=h).json()[0]["name"]
            == data["name"]
        )


def test_literal_metadata_filters_pagination_and_deleted_source_scope():
    with TestClient(app) as c:
        h, course = account(c)
        foreign, other = account(c)
        url = f"/api/v1/courses/{course}/assets/page"
        version = import_pdf(c, h, course)
        captured = capture(c, h, course, version["id"]).json()
        external = upload(c, h, course, "100%_图表.png")
        another = upload(c, h, course, "other.png")
        secret = upload(c, foreign, other, "private.png")
        for image, labels in (
            (captured, ["图表"]),
            (external, ["图", "重点"]),
            (another, ["公式"]),
        ):
            assert (
                c.patch(
                    f"/api/v1/assets/{image['id']}",
                    headers=h,
                    json={"revision": 1, "tags": labels, "alt": "中文说明"},
                ).status_code
                == 200
            )
        page = c.get(
            url, headers=h, params={"q": "中文", "limit": 2, "sort": "oldest"}
        ).json()
        rest = c.get(
            url,
            headers=h,
            params={"q": "中文", "limit": 2, "offset": 2, "sort": "oldest"},
        ).json()
        assert page["total"] == rest["total"] == 3
        assert len(page["items"]) == 2 and len(rest["items"]) == 1
        assert len({i["id"] for i in page["items"] + rest["items"]}) == 3
        assert set(page["tags"]) == {"图表", "图", "重点", "公式"}
        assert (
            c.get(url, headers=h, params={"q": "%_"}).json()["items"][0]["id"]
            == external["id"]
        )
        assert c.get(url, headers=h, params={"tag": "图"}).json()["total"] == 1
        assert (
            c.get(url, headers=h, params={"q": "重点", "origin": "external"}).json()[
                "total"
            ]
            == 1
        )
        assert c.get(url, headers=h, params={"origin": "captured"}).json()["total"] == 1
        assert c.get(url, headers=h, params={"q": "private"}).json()["total"] == 0
        assert c.get(url, headers=foreign).status_code == 404
        assert (
            c.patch(
                f"/api/v1/assets/{secret['id']}",
                headers=h,
                json={"revision": 1, "name": "窃改"},
            ).status_code
            == 404
        )
        assert (
            c.delete(
                f"/api/v1/documents/{version['document_id']}", headers=h
            ).status_code
            == 204
        )
        assert (
            c.patch(
                f"/api/v1/assets/{captured['id']}",
                headers=h,
                json={"revision": 2, "name": "来源已删"},
            ).status_code
            == 404
        )
        current = c.get(url, headers=h).json()
        assert current["total"] == 2 and "图表" not in current["tags"]
        assert (
            c.delete(f"/api/v1/assets/{external['id']}", headers=h).status_code == 204
        )
        current = c.get(url, headers=h).json()
        assert current["total"] == 1 and current["tags"] == ["公式"]


def test_invalid_metadata_and_resource_budget_do_not_change_image():
    with TestClient(app) as c:
        h, course = account(c)
        image = upload(c, h, course)
        url = f"/api/v1/assets/{image['id']}"
        for payload in (
            {"revision": True, "name": "name"},
            {"revision": 1},
            {"revision": 1, "name": " "},
            {"revision": 1, "tags": None},
            {"revision": 1, "tags": ["x"] * 13},
            {"revision": 1, "tags": ["x" * 33]},
            {"revision": 1, "alt": "x" * 501},
            {"revision": 1, "source_page": 4},
        ):
            assert c.patch(url, headers=h, json=payload).status_code == 422
        assert c.get(url + "/metadata", headers=h).json()["revision"] == 1
        page = f"/api/v1/courses/{course}/assets/page"
        for params in (
            {"limit": 49},
            {"offset": -1},
            {"q": "x" * 201},
            {"sort": "unknown"},
        ):
            assert c.get(page, headers=h, params=params).status_code == 422
        assert (
            c.patch(
                url, headers=h, json={"revision": 1, "alt": "", "tags": []}
            ).status_code
            == 200
        )
