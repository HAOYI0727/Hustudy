from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.workers.materials import drain_jobs


def setup_course(client):
    user = client.post(
        "/api/v1/auth/register",
        json={
            "username": "organize_" + uuid4().hex[:10],
            "password": "test-password-123",
        },
    ).json()
    headers = {"Authorization": "Bearer " + user["access_token"]}
    from tests.support.ai_account_test_support import maybe_seed_account

    maybe_seed_account(client, headers)
    course = client.post(
        "/api/v1/courses", headers=headers, json={"name": "资料分类"}
    ).json()["id"]
    return headers, course


def import_document(client, headers, course, body):
    response = client.post(
        f"/api/v1/courses/{course}/documents",
        headers=headers,
        files={"file": ("source.md", body, "text/markdown")},
    )
    assert response.status_code == 202
    drain_jobs()
    version = client.get(
        f"/api/v1/versions/{response.json()['resource_id']}", headers=headers
    ).json()
    return version["document_id"], version["id"]


def test_organization_validation_exact_filters_and_immutable_sources():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        other, _ = setup_course(client)
        doc, version = import_document(
            client, owner, course, "# 进程调度\n\n进程调度需要就绪队列。"
        )
        chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[
            0
        ]
        saved = client.patch(
            f"/api/v1/documents/{doc}",
            headers=owner,
            json={
                "name": "  调度专题  ",
                "category": " 核心章节 ",
                "tags": [" 期末 ", "期末", "A' OR 1=1--", "期末复习"],
            },
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["name"] == "调度专题"
        assert saved.json()["tags"] == ["期末", "A' OR 1=1--", "期末复习"]
        assert saved.json()["updated_at"].endswith("Z") or saved.json()[
            "updated_at"
        ].endswith("+00:00")
        renamed = client.patch(
            f"/api/v1/documents/{doc}", headers=owner, json={"name": "重新命名"}
        ).json()
        assert (
            renamed["tags"] == saved.json()["tags"]
            and renamed["category"] == "核心章节"
        )
        assert (
            client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[0]
            == chunk
        )
        assert (
            client.get(f"/api/v1/versions/{version}", headers=owner).json()[
                "original_filename"
            ]
            == "source.md"
        )
        assert (
            client.patch(
                f"/api/v1/documents/{doc}", headers=other, json={"name": "盗改"}
            ).status_code
            == 404
        )
        for invalid in [
            {"name": "  "},
            {"category": None},
            {"tags": None},
            {"tags": [""]},
            {"tags": ["x" * 33]},
            {"tags": [str(n) for n in range(13)]},
            {"course_id": course},
            {"storage_path": "unsafe"},
        ]:
            assert (
                client.patch(
                    f"/api/v1/documents/{doc}", headers=owner, json=invalid
                ).status_code
                == 422
            )
        path = f"/api/v1/courses/{course}/documents"
        assert (
            len(
                client.get(
                    path, headers=owner, params={"category": "核心章节", "tag": "期末"}
                ).json()
            )
            == 1
        )
        assert client.get(path, headers=owner, params={"tag": "期"}).json() == []
        assert client.get(path, headers=owner, params={"category": "其他"}).json() == []
        for tag in ["期末", "A' OR 1=1--"]:
            hit = client.get(
                f"/api/v1/courses/{course}/search",
                headers=owner,
                params={"q": "进程", "tag": tag},
            ).json()[0]
            assert hit["document_name"] == "重新命名" and hit["version_no"] == 1
        assert (
            client.get(
                f"/api/v1/courses/{course}/search",
                headers=other,
                params={"q": "进程", "tag": "期末"},
            ).status_code
            == 404
        )
        client.patch(f"/api/v1/documents/{doc}", headers=owner, json={"tags": []})
        assert client.get(path, headers=owner, params={"tag": "期末"}).json() == []
        client.delete(f"/api/v1/documents/{doc}", headers=owner)
        assert (
            client.patch(
                f"/api/v1/documents/{doc}", headers=owner, json={"name": "已删除"}
            ).status_code
            == 404
        )


def test_latest_filter_does_not_silently_fall_back_to_old_content():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        doc, old = import_document(client, owner, course, "# 调度\n\n旧版进程知识。")
        uploaded = client.post(
            f"/api/v1/documents/{doc}/versions",
            headers=owner,
            files={"file": ("new.md", "# 调度\n\n新版线程知识。")},
        )
        assert uploaded.status_code == 202
        path = f"/api/v1/courses/{course}/search"
        assert (
            client.get(
                path, headers=owner, params={"q": "进程", "latest_only": True}
            ).json()
            == []
        )
        assert (
            client.get(path, headers=owner, params={"q": "进程"}).json()[0][
                "version_id"
            ]
            == old
        )
        drain_jobs()
        assert (
            client.get(
                path, headers=owner, params={"q": "进程", "latest_only": True}
            ).json()
            == []
        )
        assert (
            client.get(
                path, headers=owner, params={"q": "线程", "latest_only": True}
            ).json()[0]["version_no"]
            == 2
        )
        jobs = client.get(f"/api/v1/courses/{course}/jobs", headers=owner).json()
        assert all(
            job["document_id"] == doc and job["version_no"] in [1, 2] for job in jobs
        )


def test_source_references_follow_note_titles_deletion_version_and_owner():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        other, _ = setup_course(client)
        doc, version = import_document(
            client, owner, course, "# 进程状态\n\n进程状态包括就绪与阻塞。"
        )
        _, foreign_version = import_document(
            client, owner, course, "# 隔离\n\n另一份资料。"
        )
        chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[
            0
        ]
        foreign_chunk = client.get(
            f"/api/v1/versions/{foreign_version}/chunks", headers=owner
        ).json()[0]
        note = client.post(
            "/api/v1/notes",
            headers=owner,
            json={
                "title": "原笔记名",
                "course_id": course,
                "citations": [
                    {
                        "version_id": version,
                        "chunk_id": chunk["id"],
                        "quote": "进程状态",
                    }
                ],
            },
        ).json()
        path = f"/api/v1/versions/{version}/references"
        assert client.get(path, headers=owner).json()[0]["note_id"] == note["id"]
        client.patch(
            f"/api/v1/notes/{note['id']}",
            headers=owner,
            json={
                "title": "最新笔记名",
                "content": "理解",
                "revision": note["revision"],
            },
        )
        assert (
            client.get(path, headers=owner, params={"chunk_id": chunk["id"]}).json()[0][
                "note_title"
            ]
            == "最新笔记名"
        )
        assert client.get(path, headers=other).status_code == 404
        assert (
            client.get(
                path, headers=owner, params={"chunk_id": foreign_chunk["id"]}
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/v1/versions/{foreign_version}/references", headers=owner
            ).json()
            == []
        )
        client.delete(f"/api/v1/notes/{note['id']}", headers=owner)
        assert client.get(path, headers=owner).json() == []
        client.delete(f"/api/v1/documents/{doc}", headers=owner)
        assert client.get(path, headers=owner).status_code == 404
