"""Explicit, isolated course/folder snapshots and additive UUID-remapped imports.

The package coordinator owns upload bytes, jobs, confirmation and transactions.
This module never commits, runs tasks, or reads another course to fill a reference.
"""

from copy import deepcopy
import hashlib
import time
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select, func, cast, LargeBinary, String, JSON

from ..core import backup_contract as contract
from ..core.config import get_settings
from ..core.database import begin_read_snapshot
from ..core.storage import LocalFileStorage
from ..models import Course, NoteFolder
from ..repositories.assets import available_assets
from .courses import owned_course
from .note_folders import owned_folder, tree_rows, validate_tree
from . import portable_structure as s


def _counts(manifest):
    return {
        category: len(manifest["tables"][table])
        for category, table in s.CATEGORIES.items()
    }


def _rows(db, user, table, clause, budget):
    if time.monotonic() > budget["deadline"]:
        raise ValueError("课程包处理超过120秒预算")
    model = s.BY_TABLE[table]
    query = select(model).where(model.user_id == user, clause)
    count = (
        db.scalar(query.with_only_columns(func.count(), maintain_column_froms=True))
        or 0
    )
    if budget["rows"] + count > s.MAX_ROWS or table == "notes" and count > 2000:
        raise ValueError("课程包记录数量超过预算")
    size = 0
    for column in model.__table__.columns:
        if isinstance(column.type, (String, JSON)):
            size += (
                db.scalar(
                    query.with_only_columns(
                        func.sum(func.length(cast(column, LargeBinary))),
                        maintain_column_froms=True,
                    )
                )
                or 0
            )
            if budget["bytes"] + size > s.MAX_METADATA:
                raise ValueError("课程包文本超过8MiB清单预算，请缩小课程范围")
    budget["rows"] += count
    budget["bytes"] += size
    return contract.serialize(db, user, [model], {table: clause})[table]


def _ids(rows):
    return [row["id"] for row in rows]


def _children(folders, root):
    result = {root}
    for _ in range(6):
        result.update(row["id"] for row in folders if row["parent_id"] in result)
    return result


def _normalize(tables, kind, warnings):
    if any(
        (s.row_json(row)["bank_meta_json"].get("exam_identity") or {}).get("confirmed")
        for row in tables.get("past_papers", [])
    ):
        warnings.add(
            "课程包中的真题身份声明会保留；导入后须由当前账户重新确认，原确认不冒充当前用户决定。"
        )
    for name, rows in tables.items():
        for row in rows:
            for field, value in s.row_json(row).items():
                clean = s.clean_controls(value)
                if clean != value:
                    warnings.add("执行任务、远程授权和AI检查点未包含在课程包中。")
                row[field] = s.encode(clean)
    # SQL ownership limits are repeated before semantic closure; no cross-course fetches.
    for name, field in (("past_papers", "bank_meta_json"), ("topics", "sources_json")):
        tables[name] = [
            row
            for row in tables[name]
            if not s.row_json(row)[field].get("deleted_by_user")
        ]
    tables["exam_attempts"] = [
        row for row in tables["exam_attempts"] if row["status"] != "IN_PROGRESS"
    ]
    for row in tables["mistakes"]:
        detail = s.row_json(row)["detail_json"]
        detail["redoes"] = {
            key: value
            for key, value in detail.get("redoes", {}).items()
            if value.get("status") == "COMPLETED"
        }
        row["detail_json"] = s.encode(detail)
    if kind == "folder":
        for row in tables["assets"]:
            if row["source_version_id"]:
                warnings.add("文件夹包保留独立图片，资料截图的回源信息不随文件夹导入。")
            row["source_version_id"] = row["source_page"] = row[
                "source_locator_type"
            ] = None
        if tables["citations"]:
            warnings.add("文件夹包不包含资料原件，笔记的资料回源引用不包含在内。")
        for name in tables:
            if name not in s.FOLDER_TABLES:
                tables[name] = []
    # Omit unsafe/out-of-scope dependent rows explicitly, rather than importing old IDs.
    for _ in range(20):
        known = s.all_definitions(tables) | {
            row["user_id"] for row in tables["courses"]
        }
        changed = False
        for name, rows in tables.items():
            keep = []
            for row in rows:
                refs = s.references(name, row)
                # Missing Markdown assets are degraded visibly, not hidden dependencies.
                if name == "notes":
                    refs -= {
                        identity.lower()
                        for _, _, identity, _ in s.TOKEN.findall(row["content"])
                    }
                if refs - known:
                    warnings.add(
                        f"{name}中存在未包含、已删除或跨课程的关联，相关条目已省略。"
                    )
                    changed = True
                else:
                    keep.append(row)
            tables[name] = keep
        if not changed:
            break
    else:
        raise ValueError("课程关联层级超过处理预算")
    mapping = {
        row["id"]: row["id"] for name in ("notes", "assets") for row in tables[name]
    }
    for row in tables["notes"]:
        row["content"] = s.markdown(row["content"], mapping, warnings)


