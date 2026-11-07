import io
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import select
from app.main import app
from app.core.database import SessionLocal
from app.models import DocumentChunk, ManualTranscript
from app.workers.materials import drain_jobs


def setup(client, source_data=None):
    user = client.post(
        "/api/v1/auth/register",
        json={
            "username": "transcript_" + uuid4().hex[:8],
            "password": "test-password-123",
        },
    ).json()
    h = {"Authorization": "Bearer " + user["access_token"]}
    course = client.post(
        "/api/v1/courses", headers=h, json={"name": "人工来源"}
    ).json()["id"]
    pdf = PdfWriter()
    pdf.add_blank_page(width=300, height=400)
    pdf.add_blank_page(width=300, height=400)
    out = io.BytesIO()
    pdf.write(out)
    job = client.post(
        f"/api/v1/courses/{course}/documents",
        headers=h,
        files={"file": ("scan.pdf", source_data or out.getvalue(), "application/pdf")},
    ).json()
    drain_jobs()
    version = client.get(f"/api/v1/versions/{job['resource_id']}", headers=h).json()
    return h, course, version, job["id"]


def draft(client, h, v, text="滑动窗口约束发送范围。", parent=None, page=1):
    r = client.post(
        f"/api/v1/versions/{v['id']}/transcripts",
        headers=h,
        json={"page": page, "text": text, "supersedes_id": parent},
    )
    assert r.status_code == 201, r.text
    return r.json()


