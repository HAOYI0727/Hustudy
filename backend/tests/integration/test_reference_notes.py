"""Source-to-note paging and legacy references never project note contents."""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from app.main import app
from app.core.database import SessionLocal, engine
from app.models import Citation, Note, Document
from app.workers.materials import drain_jobs
from tests.integration.test_source_learning import setup, cited_note
from tests.m1.test_material_organization import setup_course, import_document
from tests.m1.test_preview_assets import import_pdf
from tests.m1.test_manual_transcripts import draft, confirm


def path(version):
    return f"/api/v1/versions/{version}/reference-notes"


def test_grouped_real_paging_literal_search_and_metadata_projection():
    with TestClient(app) as c:
        h, course, uid, doc, version, citations = setup(c)
        for i in range(15):
            cited_note(
                c, h, course, citations, title="TCP 100%_" if i == 0 else f"笔记{i:02}"
            )
        with SessionLocal() as db:
            for note in db.scalars(select(Note).where(Note.user_id == uid)):
                note.updated_at = datetime(2026, 10, 24, tzinfo=timezone.utc)
            db.commit()
        sql = []

        def capture(conn, cursor, statement, parameters, context, many):
            sql.append(statement.lower())

        event.listen(engine, "before_cursor_execute", capture)
        try:
            result = c.get(path(version), headers=h)
            legacy = c.get(f"/api/v1/versions/{version}/references", headers=h)
        finally:
            event.remove(engine, "before_cursor_execute", capture)
        assert result.status_code == 200, result.text
        data = result.json()
        assert data["total"] == 15 and len(data["items"]) == 6
        assert data["course_id"] == course and data["document_id"] == doc
        assert data["version_id"] == version and data["chunk_id"] is None
        assert all(row["citation_count"] == 2 for row in data["items"])
        assert len(legacy.json()) == 30
        assert len([s for s in sql if s.lstrip().startswith("select")]) <= 10
        assert not any("notes.content" in s or "notes.tags" in s for s in sql)
        assert not any(
            s.lstrip().startswith(("insert", "update", "delete")) for s in sql
        )
        assert "私有笔记正文" not in result.text + legacy.text
        ids = []
        for offset in (0, 6, 12):
            page = c.get(path(version), headers=h, params={"offset": offset}).json()
            ids.extend(row["note_id"] for row in page["items"])
        assert len(ids) == len(set(ids)) == 15 and ids == sorted(ids)
        matched = c.get(path(version), headers=h, params={"q": "100%_"}).json()
        assert (
            matched["total"] == 1 and matched["items"][0]["note_title"] == "TCP 100%_"
        )
        assert (
            c.get(path(version), headers=h, params={"q": "没有匹配"}).json()["total"]
            == 0
        )
        single = c.get(
            path(version), headers=h, params={"chunk_id": citations[0]["chunk_id"]}
        ).json()
        assert single["total"] == 15 and all(
            x["citation_count"] == 1 for x in single["items"]
        )


