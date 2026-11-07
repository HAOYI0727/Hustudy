"""Explicit late-chapter scope and persistent QA history stay course-owned."""

from fastapi.testclient import TestClient
from app.main import app
from tests.m1.test_material_organization import setup_course, import_document
from tests.m2.test_remote_ai import configured as configured  # noqa: F401
import pytest


@pytest.mark.usefixtures("configured")
def test_report_selected_late_chunk_never_sends_earlier_text():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        _, version = import_document(
            client,
            owner,
            course,
            "# 第一章\n\n不选的早期内容。\n\n# 第九章\n\n只选择本章的原文。",
        )
        chunks = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()
        chosen = next(c for c in chunks if "只选择" in c["text"])
        response = client.post(
            f"/api/v1/courses/{course}/study-reports/preview",
            headers=owner,
            json={"version_ids": [version], "chunk_ids": [chosen["id"]]},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert len(body["sources"]) == 1 and "不选的" not in body["sources"][0]["text"]
        assert body["report_scope"]["chunk_ids"] == [chosen["id"]]
        other, other_course = setup_course(client)
        _, foreign = import_document(client, other, other_course, "# 第九章\n\n秘密。")
        chunk = client.get(f"/api/v1/versions/{foreign}/chunks", headers=other).json()[
            0
        ]["id"]
        assert (
            client.post(
                f"/api/v1/courses/{course}/study-reports/preview",
                headers=owner,
                json={"version_ids": [version], "chunk_ids": [chunk]},
            ).status_code
            == 404
        )


def test_question_history_excludes_reports_and_other_course():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        other, other_course = setup_course(client)
        doc, version = import_document(
            client, owner, course, "# 苹果\n\n苹果是自制样例。"
        )
        qa = client.post(
            f"/api/v1/courses/{course}/ai-queries",
            headers=owner,
            json={"query": "苹果"},
        ).json()
        client.post(
            f"/api/v1/versions/{version}/study-reports",
            headers=owner,
            json={"mode": "demo"},
        )
        endpoint = f"/api/v1/courses/{course}/ai-results"
        assert [r["id"] for r in client.get(endpoint, headers=owner).json()] == [
            qa["id"]
        ]
        assert client.get(endpoint, headers=other).status_code == 404
        assert (
            client.get(
                f"/api/v1/courses/{other_course}/ai-results", headers=other
            ).json()
            == []
        )
        client.delete(f"/api/v1/documents/{doc}", headers=owner)
        assert (
            client.get(endpoint, headers=owner).json()[0]["result"]["citations"][0][
                "availability"
            ]
            == "unavailable"
        )
