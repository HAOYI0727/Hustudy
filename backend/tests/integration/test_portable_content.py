from copy import deepcopy
import json
from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func

from app.main import app
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.models import (
    Course,
    Note,
    NoteFolder,
    ExamBlueprint,
    ExamPaper,
    ExamAttempt,
    Mistake,
    ReviewTask,
)
from app.services import portable_content as portable
from app.workers.materials import drain_jobs
from tests.m1.test_materialhub import context, upload


def owner(client, headers):
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


def create_note(client, headers, course, title, content, folder=None):
    response = client.post(
        "/api/v1/notes",
        headers=headers,
        json={
            "course_id": course,
            "title": title,
            "content": content,
            "folder_id": folder,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def materialize(manifest, descriptors, user, course):
    sources = {item["id"]: item["source"] for item in descriptors}
    root = Path(get_settings().storage_root) / user / course
    root.mkdir(parents=True, exist_ok=True)
    paths = {}
    for item in manifest["files"]:
        target = root / (str(uuid4()) + item["suffix"])
        shutil.copyfile(sources[item["id"]], target)
        paths["file:" + item["id"]] = target
    return paths


def test_course_subset_keeps_unfiled_and_empty_folders_without_hidden_notes():
    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        with SessionLocal() as db:
            folder = NoteFolder(user_id=user, course_id=course, name="容器")
            empty = NoteFolder(user_id=user, course_id=course, name="空目录")
            db.add_all([folder, empty])
            db.commit()
            folder_id, empty_id = folder.id, empty.id
        b = create_note(client, headers, course, "B取消选择", "B正文", folder_id)
        a = create_note(
            client,
            headers,
            course,
            "A保留",
            f"[[note:{b['id']}|B标签]]\n普通UUID文字：{b['id']}",
            folder_id,
        )
        c = create_note(client, headers, course, "C未归档", "C正文")
        with SessionLocal() as db:
            manifest, files = portable.snapshot(db, user, course)
        selected, warnings = portable.select_content(
            manifest, {"notes": [a["id"], c["id"]], "folders": [folder_id, empty_id]}
        )
        assert {n["title"] for n in selected["tables"]["notes"]} == {"A保留", "C未归档"}
        assert selected["tables"]["note_links"] == []
        assert "[[note:" not in next(
            n["content"] for n in selected["tables"]["notes"] if n["id"] == a["id"]
        )
        assert any("文字标记" in w for w in warnings)
        new_course = str(uuid4())
        with SessionLocal() as db:
            result = portable.import_content(
                db, user, selected, {}, target_course_id=new_course, title="导入副本"
            )
            db.commit()
            notes = db.scalars(select(Note).where(Note.course_id == new_course)).all()
            assert {n.title for n in notes} == {"A保留", "C未归档"}
            assert not {n.id for n in notes}.intersection({a["id"], b["id"], c["id"]})
            assert next(n for n in notes if n.title == "C未归档").folder_id is None
            assert b["id"] in next(n for n in notes if n.title == "A保留").content
            assert result["course_id"] == new_course
            assert db.get(Course, course).name != "导入副本"


def test_folder_import_into_nonempty_course_renames_root_and_rewrites_links():
    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        with SessionLocal() as db:
            folder = NoteFolder(user_id=user, course_id=course, name="导入笔记")
            db.add(folder)
            db.commit()
            original_folder = folder.id
        a = create_note(client, headers, course, "A", "原文", original_folder)
        b = create_note(
            client, headers, course, "B", f"[[note:{a['id']}|A]]", original_folder
        )
        with SessionLocal() as db:
            package, _ = portable.snapshot(db, user, course, "folder")
            for _ in range(2):
                before = set(
                    db.scalars(select(Note.id).where(Note.course_id == course))
                )
                result = portable.import_content(
                    db, user, package, {}, target_course_id=course, title="导入笔记"
                )
                assert "courses" not in result["counts"]
                db.commit()
                rows = db.scalars(
                    select(Note).where(Note.course_id == course, Note.id.not_in(before))
                ).all()
                by_title = {n.title: n for n in rows}
                assert f"[[note:{by_title['A'].id}|A]]" == by_title["B"].content
                assert a["id"] not in by_title["B"].content
            names = set(
                db.scalars(
                    select(NoteFolder.name).where(NoteFolder.course_id == course)
                )
            )
            assert names == {"导入笔记", "导入笔记 (导入2)", "导入笔记 (导入3)"}
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(Note)
                    .where(Note.course_id == course)
                )
                == 6
            )
            assert db.get(Note, b["id"]).content == b["content"]