def snapshot(db, user_id, course_id, kind="course", folder_id=None):
    if kind not in {"course", "folder"}:
        raise ValueError("导出类型必须为课程或笔记文件夹")
    if folder_id and kind != "folder":
        raise ValueError("课程导出不能附加文件夹范围")
    begin_read_snapshot(db)
    owned_course(db, user_id, course_id)
    tables = {name: [] for name in s.BY_TABLE}
    budget = {"rows": 0, "bytes": 0, "deadline": time.monotonic() + 120}

    def load(table, clause):
        return _rows(db, user_id, table, clause, budget)

    course = load("courses", Course.id == course_id)[0]
    tables["courses"] = [course]
    warnings = set()
    model = s.BY_TABLE
    tables["note_folders"] = load("note_folders", NoteFolder.course_id == course_id)
    if len(tables["note_folders"]) > 500:
        raise ValueError("课程文件夹超过500个")
    scope = None
    if folder_id:
        owned_folder(db, user_id, folder_id, course_id)
        scope = _children(tables["note_folders"], folder_id)
        tables["note_folders"] = [
            row for row in tables["note_folders"] if row["id"] in scope
        ]
        for row in tables["note_folders"]:
            if row["id"] == folder_id:
                row["parent_id"] = None
    note_scope = (model["notes"].course_id == course_id) & model["notes"].deleted.is_(
        False
    )
    if scope is not None:
        note_scope &= model["notes"].folder_id.in_(scope)
    tables["notes"] = load("notes", note_scope)
    if len(tables["notes"]) > 2000:
        raise ValueError("课程包最多2000篇笔记")
    note_ids = _ids(tables["notes"])
    asset_scope = available_assets(user_id, course_id)
    if kind == "folder":
        used_assets = {
            identity.lower()
            for row in tables["notes"]
            for _, token_kind, identity, _ in s.TOKEN.findall(row["content"])
            if token_kind == "asset"
        }
        referenced = select(model["asset_references"].asset_id).where(
            model["asset_references"].user_id == user_id,
            model["asset_references"].note_id.in_(note_ids),
        )
        asset_scope &= model["assets"].id.in_(used_assets) | model["assets"].id.in_(
            referenced
        )
    tables["assets"] = load("assets", asset_scope)
    tables["note_links"] = load(
        "note_links",
        model["note_links"].source_note_id.in_(note_ids)
        & model["note_links"].target_note_id.in_(note_ids),
    )
    tables["asset_references"] = load(
        "asset_references",
        model["asset_references"].note_id.in_(note_ids)
        & model["asset_references"].asset_id.in_(_ids(tables["assets"])),
    )
    if kind == "course":
        direct = (
            "documents",
            "topics",
            "past_papers",
            "exam_blueprints",
            "exam_papers",
            "ai_results",
            "exam_analysis_reports",
        )
        for name in direct:
            clause = model[name].course_id == course_id
            if name == "documents":
                clause &= model[name].deleted_at.is_(None)
            elif name == "ai_results":
                clause &= model[name].status.in_(["grounded", "insufficient_evidence"])
                clause &= ~model[name].prompt_version.in_(
                    [
                        "m2-execution-v1",
                        "m2-report-progress-v1",
                        "m2-report-checkpoint-v1",
                        "m2-qa-checkpoint-v1",
                    ]
                )
            tables[name] = load(name, clause)
        for name, parent, field in (
            ("document_versions", "documents", "document_id"),
            ("document_chunks", "document_versions", "version_id"),
            ("manual_transcripts", "document_versions", "version_id"),
            ("past_questions", "past_papers", "paper_id"),
            ("exam_attempts", "exam_papers", "paper_id"),
            ("mistakes", "exam_attempts", "attempt_id"),
            ("review_tasks", "mistakes", "mistake_id"),
        ):
            clause = getattr(model[name], field).in_(_ids(tables[parent]))
            if name == "manual_transcripts":
                clause &= model[name].status.in_(["CONFIRMED", "SUPERSEDED"])
            tables[name] = load(name, clause)
        confirmed = {
            row["chunk_id"] for row in tables["manual_transcripts"] if row["chunk_id"]
        }
        tables["document_chunks"] = [
            row
            for row in tables["document_chunks"]
            if row["source_kind"] != "manual_transcript" or row["id"] in confirmed
        ]
        tables["citations"] = load(
            "citations",
            model["citations"].note_id.in_(note_ids)
            & model["citations"].chunk_id.in_(_ids(tables["document_chunks"]))
            & (model["citations"].availability == "active"),
        )
    else:
        warnings.add("文件夹包仅包含笔记、目录与图片，不包含资料回源、题库和学习记录。")
    _normalize(tables, kind, warnings)
    # Files use opaque member identities; display names remain on the business objects.
    store = LocalFileStorage(Path(get_settings().storage_root))
    descriptors, cached, total_bytes = [], {}, 0
    for table, fields in {
        "documents": ["storage_path"],
        "document_versions": ["source_path", "preview_path"],
        "assets": ["storage_path"],
    }.items():
        for row in tables[table]:
            for field in fields:
                value = row[field]
                if not value:
                    continue
                path = store.checked(Path(value))
                if (
                    not path.is_relative_to(store.root / user_id / course_id)
                    or not path.resolve().is_relative_to(
                        (store.root / user_id / course_id).resolve()
                    )
                    or not path.is_file()
                ):
                    raise ValueError("导出文件缺失或不在本人当前课程目录")
                if path not in cached:
                    size = path.stat().st_size
                    total_bytes += size
                    if (
                        size > 30 * 1024 * 1024
                        or total_bytes > s.MAX_CONTENT
                        or len(descriptors) >= s.MAX_FILES
                    ):
                        raise ValueError("课程包单文件、总内容或成员数量超过预算")
                    identity = str(uuid4())
                    item = {
                        "id": identity,
                        "member": "files/" + identity + path.suffix.lower(),
                        "course_id": course_id,
                        "suffix": path.suffix.lower(),
                        "sha256": _file_hash(path, budget["deadline"]),
                        "size_bytes": size,
                    }
                    descriptors.append(item | {"source": path})
                    cached[path] = "file:" + identity
                row[field] = cached[path]
    manifest = {
        "format": "hustudy-package-v1",
        "kind": kind,
        "source_course_id": course_id,
        "source_user_id": user_id,
        "course": course,
        "tables": tables,
        "files": [
            {key: value for key, value in item.items() if key != "source"}
            for item in descriptors
        ],
        "warnings": sorted(warnings),
    }
    validate_manifest(manifest)
    return manifest, descriptors


