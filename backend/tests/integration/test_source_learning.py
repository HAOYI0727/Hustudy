"""Version/chunk links are exact, paged metadata, never a new learning task."""

import json
import re
from datetime import datetime, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import event
from app.main import app
from app.core.database import SessionLocal, engine
from app.models import AIResult, Note, Topic, Document
from app.workers.materials import drain_jobs
from tests.m1.test_material_organization import setup_course, import_document
from tests.m1.test_preview_assets import import_pdf
from tests.m1.test_manual_transcripts import draft, confirm


def topic(client, headers, course, name="进程", parent=None):
    r = client.post(
        f"/api/v1/courses/{course}/topics",
        headers=headers,
        json=dict(name=name, parent_id=parent),
    )
    assert r.status_code == 201, r.text
    return r.json()


def endpoint(version):
    return f"/api/v1/versions/{version}/learning-links"


def cited_note(c, h, course, citations, title="引用笔记"):
    result = c.post(
        "/api/v1/notes",
        headers=h,
        json={
            "course_id": course,
            "title": title,
            "content": "私有笔记正文不会出现在关联列表",
            "citations": citations,
        },
    )
    assert result.status_code == 201, result.text
    return result.json()


def setup(c):
    h, course = setup_course(c)
    uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
    doc, version = import_document(
        c, h, course, "# 进程\n进程拥有独立地址空间。🙂 1\n# 线程\n线程共享进程资源。"
    )
    chunks = c.get(f"/api/v1/versions/{version}/chunks", headers=h).json()
    citations = [
        dict(version_id=version, chunk_id=row["id"], quote=row["text"])
        for row in chunks
    ]
    return h, course, uid, doc, version, citations


def test_links_combine_owned_modules_deduplicate_and_project_metadata_without_writes():
    with TestClient(app) as c:
        h, course, uid, doc, version, citations = setup(c)
        foreign, _ = setup_course(c)
        note = cited_note(c, h, course, citations)
        t = topic(c, h, course)
        assert (
            c.put(
                f"/api/v1/topics/{t['id']}/sources",
                headers=h,
                json={"revision": t["revision"], **citations[0]},
            ).status_code
            == 200
        )
        with SessionLocal() as db:
            for prompt, selected in [
                ("mock-v1", [citations[0]] * 2),
                ("demo-study-report-v2", [citations[1]]),
            ]:
                db.add(
                    AIResult(
                        user_id=uid,
                        course_id=course,
                        query="理解课程",
                        status="grounded",
                        model_mode="demo",
                        prompt_version=prompt,
                        result_json=json.dumps(
                            {"answer": "私有模型正文不返回", "citations": selected}
                        ),
                    )
                )
            db.commit()
        sql = []

        def capture(_conn, _cursor, statement, _params, _context, _many):
            sql.append(statement.lower())

        event.listen(engine, "before_cursor_execute", capture)
        try:
            response = c.get(endpoint(version), headers=h)
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] == 4 and data["counts"] == dict(
            note=1, qa=1, report=1, topic=1, mistake=0
        )
        assert data["document_id"] == doc and data["course_id"] == course
        assert data["version_id"] == version and data["chunk_id"] is None
        assert (
            next(row for row in data["items"] if row["kind"] == "note")["id"]
            == note["id"]
        )
        assert data["checked_at"].endswith(("Z", "+00:00"))
        for secret in (
            "私有笔记正文",
            "私有模型正文",
            "独立地址空间",
            "source_path",
            "provider",
            "quote",
        ):
            assert secret not in response.text
        assert not any(
            s.lstrip().startswith(("insert ", "update ", "delete ", "replace "))
            for s in sql
        )
        projections = "\n".join(
            re.findall(r"\bselect\b(.*?)\bfrom\b", "\n".join(sql), re.S)
        )
        assert (
            "notes.content" not in projections
            and "ai_results.result_json" not in projections
        )
        assert "document_chunks.text" not in projections
        assert c.get(endpoint(version), headers=foreign).status_code == 404
        assert c.get(endpoint(version)).status_code == 401


