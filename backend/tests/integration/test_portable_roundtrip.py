"""Exercise portable packages through real M1/M2/M3/M4 public API fixtures."""

import importlib.util
import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import (
    Asset,
    Citation,
    Document,
    DocumentChunk,
    DocumentVersion,
    ExamAttempt,
    ExamPaper,
    Mistake,
    Note,
    NoteFolder,
    PastPaper,
    PastQuestion,
    ReviewTask,
    Topic,
    Course,
)

_spec = importlib.util.spec_from_file_location(
    "portable_sample_fixture",
    Path(__file__).resolve().parents[3] / "scripts" / "generate_portable_samples.py",
)
samples = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(samples)


def catalog(client, headers, course, kind="course"):
    return samples.checked(
        client.get(
            f"/api/v1/courses/{course}/packages/catalog",
            headers=headers,
            params={"kind": kind},
        )
    )


def exported(client, headers, course, kind, selection):
    response = client.post(
        "/api/v1/packages/export",
        headers=headers,
        json={
            "course_id": course,
            "kind": kind,
            "selection": selection,
        },
    )
    assert response.status_code == 200, response.text
    return response.content


def preview(client, headers, raw):
    return samples.checked(
        client.post(
            "/api/v1/packages/preview",
            headers=headers,
            files={"file": ("验收包.zip", raw, "application/zip")},
        )
    )


def test_complete_course_copies_materials_links_practice_without_old_ids():
    with TestClient(app) as client:
        headers, data = samples.seed(client)
        source = data["course"]["id"]
        all_items = catalog(client, headers, source)
        raw = exported(
            client, headers, source, "course", samples.all_selection(all_items)
        )
        viewed = preview(client, headers, raw)
        # Preview changes no course or note business state.
        assert len(samples.checked(client.get("/api/v1/courses", headers=headers))) == 1
        body = {
            "preview_id": viewed["preview_id"],
            "request_id": str(uuid4()),
            "selection": samples.all_selection(viewed),
        }
        result = samples.checked(
            client.post("/api/v1/packages/import", headers=headers, json=body)
        )
        target = result["course_id"]
        assert target != source
        assert (
            samples.checked(
                client.post("/api/v1/packages/import", headers=headers, json=body)
            )
            == result
        )
        assert len(samples.checked(client.get("/api/v1/courses", headers=headers))) == 2
        with SessionLocal() as db:
            source_notes = db.scalars(
                select(Note).where(Note.course_id == source)
            ).all()
            target_notes = db.scalars(
                select(Note).where(Note.course_id == target)
            ).all()
            assert sorted(n.title for n in source_notes) == sorted(
                n.title for n in target_notes
            )
            assert {n.id for n in source_notes}.isdisjoint(n.id for n in target_notes)
            a = next(n for n in target_notes if n.title.startswith("A "))
            b = next(
                n for n in target_notes if n.title.startswith("B ") and n.folder_id
            )
            assert f"[[note:{b.id}|" in a.content
            assert f"[[note:{a.id}|" in b.content
            assert data["b"]["id"] not in a.content
            assert a.tags == data["a"]["tags"]
            target_assets = db.scalars(
                select(Asset).where(Asset.course_id == target)
            ).all()
            assert len(target_assets) == 2
            assert any(f"![[asset:{asset.id}|" in a.content for asset in target_assets)
            for asset in target_assets:
                assert Path(asset.storage_path).is_file()
                assert target in Path(asset.storage_path).parts
            citations = db.scalars(
                select(Citation).where(Citation.note_id == a.id)
            ).all()
            assert len(citations) == 1
            citation = citations[0]
            chunk = db.get(DocumentChunk, citation.chunk_id)
            version = db.get(DocumentVersion, citation.version_id)
            document = db.get(Document, version.document_id)
            assert chunk.version_id == version.id
            assert document.course_id == target
            assert citation.quote in chunk.text
            assert (
                Path(version.source_path)
                .read_text(encoding="utf-8")
                .startswith("# 计算机网络")
            )
            assert (
                len(
                    db.scalars(
                        select(NoteFolder).where(NoteFolder.course_id == target)
                    ).all()
                )
                == 3
            )
            papers = db.scalars(
                select(ExamPaper).where(ExamPaper.course_id == target)
            ).all()
            assert len(papers) == 1
            exam = papers[0]
            question_ids = {q["id"] for q in json.loads(exam.questions_json)}
            original = db.scalar(select(ExamPaper).where(ExamPaper.course_id == source))
            assert question_ids.isdisjoint(
                q["id"] for q in json.loads(original.questions_json)
            )
            attempt = db.scalar(
                select(ExamAttempt).where(ExamAttempt.paper_id == exam.id)
            )
            assert attempt is not None
            snapshot_ids = {
                q["id"] for q in json.loads(attempt.snapshot_json)["questions"]
            }
            assert snapshot_ids == question_ids
            assert set(json.loads(attempt.answers_json)) == question_ids
            assert set(json.loads(attempt.grading_json)) == question_ids
            mistake = db.scalar(select(Mistake).where(Mistake.attempt_id == attempt.id))
            assert mistake.question_id in question_ids
            assert json.loads(mistake.detail_json)["question"]["id"] in question_ids
            review = db.scalar(
                select(ReviewTask).where(ReviewTask.mistake_id == mistake.id)
            )
            assert review.title == "复习：TCP与UDP区别"
            assert review.due_date == "2026-11-05"
            bank = db.scalar(select(PastPaper).where(PastPaper.course_id == target))
            question = db.scalar(
                select(PastQuestion).where(PastQuestion.paper_id == bank.id)
            )
            for topic_id in json.loads(question.bank_data_json).get("topic_ids", []):
                assert db.get(Topic, topic_id).course_id == target
        response = client.get(f"/api/v1/notes/{a.id}/citations", headers=headers)
        assert response.status_code == 200
        assert response.json()[0]["availability"] == "active"
        # A second real export/import proves migrated data remains portable.
        again = exported(
            client,
            headers,
            target,
            "course",
            samples.all_selection(catalog(client, headers, target)),
        )
        assert preview(client, headers, again)["items"]