def _file_hash(path, deadline=None):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(65536):
            if deadline is not None and time.monotonic() > deadline:
                raise ValueError("课程包文件处理超过120秒预算")
            value.update(block)
    return value.hexdigest()


def validate_manifest(manifest):
    s.validate_rows(manifest)
    tables = manifest["tables"]
    all_ids = contract.ids(tables)
    # Existing module validators add provenance, topic-tree and question-snapshot checks.
    root = (
        Path(get_settings().storage_root).absolute()
        / manifest["source_user_id"]
        / manifest["source_course_id"]
    )
    paths = {
        "file:" + item["id"]: root / (item["id"] + item["suffix"])
        for item in manifest["files"]
    }
    for adapter in s.ADAPTERS:
        adapter.validate(
            s.NoExistingRows(),
            manifest["source_user_id"],
            manifest["source_user_id"],
            tables,
            all_ids,
            paths,
        )


def catalog(manifest):
    validate_manifest(manifest)
    items = []
    for category, table in s.CATEGORIES.items():
        for row in manifest["tables"][table]:
            title = (
                row.get("title")
                or row.get("name")
                or row.get("query")
                or (
                    "课程分析"
                    if category == "reports"
                    else row.get("original_filename")
                )
                or "未命名条目"
            )
            item = {
                "category": category,
                "id": row["id"],
                "title": title[:240],
                "detail": {
                    "notes": "笔记与引用图片",
                    "folders": "目录容器（笔记需另选）",
                    "documents": "原件、版本与正文片段",
                    "past_papers": "题库与题目",
                    "exam_papers": "练习、已提交作答和错题复习",
                }.get(category, "已保存内容"),
            }
            if category == "folders":
                item["parent_id"] = row["parent_id"]
            if category == "notes":
                item["folder_id"] = row["folder_id"]
            items.append(item)
    roots = [
        row for row in manifest["tables"]["note_folders"] if row["parent_id"] is None
    ]
    package_title = (
        roots[0]["name"]
        if manifest["kind"] == "folder" and len(roots) == 1
        else manifest["course"]["name"]
    )
    return {
        "format": manifest["format"],
        "kind": manifest["kind"],
        "title": package_title,
        "items": items,
        "counts": _counts(manifest),
        "warnings": manifest["warnings"],
    }