def confirm(client, h, t):
    r = client.post(
        f"/api/v1/transcripts/{t['id']}/confirm",
        headers=h,
        json={"revision": t["revision"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_draft_confirmation_search_citation_and_parser_retry_preserve_manual_source():
    with TestClient(app) as c:
        h, course, v, job = setup(c)
        assert v["parse_status"] == "FAILED"
        t = draft(c, h, v)
        search = f"/api/v1/courses/{course}/search?q=滑动窗口"
        assert c.get(search, headers=h).json() == []
        assert c.get(f"/api/v1/versions/{v['id']}/chunks", headers=h).json() == []
        saved = confirm(c, h, t)
        assert saved["confirmed_by"] and saved["confirmed_at"].endswith(("Z", "+00:00"))
        again = confirm(c, h, t)
        assert again["chunk_id"] == saved["chunk_id"]
        hit = c.get(search, headers=h).json()[0]
        assert (
            hit["source_kind"] == "manual_transcript"
            and hit["transcript_id"] == t["id"]
        )
        chunk = c.get(f"/api/v1/versions/{v['id']}/chunks", headers=h).json()[0]
        assert chunk["text"][chunk["start_offset"] : chunk["end_offset"]] == t["text"]
        assert chunk["transcript_status"] == "CONFIRMED"
        note = c.post(
            "/api/v1/notes",
            headers=h,
            json={
                "title": "补录引用",
                "course_id": course,
                "citations": [
                    {
                        "version_id": v["id"],
                        "chunk_id": saved["chunk_id"],
                        "quote": t["text"],
                    }
                ],
            },
        ).json()
        cites = c.get(f"/api/v1/notes/{note['id']}/citations", headers=h).json()
        assert cites[0]["source_kind"] == "manual_transcript"
        ai = c.post(
            f"/api/v1/courses/{course}/ai-queries",
            headers=h,
            json={"query": "滑动窗口", "mode": "demo"},
        ).json()
        assert (
            ai["status"] == "grounded"
            and ai["result"]["citations"][0]["source_kind"] == "manual_transcript"
        )
        assert c.post(f"/api/v1/jobs/{job}/retry", headers=h).status_code == 202
        drain_jobs()
        assert c.get(search, headers=h).json()[0]["chunk_id"] == saved["chunk_id"]
        after = c.get(f"/api/v1/versions/{v['id']}", headers=h).json()
        assert after["parse_status"] == "FAILED" and after["index_status"] == "PENDING"
        with SessionLocal() as db:
            assert (
                len(
                    db.scalars(
                        select(DocumentChunk).where(DocumentChunk.version_id == v["id"])
                    ).all()
                )
                == 1
            )


def test_revision_keeps_old_citations_current_search_and_withdrawal_does_not_fallback():
    with TestClient(app) as c:
        h, course, v, _ = setup(c)
        old = confirm(c, h, draft(c, h, v))
        note = c.post(
            "/api/v1/notes",
            headers=h,
            json={
                "title": "旧记录",
                "course_id": course,
                "citations": [
                    {
                        "version_id": v["id"],
                        "chunk_id": old["chunk_id"],
                        "quote": old["text"],
                    }
                ],
            },
        ).json()
        new = draft(c, h, v, "拥塞控制约束网络负载。", old["id"])
        competing = draft(c, h, v, "流量控制约束接收能力。", old["id"])
        newer = confirm(c, h, new)
        conflict = c.post(
            f"/api/v1/transcripts/{competing['id']}/confirm",
            headers=h,
            json={"revision": competing["revision"]},
        )
        assert conflict.status_code == 409
        assert (
            c.get(f"/api/v1/courses/{course}/search?q=滑动窗口", headers=h).json() == []
        )
        assert (
            c.get(f"/api/v1/courses/{course}/search?q=拥塞控制", headers=h).json()[0][
                "chunk_id"
            ]
            == newer["chunk_id"]
        )
        old_citation = c.get(f"/api/v1/notes/{note['id']}/citations", headers=h).json()[
            0
        ]
        assert (
            old_citation["quote"] == old["text"]
            and old_citation["availability"] == "active"
        )
        rows = c.get(f"/api/v1/versions/{v['id']}/chunks", headers=h).json()
        assert (
            next(row for row in rows if row["id"] == old["chunk_id"])[
                "transcript_status"
            ]
            == "SUPERSEDED"
        )
        withdrawn = c.post(
            f"/api/v1/transcripts/{newer['id']}/withdraw",
            headers=h,
            json={"revision": newer["revision"]},
        )
        assert withdrawn.status_code == 200
        assert (
            c.get(f"/api/v1/courses/{course}/search?q=拥塞控制", headers=h).json() == []
        )
        assert (
            c.get(f"/api/v1/courses/{course}/search?q=滑动窗口", headers=h).json() == []
        )
        old_record = next(
            row
            for row in c.get(
                f"/api/v1/versions/{v['id']}/transcripts", headers=h
            ).json()
            if row["id"] == old["id"]
        )
        assert (
            c.post(
                f"/api/v1/transcripts/{old['id']}/withdraw",
                headers=h,
                json={"revision": old_record["revision"]},
            ).status_code
            == 200
        )
        assert (
            c.get(f"/api/v1/notes/{note['id']}/citations", headers=h).json()[0][
                "availability"
            ]
            == "unavailable"
        )
        assert (
            c.post(
                f"/api/v1/notes/{note['id']}/citations",
                headers=h,
                json={
                    "version_id": v["id"],
                    "chunk_id": old["chunk_id"],
                    "quote": old["text"],
                },
            ).status_code
            == 422
        )
        with SessionLocal() as db:
            assert db.get(ManualTranscript, competing["id"]).status == "DRAFT"


def test_transcript_conflicts_validation_and_cross_user_source_deletion():
    with TestClient(app) as c:
        h, course, v, _ = setup(c)
        stranger, _, other, _ = setup(c)
        t = draft(c, h, v)
        url = f"/api/v1/transcripts/{t['id']}"
        edited = c.patch(
            url,
            headers=h,
            json={"revision": t["revision"], "text": "修订后的窗口文字。"},
        )
        assert edited.status_code == 200
        stale = c.patch(
            url, headers=h, json={"revision": t["revision"], "text": "不能覆盖"}
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["details"]["server_text"] == "修订后的窗口文字。"
        for suffix in ("/confirm", "/withdraw"):
            assert (
                c.post(
                    url + suffix,
                    headers=stranger,
                    json={"revision": edited.json()["revision"]},
                ).status_code
                == 404
            )
        assert (
            c.patch(
                url, headers=stranger, json={"revision": 1, "text": "其他用户"}
            ).status_code
            == 404
        )
        assert (
            c.get(
                f"/api/v1/versions/{v['id']}/transcripts", headers=stranger
            ).status_code
            == 404
        )
        for payload in (
            {"page": 3, "text": "越界"},
            {"page": 0, "text": "零页"},
            {"page": True, "text": "布尔"},
            {"page": 1, "text": " "},
            {"page": 1, "text": "x" * 20001},
        ):
            assert (
                c.post(
                    f"/api/v1/versions/{v['id']}/transcripts", headers=h, json=payload
                ).status_code
                == 422
            )
        assert (
            c.post(
                f"/api/v1/versions/{other['id']}/transcripts",
                headers=h,
                json={"page": 1, "text": "越权"},
            ).status_code
            == 404
        )
        saved = confirm(c, h, edited.json())
        assert (
            c.patch(
                url,
                headers=h,
                json={"revision": saved["revision"], "text": "不能修改确认正文"},
            ).status_code
            == 409
        )
        assert (
            c.delete(f"/api/v1/documents/{v['document_id']}", headers=h).status_code
            == 204
        )
        assert (
            c.get(f"/api/v1/versions/{v['id']}/transcripts", headers=h).status_code
            == 404
        )
        assert (
            c.post(
                url + "/withdraw", headers=h, json={"revision": saved["revision"]}
            ).status_code
            == 404
        )
        assert c.get(f"/api/v1/courses/{course}/search?q=窗口", headers=h).json() == []


def test_successful_parser_recovery_keeps_manual_chunk_and_adds_extracted_text(
    monkeypatch,
):
    from app.workers import materials

    def interrupted(_source):
        raise TimeoutError("injected initial parse interruption")

    with TestClient(app) as client:
        with monkeypatch.context() as patch:
            patch.setattr(materials, "parse_isolated", interrupted)
            owner, course, version, job = setup(
                client, Path("fixtures/preview_demo.pdf").read_bytes()
            )
        source = confirm(client, owner, draft(client, owner, version))
        assert (
            client.post(f"/api/v1/jobs/{job}/retry", headers=owner).status_code == 202
        )
        drain_jobs()  # Actual pypdf parser now reads the unchanged fixture.
        chunks = client.get(
            f"/api/v1/versions/{version['id']}/chunks", headers=owner
        ).json()
        assert len([row for row in chunks if row["source_kind"] == "extracted"]) == 2
        assert (
            next(row for row in chunks if row["source_kind"] == "manual_transcript")[
                "id"
            ]
            == source["chunk_id"]
        )
        assert client.get(
            f"/api/v1/courses/{course}/search?q=Hustudy", headers=owner
        ).json()