def test_selected_folder_only_copies_chosen_notes_dependency_image_and_empty_folder():
    with TestClient(app) as client:
        headers, data = samples.seed(client)
        source = data["course"]["id"]
        raw = exported(
            client,
            headers,
            source,
            "folder",
            {
                "notes": [data["a"]["id"], data["loose"]["id"]],
                "folders": [data["empty"]["id"]],
            },
        )
        p = preview(client, headers, raw)
        assert {item["id"] for item in p["items"] if item["category"] == "notes"} == {
            data["a"]["id"],
            data["loose"]["id"],
        }
        target = samples.checked(
            client.post("/api/v1/courses", headers=headers, json={"name": "已有课程"})
        )["id"]
        keep = samples.checked(
            client.post(
                "/api/v1/notes",
                headers=headers,
                json={
                    "course_id": target,
                    "title": data["a"]["title"],
                    "content": "不能覆盖的原笔记",
                },
            )
        )
        request = {
            "preview_id": p["preview_id"],
            "request_id": str(uuid4()),
            "selection": samples.all_selection(p),
            "target_course_id": target,
        }
        imported = samples.checked(
            client.post("/api/v1/packages/import", headers=headers, json=request)
        )
        assert imported["note_count"] == 2
        with SessionLocal() as db:
            notes = db.scalars(select(Note).where(Note.course_id == target)).all()
            assert len(notes) == 3
            a = next(
                n for n in notes if n.title.startswith("A ") and n.id != keep["id"]
            )
            loose = next(n for n in notes if n.title.startswith("C "))
            assert loose.folder_id is None
            assert "[[note:" not in a.content
            assert data["b"]["id"] not in a.content
            assert "查看UDP速记" in a.content
            assert db.get(Note, keep["id"]).content == "不能覆盖的原笔记"
            assert (
                len(db.scalars(select(Asset).where(Asset.course_id == target)).all())
                == 1
            )
            assert not db.scalars(
                select(Document).where(Document.course_id == target)
            ).all()
            assert not db.scalars(
                select(Citation).where(Citation.note_id == a.id)
            ).all()
            names = [
                n.name
                for n in db.scalars(
                    select(NoteFolder).where(NoteFolder.course_id == target)
                )
            ]
            assert "空目录（应保留）" in names
        # A deliberate second import creates a new copy without same-name failure.
        request["request_id"] = str(uuid4())
        repeated = samples.checked(
            client.post("/api/v1/packages/import", headers=headers, json=request)
        )
        assert repeated["note_count"] == 2
        assert (
            len(
                samples.checked(
                    client.get(f"/api/v1/notes?course_id={target}", headers=headers)
                )
            )
            == 5
        )


