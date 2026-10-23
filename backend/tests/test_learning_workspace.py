"""Real isolated API: metadata bounds, ownership and frozen source revocation."""

import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.database import engine
from sqlalchemy import event
from app.models import (
    AIResult,
    ExamBlueprint,
    ExamPaper,
    ExamAttempt,
    Mistake,
    PastPaper,
    PastQuestion,
)
from test_material_organization import setup_course, import_document


def snapshot(owner_id, course_id, version_id, chunk):
    with SessionLocal() as db:
        blueprint = ExamBlueprint(
            user_id=owner_id, course_id=course_id, name="自制练习", config_json="{}"
        )
        db.add(blueprint)
        db.flush()
        paper = ExamPaper(
            user_id=owner_id,
            course_id=course_id,
            blueprint_id=blueprint.id,
            title="已保存的练习",
            status="READY",
            questions_json="[]",
        )
        db.add(paper)
        db.flush()
        attempt = ExamAttempt(
            user_id=owner_id,
            paper_id=paper.id,
            status="IN_PROGRESS",
            answers_json='{"private":"不能泄露"}',
        )
        db.add(attempt)
        db.flush()
        mistake = Mistake(
            user_id=owner_id,
            attempt_id=attempt.id,
            question_id="test-question",
            detail_json=json.dumps(
                {
                    "question": {
                        "stem": "私有题干",
                        "answer": "标准答案不能泄露",
                        "source_version_id": version_id,
                        "citations": [
                            {
                                "version_id": version_id,
                                "chunk_id": chunk["id"],
                                "quote": "可核对原文。",
                            }
                        ],
                    }
                }
            ),
        )
        db.add(mistake)
        bank = PastPaper(
            user_id=owner_id,
            course_id=course_id,
            title="待核验题库",
            content_hash="test-hash",
        )
        db.add(bank)
        db.flush()
        db.add(
            PastQuestion(
                user_id=owner_id,
                paper_id=bank.id,
                number="1",
                stem="题干不能泄露",
                answer="隐藏答案",
                status="DRAFT",
            )
        )
        db.commit()
        return attempt.id, mistake.id


def test_sections_are_owned_bounded_metadata_and_do_not_fetch_note_bodies():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        foreign, _ = setup_course(client)
        document, version = import_document(
            client, owner, course, "# 自制讲义\n\n可核对原文。"
        )
        for i in range(9):
            response = client.post(
                "/api/v1/notes",
                headers=owner,
                json={
                    "course_id": course,
                    "title": f"笔记{i}",
                    "content": "绝不能进入摘要的笔记正文",
                },
            )
            assert response.status_code == 201
        summary = client.get(f"/api/v1/courses/{course}/workspace/notes", headers=owner)
        assert summary.status_code == 200, summary.text
        body = summary.json()
        assert body["counts"]["total"] == 9 and len(body["recent"]) == 6
        assert (
            "绝不能进入摘要" not in summary.text and "content" not in body["recent"][0]
        )
        material = client.get(
            f"/api/v1/courses/{course}/workspace/materials", headers=owner
        ).json()
        assert material["counts"]["total"] == 1
        assert material["recent"][0]["document_id"] == document
        assert material["recent"][0]["version_id"] == version
        for domain in ("materials", "notes", "study", "practice"):
            path = f"/api/v1/courses/{course}/workspace/{domain}"
            assert client.get(path, headers=foreign).status_code == 404
            assert client.get(path).status_code == 401
            assert (
                client.get(path, headers=owner)
                .json()["checked_at"]
                .endswith(("Z", "+00:00"))
            )
        assert (
            client.get(
                f"/api/v1/courses/{course}/workspace/unknown", headers=owner
            ).status_code
            == 422
        )


