"""Shared course risks: partial updates, CAS, filtering and stable source links."""

from fastapi.testclient import TestClient
from app.main import app
from test_material_organization import setup_course, import_document


def test_partial_updates_conflict_and_source_identity():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        foreign, _ = setup_course(client)
        doc, version = import_document(
            client, owner, course, "# 调度\n\n原引用保持有效。"
        )
        chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[
            0
        ]
        note = client.post(
            "/api/v1/notes",
            headers=owner,
            json={
                "title": "保留来源",
                "course_id": course,
                "content": "原正文",
                "citations": [
                    {
                        "version_id": version,
                        "chunk_id": chunk["id"],
                        "quote": "原引用保持有效。",
                    }
                ],
            },
        ).json()
        path = f"/api/v1/courses/{course}"
        first = client.patch(
            path,
            headers=owner,
            json={
                "revision": 1,
                "description": " 学习目标 ",
                "category": " 专业必修 ",
                "tags": [" 期末 ", "期末", "期末复习"],
            },
        )
        assert first.status_code == 200, first.text
        assert first.json()["tags"] == ["期末", "期末复习"]
        renamed = client.patch(
            path, headers=owner, json={"revision": 2, "name": " 新课程名称 "}
        ).json()
        assert renamed["name"] == "新课程名称"
        assert renamed["description"] == "学习目标"
        assert (
            renamed["category"] == "专业必修"
            and renamed["tags"] == first.json()["tags"]
        )
        assert renamed["revision"] == 3
        assert renamed["updated_at"].endswith(("Z", "+00:00"))
        conflict = client.patch(
            path, headers=owner, json={"revision": 2, "description": "迟到写入"}
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["details"]["server_course"] == renamed
        assert (
            conflict.headers["X-Request-ID"] == conflict.json()["error"]["request_id"]
        )
        assert (
            client.patch(
                path, headers=foreign, json={"revision": 3, "name": "越权"}
            ).status_code
            == 404
        )
        cleared = client.patch(
            path, headers=owner, json={"revision": 3, "description": None, "tags": []}
        ).json()
        assert (
            cleared["description"] is None
            and cleared["tags"] == []
            and cleared["category"] == "专业必修"
        )
        assert (
            client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[0]
            == chunk
        )
        assert (
            client.get(f"/api/v1/courses/{course}/documents", headers=owner).json()[0][
                "id"
            ]
            == doc
        )
        assert (
            client.get(f"/api/v1/notes/{note['id']}", headers=owner).json()["course_id"]
            == course
        )
        citation = client.get(
            f"/api/v1/notes/{note['id']}/citations", headers=owner
        ).json()[0]
        assert (
            citation["chunk_id"] == chunk["id"] and citation["availability"] == "active"
        )


def test_directory_exact_literal_filters_and_input_budgets():
    with TestClient(app) as client:
        owner, _ = setup_course(client)
        foreign, _ = setup_course(client)
        courses = []
        for name, tag in [
            ("100%课程", "期末"),
            ("100_课程", "期末复习"),
            ("中文搜索", "A' OR 1=1--"),
        ]:
            response = client.post(
                "/api/v1/courses",
                headers=owner,
                json={
                    "name": name,
                    "description": " 学习目标 ",
                    "category": " 专业必修 ",
                    "tags": [tag],
                },
            )
            assert response.status_code == 201
            courses.append(response.json())
        client.post(
            "/api/v1/courses",
            headers=foreign,
            json={"name": "100%秘密", "category": "专业必修", "tags": ["期末"]},
        )

        def listing(**params):
            response = client.get("/api/v1/courses", headers=owner, params=params)
            assert response.status_code == 200, response.text
            return response.json()

        assert [
            row["id"] for row in listing(q="%", category="专业必修", tag="期末")
        ] == [courses[0]["id"]]
        assert [row["id"] for row in listing(q="_")] == [courses[1]["id"]]
        assert [row["id"] for row in listing(tag="期末")] == [courses[0]["id"]]
        assert len(listing(q="学习目标", category="专业必修")) == 3
        assert [row["id"] for row in listing(q="A' OR 1=1--")] == [courses[2]["id"]]
        assert listing(tag="末") == [] and listing(category="专业") == []
        assert all(
            row["id"] not in {item["id"] for item in courses}
            for row in client.get("/api/v1/courses", headers=foreign).json()
        )
        assert [row["id"] for row in listing(sort="updated")][:3] == [
            row["id"] for row in reversed(courses)
        ]
        for payload in [
            {"name": "  "},
            {"name": "x", "category": None},
            {"name": "x", "category": " "},
            {"name": "x", "tags": [" "]},
            {"name": "x", "tags": ["a"] * 13},
            {"name": "x", "tags": ["a" * 33]},
            {"name": "x", "category": "a" * 65},
            {"name": "x", "unknown": True},
        ]:
            assert (
                client.post("/api/v1/courses", headers=owner, json=payload).status_code
                == 422
            )
        path = f"/api/v1/courses/{courses[0]['id']}"
        for payload in [
            {},
            {"revision": 1},
            {"name": "new"},
            {"revision": True, "name": "new"},
            {"revision": 0, "name": "new"},
            {"revision": 1, "name": None},
            {"revision": 1, "tags": None},
            {"revision": 1, "category": None},
            {"revision": 1, "unknown": "x"},
        ]:
            assert client.patch(path, headers=owner, json=payload).status_code == 422
        for params in [
            {"q": "a" * 201},
            {"sort": "bad"},
            {"category": ""},
            {"tag": ""},
        ]:
            assert (
                client.get("/api/v1/courses", headers=owner, params=params).status_code
                == 422
            )