def test_chunk_scope_original_versions_and_no_name_matching():
    with TestClient(app) as c:
        h, course, uid, doc, version, citations = setup(c)
        first = cited_note(c, h, course, [citations[0]])
        both = cited_note(c, h, course, citations)
        cited_note(c, h, course, [], "进程同名但没有引用")
        assert (
            c.get(
                endpoint(version),
                headers=h,
                params={"chunk_id": citations[1]["chunk_id"]},
            ).json()["items"][0]["id"]
            == both["id"]
        )
        assert (
            c.get(
                endpoint(version),
                headers=h,
                params={"chunk_id": citations[0]["chunk_id"]},
            ).json()["total"]
            == 2
        )
        added = c.post(
            f"/api/v1/documents/{doc}/versions",
            headers=h,
            files={
                "file": ("v2.md", "# 进程\n进程拥有独立地址空间。🙂", "text/markdown")
            },
        ).json()
        drain_jobs()
        assert c.get(endpoint(added["resource_id"]), headers=h).json()["total"] == 0
        assert (
            c.get(
                endpoint(added["resource_id"]),
                headers=h,
                params={"chunk_id": citations[0]["chunk_id"]},
            ).status_code
            == 404
        )
        assert c.get(endpoint(version), headers=h).json()["total"] == 2
        assert c.delete(f"/api/v1/notes/{first['id']}", headers=h).status_code == 204
        assert c.get(endpoint(version), headers=h).json()["total"] == 1
        with SessionLocal() as db:
            db.get(Document, doc).library_scope = "question_bank"
            db.commit()
        assert c.get(endpoint(version), headers=h).status_code == 404
        with SessionLocal() as db:
            db.get(Document, doc).library_scope = "material"
            db.commit()
        assert c.delete(f"/api/v1/documents/{doc}", headers=h).status_code == 204
        assert c.get(endpoint(version), headers=h).status_code == 404


def test_literal_title_search_stable_sql_pagination_and_validation():
    with TestClient(app) as c:
        h, course, uid, doc, version, citations = setup(c)
        same = datetime(2026, 10, 23, tzinfo=timezone.utc)
        ids = [
            cited_note(c, h, course, citations, f"分页笔记{i:02}")["id"]
            for i in range(27)
        ]
        with SessionLocal() as db:
            for identity in ids:
                db.get(Note, identity).updated_at = same
            db.commit()
        cited_note(c, h, course, citations[:1], "100%_SQL ' 字面标题")
        collected = []
        for offset in (0, 10, 20):
            response = c.get(
                endpoint(version),
                headers=h,
                params={"kind": "note", "q": "分页笔记", "offset": offset, "limit": 10},
            )
            assert response.status_code == 200, response.text
            page = response.json()
            assert page["total"] == 27 and page["counts"]["note"] == 27
            collected.extend(row["id"] for row in page["items"])
        assert collected == sorted(ids) and len(set(collected)) == 27
        assert (
            c.get(endpoint(version), headers=h, params={"q": "%_sql '"}).json()["total"]
            == 1
        )
        assert (
            c.get(endpoint(version), headers=h, params={"q": "私有笔记正文"}).json()[
                "total"
            ]
            == 0
        )
        assert (
            c.get(endpoint(version), headers=h, params={"q": "' OR 1=1 --"}).json()[
                "total"
            ]
            == 0
        )
        assert (
            c.get(endpoint(version), headers=h, params={"offset": 100}).json()["items"]
            == []
        )
        for bad in (
            {"kind": "unknown"},
            {"chunk_id": "bad"},
            {"offset": -1},
            {"offset": 1000001},
            {"limit": 0},
            {"limit": 51},
            {"q": "字" * 201},
        ):
            assert c.get(endpoint(version), headers=h, params=bad).status_code == 422
        assert (
            c.get(
                endpoint(version), headers=h, params={"chunk_id": str(uuid4())}
            ).status_code
            == 404
        )