def test_note_citation_selection_closes_material_dependencies_and_remaps_source():
    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        job = upload(client, headers, course, "# 来源\n\n窗口机制限制发送速率。")
        drain_jobs()
        chunk = client.get(
            f"/api/v1/versions/{job['resource_id']}/chunks", headers=headers
        ).json()[0]
        response = client.post(
            "/api/v1/notes",
            headers=headers,
            json={
                "course_id": course,
                "title": "来源摘记",
                "content": "摘记",
                "citations": [
                    {
                        "version_id": chunk["version_id"],
                        "chunk_id": chunk["id"],
                        "quote": "窗口机制限制发送速率。",
                    }
                ],
            },
        )
        assert response.status_code == 201, response.text
        with SessionLocal() as db:
            package, files = portable.snapshot(db, user, course)
        selected, warnings = portable.select_content(
            package, {"notes": [response.json()["id"]]}
        )
        assert (
            len(selected["tables"]["documents"])
            == len(selected["tables"]["document_versions"])
            == 1
        )
        assert any("依赖" in w for w in warnings)
        destination = str(uuid4())
        paths = materialize(selected, files, user, destination)
        with SessionLocal() as db:
            portable.import_content(
                db, user, selected, paths, target_course_id=destination
            )
            db.commit()
            from app.models import Citation, DocumentVersion

            note = db.scalar(select(Note).where(Note.course_id == destination))
            citation = db.scalar(select(Citation).where(Citation.note_id == note.id))
            assert (
                citation.version_id != chunk["version_id"]
                and citation.chunk_id != chunk["id"]
            )
            version = db.get(DocumentVersion, citation.version_id)
            assert (
                version.sha256 == selected["tables"]["document_versions"][0]["sha256"]
            )
        with SessionLocal() as db:
            folder_package, _ = portable.snapshot(db, user, course, "folder")
        assert folder_package["tables"]["citations"] == []
        assert folder_package["tables"]["documents"] == []


def test_exam_inline_ids_and_answer_grading_keys_are_remapped():
    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        question_id = str(uuid4())
        question = {"id": question_id, "stem": "1+1?", "answer": "2"}
        with SessionLocal() as db:
            blueprint = ExamBlueprint(
                user_id=user, course_id=course, name="练习蓝图", config_json="{}"
            )
            db.add(blueprint)
            db.flush()
            paper = ExamPaper(
                user_id=user,
                course_id=course,
                blueprint_id=blueprint.id,
                title="已做练习",
                status="READY",
                questions_json=json.dumps([question]),
            )
            db.add(paper)
            db.flush()
            attempt = ExamAttempt(
                user_id=user,
                paper_id=paper.id,
                status="SUBMITTED",
                answers_json=json.dumps({question_id: "3"}),
                grading_json=json.dumps({question_id: {"score": 0}}),
                snapshot_json=json.dumps(
                    {"questions": [question], "duration_minutes": 30}
                ),
            )
            db.add(attempt)
            db.flush()
            mistake = Mistake(
                user_id=user,
                attempt_id=attempt.id,
                question_id=question_id,
                detail_json=json.dumps(
                    {"question": question, "redoes": {}, "relapses": {}}
                ),
            )
            db.add(mistake)
            db.flush()
            db.add(
                ReviewTask(
                    user_id=user,
                    mistake_id=mistake.id,
                    title="复习",
                    due_date="2026-10-30",
                )
            )
            db.commit()
            paper_id, attempt_id = paper.id, attempt.id
            package, files = portable.snapshot(db, user, course)
        selected, _ = portable.select_content(package, {"exam_papers": [paper_id]})
        destination = str(uuid4())
        with SessionLocal() as db:
            portable.import_content(
                db, user, selected, {}, target_course_id=destination
            )
            db.commit()
            new_paper = db.scalar(
                select(ExamPaper).where(ExamPaper.course_id == destination)
            )
            new_attempt = db.scalar(
                select(ExamAttempt).where(ExamAttempt.paper_id == new_paper.id)
            )
            new_question = json.loads(new_paper.questions_json)[0]["id"]
            assert new_question != question_id and new_attempt.id != attempt_id
            assert set(json.loads(new_attempt.answers_json)) == {new_question}
            assert set(json.loads(new_attempt.grading_json)) == {new_question}
            assert (
                json.loads(new_attempt.snapshot_json)["questions"][0]["id"]
                == new_question
            )
            new_mistake = db.scalar(
                select(Mistake).where(Mistake.attempt_id == new_attempt.id)
            )
            assert new_mistake.question_id == new_question
            assert db.scalar(
                select(ReviewTask).where(ReviewTask.mistake_id == new_mistake.id)
            )