def select_content(manifest, selection=None):
    validate_manifest(manifest)
    result = deepcopy(manifest)
    tables = result["tables"]
    lookup = {row["id"]: (name, row) for name, rows in tables.items() for row in rows}
    if selection is None:
        selected = {
            row["id"] for table in s.CATEGORIES.values() for row in tables[table]
        }
    else:
        if not isinstance(selection, dict) or set(selection) - set(s.CATEGORIES):
            raise ValueError("包含无法识别的内容类别")
        selected = set()
        for category, identities in selection.items():
            available = set(_ids(tables[s.CATEGORIES[category]]))
            if (
                not isinstance(identities, list)
                or len(identities) != len(set(identities))
                or not set(identities) <= available
            ):
                raise ValueError("选择的条目不存在、重复或不属于该类别")
            selected.update(identities)
    if not selected:
        raise ValueError("请至少选择一个可导入或导出的条目")
    requested = set(selected)
    selected.add(manifest["source_course_id"])
    definitions = {}
    for identity, (table, row) in lookup.items():
        for value in s.row_json(row).values():
            for inner in s.definitions(value):
                definitions.setdefault(inner, identity)
    children = {
        "documents": [("document_versions", "document_id")],
        "document_versions": [
            ("document_chunks", "version_id"),
            ("manual_transcripts", "version_id"),
        ],
        "past_papers": [("past_questions", "paper_id")],
        "exam_papers": [("exam_attempts", "paper_id")],
        "exam_attempts": [("mistakes", "attempt_id")],
        "mistakes": [("review_tasks", "mistake_id")],
        "notes": [("citations", "note_id"), ("asset_references", "note_id")],
    }
    # A selected folder is a container, not implicit consent to include its notes.
    for _ in range(40):
        before = set(selected)
        for identity in list(selected):
            table, row = lookup[identity]
            for ref in s.references(table, row):
                if ref in lookup:
                    selected.add(ref)
                elif ref in definitions:
                    selected.add(definitions[ref])
            for child_table, field in children.get(table, []):
                selected.update(
                    child["id"]
                    for child in tables[child_table]
                    if child[field] == identity
                )
        if selected == before:
            break
    else:
        raise ValueError("内容依赖超过处理层级预算")
    for row in tables["note_links"]:
        if row["source_note_id"] in selected and row["target_note_id"] in selected:
            selected.add(row["id"])
    result["tables"] = {
        name: [row for row in rows if row["id"] in selected]
        for name, rows in tables.items()
    }
    warnings = set(result["warnings"])
    extras = sum(
        1
        for identity in selected - requested
        if lookup[identity][0] in s.CATEGORIES.values()
    )
    if extras:
        warnings.add(
            f"为保持目录、图片及来源关系，已补入{extras}个依赖条目；可在最终清单中核对。"
        )
    mapping = {
        row["id"]: row["id"]
        for name in ("notes", "assets")
        for row in result["tables"][name]
    }
    for row in result["tables"]["notes"]:
        row["content"] = s.markdown(row["content"], mapping, warnings)
    used = {
        row[field]
        for table, fields in {
            "documents": ["storage_path"],
            "document_versions": ["source_path", "preview_path"],
            "assets": ["storage_path"],
        }.items()
        for row in result["tables"][table]
        for field in fields
        if row[field]
    }
    result["files"] = [item for item in result["files"] if "file:" + item["id"] in used]
    result["warnings"] = sorted(warnings)
    validate_manifest(result)
    return result, result["warnings"]


