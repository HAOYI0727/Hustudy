from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app


def register(client):
    result = client.post(
        "/api/v1/auth/register",
        json={"username": "notes_" + uuid4().hex[:10], "password": "test-password-123"},
    )
    return {"Authorization": "Bearer " + result.json()["access_token"]}


def test_note_conflict_links_export_and_permissions():
    with TestClient(app) as client:
        owner, stranger = register(client), register(client)
        target = client.post(
            "/api/v1/notes", headers=owner, json={"title": "概念", "content": "原文"}
        ).json()
        note_id = target["id"]
        source = client.post(
            "/api/v1/notes",
            headers=owner,
            json={"title": "复习", "content": f"[[note:{note_id}|概念]]"},
        ).json()
        path = f"/api/v1/notes/{note_id}"
        saved = client.patch(
            path,
            headers=owner,
            json={"revision": 1, "title": "新名称", "content": "服务器内容"},
        )
        assert saved.status_code == 200 and saved.json()["revision"] == 2
        conflict = client.patch(
            path, headers=owner, json={"revision": 1, "content": "旧窗口内容"}
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["details"]["server_content"] == "服务器内容"
        assert client.get(path, headers=owner).json()["content"] == "服务器内容"
        links = client.get(path + "/backlinks", headers=owner).json()
        assert [row["id"] for row in links] == [source["id"]]
        exported = client.get(path + "/export", headers=owner)
        assert exported.status_code == 200
        assert exported.text == "# 新名称\n\n服务器内容\n"
        assert "attachment" in exported.headers["content-disposition"]
        for suffix in ["", "/export", "/backlinks"]:
            assert client.get(path + suffix, headers=stranger).status_code == 404
        assert (
            client.patch(
                path, headers=stranger, json={"revision": 2, "content": "unauthorized"}
            ).status_code
            == 404
        )
        client.delete(path, headers=owner)
        assert client.get(path + "/export", headers=owner).status_code == 404