def test_course_merge_preserves_destination_and_can_merge_back_into_source():
    with TestClient(app) as client:
        headers, data = samples.seed(client)
        source = data["course"]["id"]
        raw = exported(
            client,
            headers,
            source,
            "course",
            samples.all_selection(catalog(client, headers, source)),
        )
        p = preview(client, headers, raw)
        destination = samples.checked(
            client.post(
                "/api/v1/courses",
                headers=headers,
                json={
                    "name": "保留的目标课程名称",
                    "description": "原简介不覆盖",
                    "category": "原分类",
                    "tags": ["原标签"],
                },
            )
        )
        target = destination["id"]
        samples.checked(
            client.post(
                "/api/v1/note-folders",
                headers=headers,
                json={"course_id": target, "name": data["root"]["name"]},
            )
        )
        old_note = samples.checked(
            client.post(
                "/api/v1/notes",
                headers=headers,
                json={
                    "course_id": target,
                    "title": data["a"]["title"],
                    "content": "原笔记保持不变",
                },
            )
        )
        payload = {
            "preview_id": p["preview_id"],
            "request_id": str(uuid4()),
            "selection": samples.all_selection(p),
            "target_course_id": target,
        }
        merged = samples.checked(
            client.post("/api/v1/packages/import", headers=headers, json=payload)
        )
        assert merged["course_id"] == target
        assert merged["counts"].get("courses", 0) == 0
        assert (
            samples.checked(
                client.post("/api/v1/packages/import", headers=headers, json=payload)
            )
            == merged
        )
        with SessionLocal() as db:
            course = db.get(Course, target)
            assert (
                course.name,
                course.description,
                course.category,
                course.tags,
                course.revision,
            ) == (
                destination["name"],
                destination["description"],
                destination["category"],
                destination["tags"],
                destination["revision"],
            )
            assert db.get(Note, old_note["id"]).content == "原笔记保持不变"
            assert (
                len(db.scalars(select(Note).where(Note.course_id == target)).all()) == 5
            )
            folders = db.scalars(
                select(NoteFolder).where(NoteFolder.course_id == target)
            ).all()
            assert len(folders) == 4
            assert any("导入2" in row.name for row in folders)
            assert (
                len(
                    db.scalars(
                        select(Document).where(Document.course_id == target)
                    ).all()
                )
                == 1
            )
            assert (
                len(
                    db.scalars(
                        select(ExamPaper).where(ExamPaper.course_id == target)
                    ).all()
                )
                == 1
            )
        payload = payload | {"request_id": str(uuid4()), "target_course_id": source}
        self_merged = samples.checked(
            client.post("/api/v1/packages/import", headers=headers, json=payload)
        )
        assert self_merged["course_id"] == source
        assert (
            len(
                samples.checked(
                    client.get(f"/api/v1/notes?course_id={source}", headers=headers)
                )
            )
            == 8
        )
        original = samples.checked(
            client.get(f"/api/v1/notes/{data['a']['id']}", headers=headers)
        )
        assert original["content"] == data["a"]["content"]