def _place_folders(folders, existing, parent_folder_id):
    sibling_names = {(row["parent_id"], row["name"].casefold()) for row in existing}
    for row in folders:
        if row["parent_id"] is None:
            row["parent_id"] = parent_folder_id
        original_title, number = row["name"], 2
        while (row["parent_id"], row["name"].casefold()) in sibling_names:
            suffix = f" (导入{number})"
            row["name"] = original_title[: 64 - len(suffix)] + suffix
            number += 1
        sibling_names.add((row["parent_id"], row["name"].casefold()))
    validate_tree(existing + folders)


def validate_target(
    db, user_id, manifest, target_course_id, parent_folder_id=None, title=None
):
    """Read-only placement preflight, repeated under the import caller's write lock."""
    validate_manifest(manifest)
    if not s.uuid_value(target_course_id):
        raise ValueError("目标课程标识无效")
    kind = manifest["kind"]
    existing = db.get(Course, target_course_id)
    if kind == "course" and parent_folder_id:
        raise ValueError("课程包须合并到课程根目录，不能指定笔记父文件夹")
    if existing is not None or kind == "folder":
        owned_course(db, user_id, target_course_id)
        if kind == "course" and title:
            raise ValueError("合并课程包不会修改目标课程名称")
        if parent_folder_id:
            owned_folder(db, user_id, parent_folder_id, target_course_id)
    elif title and (not isinstance(title, str) or not 1 <= len(title.strip()) <= 200):
        raise ValueError("课程名称须为1至200字")
    folders = deepcopy(manifest["tables"]["note_folders"])
    mapping = {row["id"]: str(uuid4()) for row in folders}
    for row in folders:
        row["id"] = mapping[row["id"]]
        row["parent_id"] = mapping.get(row["parent_id"])
        row["course_id"] = target_course_id
    _place_folders(
        folders,
        tree_rows(db, user_id, target_course_id) if existing is not None else [],
        parent_folder_id,
    )


