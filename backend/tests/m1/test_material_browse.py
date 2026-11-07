from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import Document, DocumentVersion, ProcessingJob
from app.models.base import utc_now
from tests.m1.test_materialhub import context, upload
from app.workers.materials import drain_jobs


def seed(db, owner, course, count):
    stamp = utc_now()
    for index in range(count):
        doc = Document(
            user_id=owner,
            course_id=course,
            name=f"资料{index:03}",
            category="课程",
            tags=["标签", "100%_字面"] if index == 0 else ["标签"],
            original_filename=f"lesson{index}.md",
            mime_type="text/markdown",
            size_bytes=index + 1,
            sha256=str(index),
            storage_path="unused",
            created_at=stamp,
            updated_at=stamp,
        )
        db.add(doc)
        db.flush()
        version = DocumentVersion(
            user_id=owner,
            document_id=doc.id,
            version_no=1,
            source_path="unused",
            original_filename=doc.original_filename,
            size_bytes=index + 1,
            parse_status="SUCCEEDED",
            index_status="SUCCEEDED",
        )
        db.add(version)
        db.flush()
        db.add(
            ProcessingJob(
                user_id=owner,
                resource_id=version.id,
                type="PARSE",
                status="SUCCEEDED",
                created_at=stamp,
            )
        )
    db.commit()


def test_more_than_100_jobs_and_documents_stable_pages_and_filters():
    with TestClient(app) as client:
        headers, course = context(client)
        owner = client.get("/api/v1/auth/me", headers=headers).json()["id"]
        with SessionLocal() as db:
            seed(db, owner, course, 105)
        docs = f"/api/v1/courses/{course}/documents/page"
        jobs = f"/api/v1/courses/{course}/jobs/page"
        first = client.get(
            docs, headers=headers, params={"limit": 100, "sort": "name"}
        ).json()
        last = client.get(
            docs, headers=headers, params={"limit": 100, "sort": "name", "offset": 100}
        ).json()
        assert first["total"] == last["total"] == 105
        assert first["stats"] == {"total": 105, "ready": 105, "processing": 0}
        assert len(first["items"]) == 100 and len(last["items"]) == 5
        assert len({row["id"] for row in first["items"] + last["items"]}) == 105
        assert (
            first["items"]
            == client.get(
                docs, headers=headers, params={"limit": 100, "sort": "name"}
            ).json()["items"]
        )
        assert (
            client.get(docs, headers=headers, params={"q": "100%_"}).json()["total"]
            == 1
        )
        assert (
            client.get(docs, headers=headers, params={"tag": "标"}).json()["total"] == 0
        )
        assert (
            client.get(
                docs,
                headers=headers,
                params={"tag": "标签", "category": "课程", "state": "ready"},
            ).json()["total"]
            == 105
        )
        assert (
            client.get(docs, headers=headers, params={"offset": 999}).json()["items"]
            == []
        )
        ids = []
        for offset in (0, 100):
            page = client.get(
                jobs, headers=headers, params={"limit": 100, "offset": offset}
            ).json()
            assert page["total"] == 105
            ids += [item["id"] for item in page["items"]]
        assert len(ids) == len(set(ids)) == 105
        assert (
            client.get(jobs, headers=headers, params={"status": "failed"}).json()[
                "total"
            ]
            == 0
        )


def test_latest_version_status_pending_counts_deleted_and_cross_user():
    with TestClient(app) as client:
        headers, course = context(client)
        foreign, foreign_course = context(client)
        original = upload(client, headers, course, "# 旧版本\n\n可以检索。")
        drain_jobs()
        doc = client.get(f"/api/v1/courses/{course}/documents", headers=headers).json()[
            0
        ]
        updated = client.post(
            f"/api/v1/documents/{doc['id']}/versions",
            headers=headers,
            files={"file": ("latest.md", b"# newer version")},
        )
        assert updated.status_code == 202
        docs = f"/api/v1/courses/{course}/documents/page"
        jobs = f"/api/v1/courses/{course}/jobs/page"
        ready = client.get(docs, headers=headers, params={"state": "ready"}).json()
        assert ready["total"] == ready["stats"]["ready"] == 0
        processing = client.get(
            docs, headers=headers, params={"state": "processing"}
        ).json()
        assert (
            processing["total"] == 1
            and processing["items"][0]["latest_version_no"] == 2
        )
        queue = client.get(
            jobs, headers=headers, params={"status": "succeeded", "offset": 1000}
        ).json()
        assert queue["items"] == [] and queue["pending_count"] == 1
        for path in [docs, jobs]:
            assert client.get(path, headers=foreign).status_code == 404
            assert (
                client.get(path, headers=headers, params={"limit": 101}).status_code
                == 422
            )
            assert (
                client.get(path, headers=headers, params={"offset": -1}).status_code
                == 422
            )
        assert (
            client.get(docs, headers=headers, params={"state": "invented"}).status_code
            == 422
        )
        assert (
            client.get(
                jobs, headers=headers, params={"kind": "AI_ANALYSIS"}
            ).status_code
            == 422
        )
        assert (
            client.delete(f"/api/v1/documents/{doc['id']}", headers=headers).status_code
            == 204
        )
        for path in [docs, jobs]:
            assert client.get(path, headers=headers).json()["total"] == 0
        assert (
            client.get(
                f"/api/v1/courses/{foreign_course}/documents/page", headers=foreign
            ).json()["total"]
            == 0
        )
        with SessionLocal() as db:
            old = db.get(DocumentVersion, original["resource_id"])
            assert old.version_no == 1
            assert (
                db.scalar(
                    select(ProcessingJob).where(ProcessingJob.resource_id == old.id)
                ).status
                == "SUCCEEDED"
            )