def test_counts_exclude_trash_and_retired_generation_and_deleted_course():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        user_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        note = client.post(
            "/api/v1/notes",
            headers=owner,
            json={"course_id": course, "title": "回收站笔记", "content": "正文"},
        ).json()
        assert (
            client.delete(f"/api/v1/notes/{note['id']}", headers=owner).status_code
            == 204
        )
        with SessionLocal() as db:
            for i in range(8):
                db.add(
                    AIResult(
                        user_id=user_id,
                        course_id=course,
                        query=f"问题{i}",
                        status="grounded",
                        model_mode="demo",
                        prompt_version="demo-study-report-v2",
                        result_json='{"answer":"私有结果正文"}',
                    )
                )
            db.add(
                AIResult(
                    user_id=user_id,
                    course_id=course,
                    query="已停用的题目生成",
                    status="grounded",
                    model_mode="demo",
                    result_json='{"result_kind":"question_drafts"}',
                )
            )
            db.commit()
        notes = client.get(
            f"/api/v1/courses/{course}/workspace/notes", headers=owner
        ).json()
        assert notes["counts"]["total"] == 0 and notes["recent"] == []
        response = client.get(
            f"/api/v1/courses/{course}/workspace/study", headers=owner
        )
        assert response.json()["counts"] == {"total": 8, "grounded": 8, "failed": 0}
        assert (
            len(response.json()["recent"]) == 6
            and response.json()["recent"][0]["kind"] == "report"
        )
        assert "私有结果正文" not in response.text
        assert (
            client.delete(
                f"/api/v1/courses/{course}?revision=1", headers=owner
            ).status_code
            == 204
        )
        assert (
            client.get(
                f"/api/v1/courses/{course}/workspace/study", headers=owner
            ).status_code
            == 404
        )


def test_practice_metadata_never_leaks_answers_and_mistake_sources_revoke():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        foreign, _ = setup_course(client)
        user_id = client.get("/api/v1/auth/me", headers=owner).json()["id"]
        document, version = import_document(
            client, owner, course, "# 原始资料\n\n可核对原文。"
        )
        chunk = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()[
            0
        ]
        attempt_id, mistake_id = snapshot(user_id, course, version, chunk)
        response = client.get(
            f"/api/v1/courses/{course}/workspace/practice", headers=owner
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["counts"]["in_progress"] == 1 and data["counts"]["pending"] == 1
        assert data["recent"][0]["id"] == attempt_id
        assert all(
            word not in response.text
            for word in ("标准答案", "私有题干", "不能泄露", "answers_json")
        )
        path = f"/api/v1/mistakes/{mistake_id}/sources"
        assert client.get(path, headers=foreign).status_code == 404
        sources = client.get(path, headers=owner).json()
        assert sources["course_id"] == course and len(sources["items"]) == 1
        assert sources["items"][0]["availability"] == "active"
        assert sources["items"][0]["chunk_id"] == chunk["id"]
        statements = []

        def capture(_connection, _cursor, statement, _parameters, _context, _many):
            statements.append(statement.strip().split()[0].upper())

        event.listen(engine, "before_cursor_execute", capture)
        try:
            assert client.get(path, headers=owner).status_code == 200
            for domain in ("materials", "notes", "study", "practice"):
                assert (
                    client.get(
                        f"/api/v1/courses/{course}/workspace/{domain}", headers=owner
                    ).status_code
                    == 200
                )
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert not {"INSERT", "UPDATE", "DELETE", "REPLACE"}.intersection(statements)
        assert (
            client.get(
                f"/api/v1/attempts/{attempt_id}?course_id=wrong-course", headers=owner
            ).status_code
            == 404
        )
        assert (
            client.delete(f"/api/v1/documents/{document}", headers=owner).status_code
            == 204
        )
        revoked = client.get(path, headers=owner).json()
        assert revoked["items"][0]["availability"] == "unavailable"
        assert revoked["items"][0]["document_id"] is None
        with SessionLocal() as db:
            assert (
                json.loads(db.get(Mistake, mistake_id).detail_json)["question"][
                    "answer"
                ]
                == "标准答案不能泄露"
            )