def import_content(
    db, user_id, manifest, paths, *, target_course_id, parent_folder_id=None, title=None
):
    validate_target(db, user_id, manifest, target_course_id, parent_folder_id, title)
    tables = deepcopy(manifest["tables"])
    kind = manifest["kind"]
    creates_course = kind == "course" and db.get(Course, target_course_id) is None
    if not creates_course:
        owned_course(db, user_id, target_course_id, lock=True)
    identities = s.all_definitions(tables)
    mapping = {identity: str(uuid4()) for identity in identities}
    mapping[manifest["source_course_id"]] = target_course_id
    mapping[manifest["source_user_id"]] = user_id
    expected_paths = {"file:" + item["id"] for item in manifest["files"]}
    if set(paths) != expected_paths:
        raise ValueError("导入文件映射不完整")
    root = Path(get_settings().storage_root).absolute() / user_id / target_course_id
    storage = LocalFileStorage(root)
    deadline = time.monotonic() + 120
    for item in manifest["files"]:
        path = storage.checked(Path(paths["file:" + item["id"]]))
        if (
            not path.is_relative_to(root)
            or not path.is_file()
            or path.stat().st_size != item["size_bytes"]
            or _file_hash(path, deadline) != item["sha256"]
        ):
            raise ValueError("导入文件范围、大小或hash校验失败")
    for name, rows in tables.items():
        for row in rows:
            row["id"] = mapping[row["id"]]
            for column in s.BY_TABLE[name].__table__.columns:
                if column.foreign_keys and row.get(column.name):
                    row[column.name] = mapping[row[column.name]]
            row["user_id"] = user_id
            if name == "topics" and row["merged_into_id"]:
                row["merged_into_id"] = mapping[row["merged_into_id"]]
            if name == "mistakes" and row["question_id"] in mapping:
                row["question_id"] = mapping[row["question_id"]]
            for field, value in s.row_json(row).items():
                row[field] = s.encode(s.remap_json(value, mapping))
            for field in ("content", "stem", "answer"):
                if isinstance(row.get(field), str):
                    row[field] = s.markdown(row[field], mapping)
            if name == "exam_analysis_reports":
                row["status"] = "STALE"
            if name == "ai_results":
                # A saved imported result is readable history, never reusable remote consent.
                row["prompt_version"] = "portable-import-v1"
    course = tables["courses"][0]
    if title and creates_course:
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
            raise ValueError("课程名称须为1至200字")
        course["name"] = title.strip()
    folder_id = parent_folder_id if kind == "folder" else None
    if not creates_course:
        existing_folders = tree_rows(db, user_id, target_course_id)
        _place_folders(tables["note_folders"], existing_folders, parent_folder_id)
        for row in tables["notes"]:
            if row["folder_id"] is None:
                row["folder_id"] = parent_folder_id
    all_ids = contract.ids(tables)
    # Allow existing parent only for the explicitly checked folder destination.
    for row in tables.get("past_papers", []):
        meta = s.row_json(row)["bank_meta_json"]
        identity = meta.get("exam_identity")
        if identity:
            from .bank_identity import validate as validate_identity

            validate_identity(identity)
            meta["exam_identity"] = identity | {
                "confirmed": False,
                "confirmed_at": None,
                "revision": identity.get("revision", 0) + 1,
            }
            row["bank_meta_json"] = s.encode(meta)
    if parent_folder_id:
        all_ids["note_folders"].add(parent_folder_id)
    decoded = (
        contract.validate(db, user_id, user_id, s.MODELS, tables, all_ids, paths)
        if creates_course
        else contract.validate(
            db,
            user_id,
            user_id,
            [model for model in s.MODELS if model is not Course],
            tables,
            all_ids,
            paths,
        )
    )
    if creates_course:
        contract.apply(db, [Course], decoded)
    # Folders can point at an existing parent. Insert in topological order with that parent seeded.
    pending = list(decoded["note_folders"])
    done = {parent_folder_id} if parent_folder_id else set()
    while pending:
        ready = [
            row
            for row in pending
            if row["parent_id"] is None or row["parent_id"] in done
        ]
        if not ready:
            raise ValueError("导入文件夹存在循环或缺失父级")
        for row in ready:
            db.add(NoteFolder(**row))
            done.add(row["id"])
            pending.remove(row)
        db.flush()
    rest = [model for model in s.MODELS if model not in (Course, NoteFolder)]
    # Relations such as manual-transcript supersedes are deferred until the transaction ends.
    db.connection().exec_driver_sql("PRAGMA defer_foreign_keys=ON")
    contract.apply(db, rest, decoded)
    from .search import index_version

    for row in decoded["document_versions"]:
        index_version(db, row["id"])
    return {
        "course_id": target_course_id,
        "folder_id": folder_id,
        "counts": {
            name: len(rows)
            for name, rows in tables.items()
            if rows and (creates_course or name != "courses")
        },
        "warnings": manifest["warnings"],
    }