@pytest.mark.parametrize(
    "mutation",
    [
        "owner",
        "course",
        "deleted",
        "unknown_table",
        "unknown_column",
        "control",
        "duplicate_id",
    ],
)
def test_preview_rejects_invalid_scope_and_unknown_structure(mutation):
    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        create_note(client, headers, course, "验证", "正文")
        with SessionLocal() as db:
            package, _ = portable.snapshot(db, user, course)
        bad = deepcopy(package)
        note = bad["tables"]["notes"][0]
        if mutation == "owner":
            note["user_id"] = str(uuid4())
        elif mutation == "course":
            note["course_id"] = str(uuid4())
        elif mutation == "deleted":
            note["deleted"] = True
        elif mutation == "unknown_table":
            bad["tables"]["unknown"] = []
        elif mutation == "unknown_column":
            note["unknown"] = "no"
        elif mutation == "control":
            bad["tables"]["processing_jobs"] = [{"id": str(uuid4())}]
        elif mutation == "duplicate_id":
            note["id"] = course
        with pytest.raises((ValueError, KeyError)):
            portable.validate_manifest(bad)


def test_selection_does_not_accept_unknown_or_empty_ids():
    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        create_note(client, headers, course, "选择", "正文")
        with SessionLocal() as db:
            package, _ = portable.snapshot(db, user, course)
        for selection in ({}, {"unknown": []}, {"notes": [str(uuid4())]}):
            with pytest.raises(ValueError):
                portable.select_content(package, selection)


def test_caller_rollback_keeps_existing_course_and_notes_unchanged():
    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        note = create_note(client, headers, course, "不能更改", "原文")
        with SessionLocal() as db:
            package, _ = portable.snapshot(db, user, course, "folder")
        with SessionLocal() as db:
            portable.import_content(
                db, user, package, {}, target_course_id=course, title="未提交"
            )
            db.rollback()
        with SessionLocal() as db:
            assert db.get(Note, note["id"]).content == "原文"
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(Note)
                    .where(Note.course_id == course)
                )
                == 1
            )
            assert not db.scalar(
                select(NoteFolder.id).where(NoteFolder.course_id == course)
            )


def test_folder_scope_only_contains_images_referenced_by_scoped_notes():
    from tests.m1.test_preview_assets import png

    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        with SessionLocal() as db:
            folder = NoteFolder(user_id=user, course_id=course, name="选定范围")
            db.add(folder)
            db.commit()
            folder_id = folder.id
        assets = []
        for index in range(3):
            response = client.post(
                f"/api/v1/courses/{course}/assets",
                headers=headers,
                files={"file": (f"图{index}.png", png(), "image/png")},
            )
            assert response.status_code == 201, response.text
            assets.append(response.json()["id"])
        create_note(
            client, headers, course, "范围内", f"![[asset:{assets[0]}|图片]]", folder_id
        )
        create_note(client, headers, course, "范围外", f"![[asset:{assets[1]}|图片]]")
        with SessionLocal() as db:
            branch, files = portable.snapshot(db, user, course, "folder", folder_id)
            all_notes, _ = portable.snapshot(db, user, course, "folder")
            full_course, _ = portable.snapshot(db, user, course)
        assert {row["id"] for row in branch["tables"]["assets"]} == {assets[0]}
        assert len(files) == 1
        assert portable.catalog(branch)["title"] == "选定范围"
        assert {row["id"] for row in all_notes["tables"]["assets"]} == set(assets[:2])
        assert {row["id"] for row in full_course["tables"]["assets"]} == set(assets)


