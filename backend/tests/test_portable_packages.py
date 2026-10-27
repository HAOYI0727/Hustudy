"""ZIP boundaries and reliable confirmation use disposable accounts and storage."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import stat
import struct
from uuid import uuid4
import warnings
import zipfile

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.main import app
from app.models import Course, Note, PackageImport, PackagePreview
from app.models.base import utc_now
from app.services import portable_packages as service
from test_materialhub import context
from test_preview_assets import png


def all_selection(catalog):
    result = {}
    for item in catalog["items"]:
        result.setdefault(item["category"], []).append(item["id"])
    return result


def checked(response, expected=200):
    assert response.status_code == expected, response.text
    return response.json()


@pytest.fixture
def package():
    with TestClient(app) as client:
        headers, course = context(client)
        asset = checked(
            client.post(
                f"/api/v1/courses/{course}/assets",
                headers=headers,
                files={"file": ("测试图片.png", png(), "image/png")},
            ),
            201,
        )
        note = checked(
            client.post(
                "/api/v1/notes",
                headers=headers,
                json={
                    "course_id": course,
                    "title": "可移植笔记",
                    "content": f"# 正文\n![[asset:{asset['id']}|测试图片]]",
                },
            ),
            201,
        )
        catalog = checked(
            client.get(f"/api/v1/courses/{course}/packages/catalog", headers=headers)
        )
        payload = {
            "course_id": course,
            "kind": "course",
            "selection": all_selection(catalog),
        }
        response = client.post("/api/v1/packages/export", headers=headers, json=payload)
        assert response.status_code == 200, response.text
        assert "filename*=utf-8''" in response.headers["content-disposition"]
        raw = response.content
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            members = {name: archive.read(name) for name in archive.namelist()}
        yield client, headers, course, note, raw, manifest, members


def preview(client, headers, raw):
    return client.post(
        "/api/v1/packages/preview",
        headers=headers,
        files={"file": ("测试包.zip", raw, "application/zip")},
    )


def request_for(viewed):
    return {
        "preview_id": viewed["preview_id"],
        "request_id": str(uuid4()),
        "selection": all_selection(viewed),
    }


def repack(members, *, method=zipfile.ZIP_STORED, extra=()):
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w", compression=method) as archive:
            for key, value in [*members.items(), *extra]:
                archive.writestr(key, value)
    return output.getvalue()


def account_state(client, headers):
    courses = checked(client.get("/api/v1/courses", headers=headers))
    return sorted((row["id"], row["name"]) for row in courses)


def test_preview_is_private_metadata_only_and_explicit_selection_does_not_write(
    package,
):
    client, headers, course, note, raw, _manifest, _members = package
    before = account_state(client, headers)
    viewed = checked(preview(client, headers, raw))
    assert account_state(client, headers) == before
    assert "content" not in viewed["items"][0]
    narrowed = checked(
        client.post(
            "/api/v1/packages/selection-preview",
            headers=headers,
            json={
                "preview_id": viewed["preview_id"],
                "selection": {"notes": [note["id"]]},
            },
        )
    )
    assert narrowed["selection"]["notes"] == [note["id"]]
    assert len(narrowed["selection"]["assets"]) == 1
    assert narrowed["warnings"]
    assert account_state(client, headers) == before
    stranger, _ = context(client)
    for response in (
        client.get(f"/api/v1/courses/{course}/packages/catalog", headers=stranger),
        client.post(
            "/api/v1/packages/selection-preview",
            headers=stranger,
            json={
                "preview_id": viewed["preview_id"],
                "selection": all_selection(viewed),
            },
        ),
        client.post(
            "/api/v1/packages/import", headers=stranger, json=request_for(viewed)
        ),
        client.delete(
            f"/api/v1/packages/previews/{viewed['preview_id']}", headers=stranger
        ),
    ):
        assert response.status_code == 404, response.text
    assert checked(client.get("/api/v1/packages/previews", headers=stranger)) == []
    listing = checked(client.get("/api/v1/packages/previews", headers=headers))
    assert listing[0]["id"] == viewed["preview_id"]
    assert set(listing[0]) == {"id", "created_at", "expires_at", "sha256", "size_bytes"}
    assert client.get(f"/api/v1/courses/{course}/packages/catalog").status_code == 401


@pytest.mark.parametrize(
    "mode",
    [
        "traversal",
        "absolute",
        "backslash",
        "drive",
        "duplicate",
        "case_duplicate",
        "unicode_duplicate",
        "directory",
        "symlink",
        "extra",
        "ratio",
        "bad_hash",
        "unknown",
        "missing",
        "bad_json",
        "bad_image",
        "corrupt_crc",
        "corrupt_deflate",
        "foreign_owner",
        "path_reference",
    ],
)
def test_rejects_unsafe_or_corrupt_packages_without_business_or_file_writes(
    package, mode
):
    client, headers, _course, _note, raw, manifest, members = package
    before = account_state(client, headers)
    user = checked(client.get("/api/v1/auth/me", headers=headers))["id"]
    root = service.storage().root / user
    existing = {path for path in root.rglob("*") if path.is_file()}
    extra = []
    if mode in {"traversal", "absolute", "backslash", "drive"}:
        extra = [
            (
                {
                    "traversal": "../outside.txt",
                    "absolute": "/outside.txt",
                    "backslash": "notes\\outside.txt",
                    "drive": "C:/outside.txt",
                }[mode],
                b"reject",
            )
        ]
    elif mode in {"duplicate", "case_duplicate", "unicode_duplicate"}:
        extra = [
            (
                {
                    "duplicate": "manifest.json",
                    "case_duplicate": "MANIFEST.JSON",
                    "unicode_duplicate": "ｍanifest.json",
                }[mode],
                members["manifest.json"],
            )
        ]
    elif mode in {"directory", "symlink"}:
        info = zipfile.ZipInfo("forbidden/" if mode == "directory" else "linked.txt")
        info.create_system = 3
        info.external_attr = (
            (stat.S_IFDIR if mode == "directory" else stat.S_IFLNK) | 0o755
        ) << 16
        extra = [(info, b"../outside")]
    elif mode == "extra":
        extra = [("unlisted.txt", b"not declared")]
    elif mode == "ratio":
        extra = [("bomb.txt", b"A" * (256 * 1024))]
    elif mode == "bad_hash":
        manifest["files"][0]["sha256"] = "0" * 64
    elif mode == "unknown":
        manifest["format"] = "hustudy-package-v99"
    elif mode == "missing":
        members.pop(manifest["files"][0]["member"])
    elif mode == "bad_image":
        item = manifest["files"][0]
        fake = b"<html>not a png</html>"
        item["size_bytes"], item["sha256"] = len(fake), hashlib.sha256(fake).hexdigest()
        members[item["member"]] = fake
        asset = manifest["tables"]["assets"][0]
        asset["size_bytes"], asset["sha256"] = len(fake), item["sha256"]
    elif mode == "foreign_owner":
        manifest["tables"]["notes"][0]["user_id"] = str(uuid4())
    elif mode == "path_reference":
        manifest["tables"]["assets"][0]["storage_path"] = "C:/private.png"
    members["manifest.json"] = json.dumps(manifest, ensure_ascii=False).encode()
    if mode == "bad_json":
        members["manifest.json"] = (
            b'{"format":"hustudy-package-v1","format":"hustudy-package-v1"}'
        )
    raw = repack(
        members,
        extra=extra,
        method=zipfile.ZIP_DEFLATED
        if mode in {"ratio", "corrupt_deflate"}
        else zipfile.ZIP_STORED,
    )
    if mode in {"corrupt_crc", "corrupt_deflate"}:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.getinfo(manifest["files"][0]["member"])
            offset = info.header_offset
        data = bytearray(raw)
        name_size, extra_size = struct.unpack_from("<HH", data, offset + 26)
        if mode == "corrupt_deflate":
            data[offset + 30 + name_size + extra_size] = (
                7  # Invalid DEFLATE block type.
            )
        else:
            data[offset + 30 + name_size + extra_size] ^= 1
        raw = bytes(data)
    result = preview(client, headers, raw)
    assert result.status_code == 422, result.text
    assert account_state(client, headers) == before
    assert checked(client.get("/api/v1/packages/previews", headers=headers)) == []
    assert {path for path in root.rglob("*") if path.is_file()} == existing


@pytest.mark.parametrize(
    "budget", ["MAX_ZIP", "MAX_CONTENT", "MAX_METADATA", "MAX_MEMBERS", "SECONDS"]
)
def test_transport_and_time_budgets_are_enforced(package, monkeypatch, budget):
    client, headers, _course, _note, raw, _manifest, _members = package
    monkeypatch.setattr(service, budget, -1 if budget == "SECONDS" else 1)
    response = preview(client, headers, raw)
    assert response.status_code == 422, response.text


def test_success_receipt_survives_preview_removal_and_rejects_parameter_changes(
    package,
):
    client, headers, course, _note, raw, _manifest, _members = package
    viewed = checked(preview(client, headers, raw))
    payload = request_for(viewed)
    result = checked(
        client.post("/api/v1/packages/import", headers=headers, json=payload)
    )
    assert result["course_id"] != course and result["note_count"] == 1
    assert (
        client.delete(
            f"/api/v1/packages/previews/{viewed['preview_id']}", headers=headers
        ).status_code
        == 204
    )
    assert (
        checked(client.post("/api/v1/packages/import", headers=headers, json=payload))
        == result
    )
    assert (
        checked(
            client.get(
                f"/api/v1/packages/imports/{payload['request_id']}", headers=headers
            )
        )
        == result
    )
    changed = client.post(
        "/api/v1/packages/import", headers=headers, json=payload | {"title": "不同参数"}
    )
    assert changed.status_code == 409
    stranger, _ = context(client)
    assert (
        client.get(
            f"/api/v1/packages/imports/{payload['request_id']}", headers=stranger
        ).status_code
        == 404
    )


def test_expiry_changed_preview_and_quota_are_recoverable(package, monkeypatch):
    client, headers, _course, _note, raw, _manifest, _members = package
    first = checked(preview(client, headers, raw))
    with SessionLocal() as db:
        row = db.get(PackagePreview, first["preview_id"])
        expired_path = Path(row.artifact_path)
        row.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    assert (
        client.post(
            "/api/v1/packages/import", headers=headers, json=request_for(first)
        ).status_code
        == 410
    )
    monkeypatch.setattr(service, "MAX_PREVIEWS", 1)
    second = checked(preview(client, headers, raw))
    assert not expired_path.exists()
    assert preview(client, headers, raw).status_code == 409
    with SessionLocal() as db:
        row = db.get(PackagePreview, second["preview_id"])
        Path(row.artifact_path).write_bytes(raw + b"changed")
    assert (
        client.post(
            "/api/v1/packages/import", headers=headers, json=request_for(second)
        ).status_code
        == 422
    )
    assert (
        client.delete(
            f"/api/v1/packages/previews/{second['preview_id']}", headers=headers
        ).status_code
        == 204
    )
    assert preview(client, headers, raw).status_code == 200


@pytest.mark.parametrize("fault", ["apply", "disk", "commit"])
def test_failed_import_rolls_back_rows_files_and_receipt_then_same_request_retries(
    package, monkeypatch, fault
):
    client, headers, _course, _note, raw, _manifest, _members = package
    viewed = checked(preview(client, headers, raw))
    payload = request_for(viewed)
    before = account_state(client, headers)
    user = checked(client.get("/api/v1/auth/me", headers=headers))["id"]
    root = service.storage().root / user
    existing = {path for path in root.rglob("*") if path.is_file()}
    with monkeypatch.context() as patch:
        if fault == "apply":
            original = service.content.import_content

            def fail_apply(*args, **kwargs):
                original(*args, **kwargs)
                raise ValueError("模拟写入业务后失败")

            patch.setattr(service.content, "import_content", fail_apply)
        elif fault == "disk":

            def fail_write(*_args, **_kwargs):
                raise OSError("isolated disk failure")

            patch.setattr(service.LocalFileStorage, "write_stream", fail_write)
        else:
            original = Session.commit

            def fail_commit(db):
                if any(isinstance(value, PackageImport) for value in db.new):
                    raise ValueError("模拟提交失败")
                return original(db)

            patch.setattr(Session, "commit", fail_commit)
        failed = client.post("/api/v1/packages/import", headers=headers, json=payload)
        assert failed.status_code == 422, failed.text
    assert account_state(client, headers) == before
    assert {path for path in root.rglob("*") if path.is_file()} == existing
    assert (
        client.get(
            f"/api/v1/packages/imports/{payload['request_id']}", headers=headers
        ).status_code
        == 404
    )
    assert (
        checked(client.post("/api/v1/packages/import", headers=headers, json=payload))[
            "note_count"
        ]
        == 1
    )


def test_commit_response_error_keeps_durable_receipt_and_files(package, monkeypatch):
    client, headers, _course, _note, raw, _manifest, _members = package
    payload = request_for(checked(preview(client, headers, raw)))
    original = Session.commit

    def commit_then_fail(db):
        is_import = any(isinstance(value, PackageImport) for value in db.new)
        original(db)
        if is_import:
            raise ValueError("模拟COMMIT成功后响应丢失")

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", commit_then_fail)
        result = checked(
            client.post("/api/v1/packages/import", headers=headers, json=payload)
        )
    assert (
        checked(client.post("/api/v1/packages/import", headers=headers, json=payload))
        == result
    )
    with SessionLocal() as db:
        assert db.get(Course, result["course_id"]) is not None
        assert db.scalar(select(Note.id).where(Note.course_id == result["course_id"]))
    assert list(
        (
            service.storage().root
            / checked(client.get("/api/v1/auth/me", headers=headers))["id"]
            / result["course_id"]
        ).rglob("*.png")
    )


def test_two_concurrent_confirmations_create_one_copy(package):
    client, headers, _course, _note, raw, _manifest, _members = package
    payload = request_for(checked(preview(client, headers, raw)))

    def confirm(_):
        return client.post("/api/v1/packages/import", headers=headers, json=payload)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(confirm, range(2)))
    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    assert len(account_state(client, headers)) == 2


def test_confirmation_digest_is_stable_with_images_and_rejects_new_dependencies(
    package,
):
    client, headers, course, note, _raw, _manifest, _members = package
    query = {
        "course_id": course,
        "kind": "course",
        "selection": {"notes": [note["id"]]},
    }
    before = checked(
        client.post("/api/v1/packages/selection-preview", headers=headers, json=query)
    )
    repeated = checked(
        client.post("/api/v1/packages/selection-preview", headers=headers, json=query)
    )
    assert before["selection_sha256"] == repeated["selection_sha256"]
    confirmed = query | {"expected_sha256": before["selection_sha256"]}
    export = client.post("/api/v1/packages/export", headers=headers, json=confirmed)
    assert export.status_code == 200, export.text
    asset = checked(
        client.post(
            f"/api/v1/courses/{course}/assets",
            headers=headers,
            files={"file": ("新增图片.png", png(), "image/png")},
        ),
        201,
    )
    checked(
        client.patch(
            f"/api/v1/notes/{note['id']}",
            headers=headers,
            json={
                "revision": note["revision"],
                "content": note["content"] + f"\n![[asset:{asset['id']}|后新增依赖]]",
            },
        )
    )
    rejected = client.post("/api/v1/packages/export", headers=headers, json=confirmed)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["error"]["code"] == "PACKAGE_SELECTION_CHANGED"
    after = checked(
        client.post("/api/v1/packages/selection-preview", headers=headers, json=query)
    )
    assert before["selection_sha256"] != after["selection_sha256"]
    assert len(after["selection"]["assets"]) == 2
    assert (
        client.post(
            "/api/v1/packages/export",
            headers=headers,
            json=query | {"expected_sha256": after["selection_sha256"]},
        ).status_code
        == 200
    )


def test_import_confirmation_covers_selection_without_creating_partial_copy(package):
    client, headers, _course, _note, raw, _manifest, _members = package
    viewed = checked(preview(client, headers, raw))
    payload = request_for(viewed)
    verified = checked(
        client.post(
            "/api/v1/packages/selection-preview",
            headers=headers,
            json={
                "preview_id": payload["preview_id"],
                "selection": payload["selection"],
            },
        )
    )
    rejected = client.post(
        "/api/v1/packages/import",
        headers=headers,
        json=payload | {"expected_sha256": "0" * 64},
    )
    assert rejected.status_code == 409
    assert len(account_state(client, headers)) == 1
    result = checked(
        client.post(
            "/api/v1/packages/import",
            headers=headers,
            json=payload | {"expected_sha256": verified["selection_sha256"]},
        )
    )
    assert result["note_count"] == 1


def test_own_highly_repetitive_note_exports_as_stored_and_roundtrips(package):
    client, headers, course, note, _raw, _manifest, _members = package
    body = "A" * 2_000_000
    checked(
        client.patch(
            f"/api/v1/notes/{note['id']}",
            headers=headers,
            json={"revision": note["revision"], "content": body},
        )
    )
    exported = client.post(
        "/api/v1/packages/export",
        headers=headers,
        json={
            "course_id": course,
            "kind": "course",
            "selection": {"notes": [note["id"]]},
        },
    )
    assert exported.status_code == 200, exported.text
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert archive.getinfo("manifest.json").compress_type == zipfile.ZIP_STORED
    viewed = checked(preview(client, headers, exported.content))
    result = checked(
        client.post(
            "/api/v1/packages/import", headers=headers, json=request_for(viewed)
        )
    )
    with SessionLocal() as db:
        restored = db.scalar(select(Note).where(Note.course_id == result["course_id"]))
        assert restored.content == body


def test_real_office_pdf_and_utf8_files_pass_signature_validation(package):
    from docx import Document as WordDocument
    from pptx import Presentation
    from pypdf import PdfWriter
    from test_materialhub import upload
    from app.workers.materials import drain_jobs

    client, headers, course, _note, _raw, _manifest, _members = package
    word = WordDocument()
    word.add_paragraph("可移植Word原文")
    slides = Presentation()
    slides.slides.add_slide(slides.slide_layouts[6]).shapes.add_textbox(
        0, 0, 1000000, 1000000
    ).text = "PPTX原文"
    pdf = PdfWriter()
    pdf.add_blank_page(width=100, height=100)
    for filename, document, save in [
        ("word.docx", word, "save"),
        ("slides.pptx", slides, "save"),
        ("paper.pdf", pdf, "write"),
    ]:
        binary = io.BytesIO()
        getattr(document, save)(binary)
        upload(client, headers, course, binary.getvalue(), filename)
    upload(client, headers, course, "纯文本原件", "文本.txt")
    drain_jobs()
    catalog = checked(
        client.get(f"/api/v1/courses/{course}/packages/catalog", headers=headers)
    )
    response = client.post(
        "/api/v1/packages/export",
        headers=headers,
        json={"course_id": course, "selection": all_selection(catalog)},
    )
    assert response.status_code == 200, response.text
    assert (
        len(
            [
                row
                for row in checked(preview(client, headers, response.content))["items"]
                if row["category"] == "documents"
            ]
        )
        == 4
    )


def test_course_package_merges_additively_into_owned_target_and_retries_once(package):
    client, headers, course, note, raw, _manifest, _members = package
    viewed = checked(preview(client, headers, raw))
    before = account_state(client, headers)
    # Merging back into the source itself is still a fresh identity copy.
    query = {
        "preview_id": viewed["preview_id"],
        "target_course_id": course,
        "selection": all_selection(viewed),
    }
    verified = checked(
        client.post("/api/v1/packages/selection-preview", headers=headers, json=query)
    )
    payload = query | {
        "request_id": str(uuid4()),
        "expected_sha256": verified["selection_sha256"],
    }
    result = checked(
        client.post("/api/v1/packages/import", headers=headers, json=payload)
    )
    assert result["course_id"] == course and result["note_count"] == 1
    assert account_state(client, headers) == before
    assert (
        checked(client.post("/api/v1/packages/import", headers=headers, json=payload))
        == result
    )
    assert (
        client.post(
            "/api/v1/packages/import",
            headers=headers,
            json=payload | {"target_course_id": None},
        ).status_code
        == 409
    )
    with SessionLocal() as db:
        original = db.get(Note, note["id"])
        copies = db.scalars(select(Note).where(Note.course_id == course)).all()
        assert (
            original.content == note["content"]
            and original.revision == note["revision"]
        )
        assert len(copies) == 2 and len({row.id for row in copies}) == 2


def test_merge_checks_target_owner_and_retirement_before_copying_files(
    package, monkeypatch
):
    client, headers, course, _note, raw, _manifest, _members = package
    viewed = checked(preview(client, headers, raw))
    _stranger, other_course = context(client)
    retired = checked(
        client.post("/api/v1/courses", headers=headers, json={"name": "已删除课程"}),
        201,
    )
    with SessionLocal() as db:
        db.get(Course, retired["id"]).deleted_at = utc_now()
        db.commit()

    def forbid_copy(*_args, **_kwargs):
        raise AssertionError("Forbidden target must fail before any file writes")

    with monkeypatch.context() as patch:
        patch.setattr(service.LocalFileStorage, "write_stream", forbid_copy)
        for target in (other_course, retired["id"], str(uuid4())):
            payload = request_for(viewed) | {"target_course_id": target}
            assert (
                client.post(
                    "/api/v1/packages/import", headers=headers, json=payload
                ).status_code
                == 404
            )
            assert (
                client.post(
                    "/api/v1/packages/selection-preview",
                    headers=headers,
                    json={
                        "preview_id": viewed["preview_id"],
                        "selection": payload["selection"],
                        "target_course_id": target,
                    },
                ).status_code
                == 404
            )
    assert (
        client.post(
            "/api/v1/packages/import",
            headers=headers,
            json=request_for(viewed)
            | {"target_course_id": course, "parent_folder_id": str(uuid4())},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/packages/import",
            headers=headers,
            json=request_for(viewed)
            | {"target_course_id": course, "title": "不可重命名目标"},
        ).status_code
        == 422
    )