def test_ownership_invalid_quotes_trash_and_note_course_is_preserved():
    with TestClient(app) as c:
        h, course, uid, doc, version, citations = setup(c)
        other, _, _, _, other_version, other_citations = setup(c)
        note = cited_note(c, h, course, citations)
        uncategorized = cited_note(c, h, None, [citations[0]], title="未归课程笔记")
        with SessionLocal() as db:
            db.add(
                Citation(
                    user_id=uid,
                    note_id=note["id"],
                    version_id=version,
                    chunk_id=citations[0]["chunk_id"],
                    quote="伪造原文",
                        quote_hash="0" * 64,
                    locator_type="heading",
                    locator_value="无效",
                )
            )
            db.add(
                Citation(
                    user_id=uid,
                    note_id=note["id"],
                    version_id=version,
                    chunk_id=other_citations[0]["chunk_id"],
                    quote=other_citations[0]["quote"],
                        quote_hash="1" * 64,
                    locator_type="heading",
                    locator_value="越权",
                )
            )
            db.commit()
        data = c.get(path(version), headers=h).json()
        assert data["total"] == 2
        assert (
            next(x for x in data["items"] if x["note_id"] == note["id"])[
                "citation_count"
            ]
            == 2
        )
        assert (
            next(x for x in data["items"] if x["note_id"] == uncategorized["id"])[
                "note_course_id"
            ]
            is None
        )
        assert c.get(path(version), headers=other).status_code == 404
        assert (
            c.get(
                path(version),
                headers=h,
                params={"chunk_id": other_citations[0]["chunk_id"]},
            ).status_code
            == 404
        )
        assert c.get(path(other_version), headers=h).status_code == 404
        assert (
            len(c.get(f"/api/v1/versions/{version}/references", headers=h).json()) == 3
        )
        with SessionLocal() as db:
            db.get(Note, note["id"]).deleted = True
            db.commit()
        assert c.get(path(version), headers=h).json()["total"] == 1
        with SessionLocal() as db:
            db.get(Document, doc).deleted_at = datetime.now(timezone.utc)
            db.commit()
        assert c.get(path(version), headers=h).status_code == 404


def test_new_versions_do_not_inherit_and_budgets_are_enforced():
    with TestClient(app) as c:
        h, course, _, doc, version, citations = setup(c)
        cited_note(c, h, course, citations)
        job = c.post(
            f"/api/v1/documents/{doc}/versions",
            headers=h,
            files={
                "file": (
                    "new.md",
                    "# 新版\n当前版本不继承旧引用。".encode(),
                    "text/markdown",
                )
            },
        ).json()
        drain_jobs()
        assert c.get(path(job["resource_id"]), headers=h).json()["total"] == 0
        assert c.get(path(version), headers=h).json()["total"] == 1
        for params in (
            {"q": "x" * 201},
            {"limit": 51},
            {"limit": 0},
            {"offset": 1000001},
            {"offset": -1},
        ):
            assert c.get(path(version), headers=h, params=params).status_code == 422
        with SessionLocal() as db:
            db.get(Document, doc).library_scope = "question_bank"
            db.commit()
        assert c.get(path(version), headers=h).status_code == 404


def test_quote_preview_uses_unicode_characters_and_never_rewrites_note():
    with TestClient(app) as c:
        h, course = setup_course(c)
        text = "甲" * 179 + "🧠" + "乙" * 50
        _, version = import_document(c, h, course, text)
        chunk = c.get(f"/api/v1/versions/{version}/chunks", headers=h).json()[0]
        note = cited_note(
            c, h, course, [dict(version_id=version, chunk_id=chunk["id"], quote=text)]
        )
        row = c.get(path(version), headers=h).json()["items"][0]
        assert row["quote_excerpt"] == "甲" * 179 + "🧠"
        assert row["note_id"] == note["id"] and row["citation_count"] == 1
        current = c.get(f"/api/v1/notes/{note['id']}", headers=h).json()
        assert (
            current["content"] == note["content"]
            and current["revision"] == note["revision"]
        )


def test_manual_history_is_valid_until_withdrawn_for_both_reference_apis():
    with TestClient(app) as c:
        h, course = setup_course(c)
        pdf = import_pdf(c, h, course)
        first = confirm(c, h, draft(c, h, pdf, text="已经核对的人工原文。"))
        cited_note(
            c,
            h,
            course,
            [
                dict(
                    version_id=pdf["id"],
                    chunk_id=first["chunk_id"],
                    quote=first["text"],
                )
            ],
        )
        confirm(c, h, draft(c, h, pdf, text="新修订的人工原文。", parent=first["id"]))
        assert c.get(path(pdf["id"]), headers=h).json()["total"] == 1
        with SessionLocal() as db:
            from app.models import ManualTranscript

            db.get(ManualTranscript, first["id"]).status = "WITHDRAWN"
            db.commit()
        assert c.get(path(pdf["id"]), headers=h).json()["total"] == 0
        assert c.get(f"/api/v1/versions/{pdf['id']}/references", headers=h).json() == []