@pytest.mark.parametrize("same_course", [True, False])
def test_course_merge_is_additive_and_preserves_existing_course_metadata(same_course):
    with TestClient(app) as client:
        headers, source = context(client)
        user = owner(client, headers)
        target = (
            source
            if same_course
            else client.post(
                "/api/v1/courses", headers=headers, json={"name": "目标课程"}
            ).json()["id"]
        )
        with SessionLocal() as db:
            folder = NoteFolder(user_id=user, course_id=source, name="章节")
            db.add(folder)
            if not same_course:
                db.add(NoteFolder(user_id=user, course_id=target, name="章节"))
            course = db.get(Course, target)
            course.description, course.category = "原始简介", "原始分类"
            course.tags, course.revision = ["不覆盖"], 7
            db.commit()
            folder_id = folder.id
            metadata = {
                key: getattr(course, key)
                for key in (
                    "name",
                    "description",
                    "category",
                    "tags",
                    "revision",
                    "updated_at",
                )
            }
        a = create_note(client, headers, source, "同名", "甲", folder_id)
        b = create_note(client, headers, source, "未归档", f"[[note:{a['id']}|甲]]")
        with SessionLocal() as db:
            package, _ = portable.snapshot(db, user, source)
            before = set(db.scalars(select(Note.id).where(Note.course_id == target)))
            portable.validate_target(db, user, package, target)
            assert (
                set(db.scalars(select(Note.id).where(Note.course_id == target)))
                == before
            )
            result = portable.import_content(
                db, user, package, {}, target_course_id=target
            )
            db.commit()
            course = db.get(Course, target)
            assert {key: getattr(course, key) for key in metadata} == metadata
            added = db.scalars(
                select(Note).where(Note.course_id == target, Note.id.not_in(before))
            ).all()
            by_title = {note.title: note for note in added}
            assert len(added) == 2 and not {note.id for note in added} & {
                a["id"],
                b["id"],
            }
            assert by_title["未归档"].content == f"[[note:{by_title['同名'].id}|甲]]"
            assert by_title["未归档"].folder_id is None
            assert {
                row.name
                for row in db.scalars(
                    select(NoteFolder).where(NoteFolder.course_id == target)
                )
            } == {"章节", "章节 (导入2)"}
            assert result["counts"]["notes"] == 2 and "courses" not in result["counts"]
            assert db.get(Note, a["id"]).content == "甲"


def test_merge_target_preflight_rejects_foreign_course_and_parent_or_rename():
    from fastapi import HTTPException

    with TestClient(app) as client:
        headers, course = context(client)
        _, foreign = context(client)
        user = owner(client, headers)
        create_note(client, headers, course, "来源", "原文")
        with SessionLocal() as db:
            package, _ = portable.snapshot(db, user, course)
            with pytest.raises(HTTPException) as denied:
                portable.validate_target(db, user, package, foreign)
            assert denied.value.status_code == 404
            with pytest.raises(ValueError, match="根目录"):
                portable.validate_target(db, user, package, course, str(uuid4()))
            with pytest.raises(ValueError, match="名称"):
                portable.validate_target(db, user, package, course, title="意外覆盖")


def test_folder_preflight_checks_combined_depth_without_business_writes():
    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        with SessionLocal() as db:
            parent = None
            for level in range(6):
                folder = NoteFolder(
                    user_id=user, course_id=course, name=f"层{level}", parent_id=parent
                )
                db.add(folder)
                db.flush()
                parent = folder.id
            db.commit()
            package, _ = portable.snapshot(db, user, course, "folder")
            with pytest.raises(ValueError, match="6级"):
                portable.validate_target(db, user, package, course, parent)
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(NoteFolder)
                    .where(NoteFolder.course_id == course)
                )
                == 6
            )


def test_snapshot_rejects_oversized_source_before_reading_or_hashing(monkeypatch):
    from app.models import Document

    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        upload(client, headers, course, "合法原件")
        drain_jobs()
        with SessionLocal() as db:
            source = db.scalar(select(Document).where(Document.course_id == course))
            with Path(source.storage_path).open("r+b") as stream:
                stream.truncate(30 * 1024 * 1024 + 1)
            monkeypatch.setattr(
                portable, "_file_hash", lambda *_: pytest.fail("超大文件不应读取哈希")
            )
            with pytest.raises(ValueError, match="单文件"):
                portable.snapshot(db, user, course)


def test_manifest_rejects_mime_suffix_mismatch():
    with TestClient(app) as client:
        headers, course = context(client)
        user = owner(client, headers)
        upload(client, headers, course, "合法原件")
        drain_jobs()
        with SessionLocal() as db:
            manifest, _ = portable.snapshot(db, user, course)
        manifest["tables"]["documents"][0]["mime_type"] = "application/pdf"
        with pytest.raises(ValueError, match="MIME"):
            portable.validate_manifest(manifest)