def test_invalid_quotes_partial_retired_results_and_inactive_topics_excluded():
    with TestClient(app) as c:
        h, course, uid, doc, version, citations = setup(c)
        own_other = c.post(
            "/api/v1/courses", headers=h, json={"name": "另一个课程"}
        ).json()["id"]
        with SessionLocal() as db:
            cases = [
                ({"citations": [citations[0]]}, "grounded", course),
                ({"citations": [citations[0]], "partial": True}, "grounded", course),
                (
                    {"citations": [citations[0]], "result_kind": "question_drafts"},
                    "grounded",
                    course,
                ),
                ({"citations": [citations[0]]}, "provider_error", course),
                (
                    {"citations": [{**citations[0], "quote": "假引用"}]},
                    "grounded",
                    course,
                ),
                ({"nested": {"citations": [citations[0]]}}, "grounded", course),
                ({"citations": [citations[0]]}, "grounded", own_other),
                (
                    {"citations": ["legacy", 7, None, {}, citations[1]]},
                    "grounded",
                    course,
                ),
                ({"citations": {"legacy": citations[0]}}, "grounded", course),
                ({"citations": [{**citations[0], "quote": "　"}]}, "grounded", course),
                ({"citations": [{**citations[0], "quote": 1}]}, "grounded", course),
                ({"citations": [{**citations[0], "quote": True}]}, "grounded", course),
            ]
            for body, status, cid in cases:
                db.add(
                    AIResult(
                        user_id=uid,
                        course_id=cid,
                        query="原结果",
                        status=status,
                        result_json=json.dumps(body),
                        model_mode="demo",
                    )
                )
            for extra in ({}, {"deleted_by_user": True}):
                db.add(
                    Topic(
                        user_id=uid,
                        course_id=course,
                        name="来源知识点",
                        sources_json=json.dumps({"citations": [citations[0]], **extra}),
                    )
                )
            db.add(
                Topic(
                    user_id=uid,
                    course_id=course,
                    name="已合并",
                    merged_into_id=str(uuid4()),
                    sources_json=json.dumps({"citations": [citations[0]]}),
                )
            )
            db.commit()
        response = c.get(endpoint(version), headers=h)
        assert response.status_code == 200, response.text
        assert response.json()["counts"] == dict(
            note=0, qa=2, report=0, topic=1, mistake=0
        )


def test_manual_sources_withdrawal_and_course_revocation():
    with TestClient(app) as c:
        h, course = setup_course(c)
        uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        pdf = import_pdf(c, h, course)
        text = confirm(c, h, draft(c, h, pdf, text="人工确认的进程摘录。"))
        citation = dict(
            version_id=pdf["id"], chunk_id=text["chunk_id"], quote=text["text"]
        )
        cited_note(c, h, course, [citation])
        with SessionLocal() as db:
            db.add(
                AIResult(
                    user_id=uid,
                    course_id=course,
                    query="人工来源",
                    status="grounded",
                    result_json=json.dumps({"citations": [citation]}),
                    model_mode="demo",
                )
            )
            db.add(
                Topic(
                    user_id=uid,
                    course_id=course,
                    name="原文依据",
                    sources_json=json.dumps({"citations": [citation]}),
                )
            )
            db.commit()
        assert c.get(endpoint(pdf["id"]), headers=h).json()["total"] == 3
        assert (
            c.post(
                f"/api/v1/transcripts/{text['id']}/withdraw",
                headers=h,
                json={"revision": text["revision"]},
            ).status_code
            == 200
        )
        assert c.get(endpoint(pdf["id"]), headers=h).json()["total"] == 0
        assert (
            c.delete(f"/api/v1/courses/{course}?revision=1", headers=h).status_code
            == 204
        )
        assert c.get(endpoint(pdf["id"]), headers=h).status_code == 404
