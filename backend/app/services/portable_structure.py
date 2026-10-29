"""Schema and semantic helpers for explicit course/folder package transfers."""

import json
import re

from ..core import backup_contract
from ..models import Course
from . import material_backup, note_backup, ai_backup, exam_backup

ADAPTERS = [material_backup, note_backup, ai_backup, exam_backup]
MODELS = [Course, *(model for adapter in ADAPTERS for model in adapter.MODELS)]
BY_TABLE = {model.__tablename__: model for model in MODELS}
CATEGORIES = {
    "notes": "notes",
    "folders": "note_folders",
    "documents": "documents",
    "assets": "assets",
    "topics": "topics",
    "past_papers": "past_papers",
    "exam_papers": "exam_papers",
    "ai_results": "ai_results",
    "reports": "exam_analysis_reports",
    "blueprints": "exam_blueprints",
}
OMITTED = {
    "processing_jobs",
    "material_exports",
    "remote_queries",
    "note_trash_policies",
    "feedback",
}
FOLDER_TABLES = {
    "courses",
    "note_folders",
    "notes",
    "note_links",
    "assets",
    "asset_references",
}
MAX_METADATA = 8 * 1024 * 1024
MAX_ROWS = 20000
MAX_FILES = 2999
MAX_CONTENT = 256 * 1024 * 1024
TOKEN = re.compile(r"(!?)\[\[(note|asset):([0-9a-fA-F-]{36})(?:\|([^\]]*))?\]\]")
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
CONTROL_KEYS = {
    "job_id",
    "image_job_id",
    "ai_extract",
    "ai_topic_index",
    "vision_checkpoints",
    "execution",
    "checkpoint",
    "checkpoints",
    "consented_at",
    "dispatched_at",
    "api_key",
    "api_config",
    "config_revision",
    "lease_token",
    "lease_until",
}
TEXT_KEYS = {
    "title",
    "name",
    "text",
    "content",
    "stem",
    "answer",
    "explanation",
    "quote",
    "reason",
    "message",
    "query",
    "description",
    "label",
    "context_stem",
    "whole_stem",
    "source_number",
    "goal",
    "markdown",
    "summary",
    "model_notice",
    "display_label",
    "number",
    "body",
}


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def uuid_value(value):
    return isinstance(value, str) and bool(UUID_PATTERN.fullmatch(value))


def clean_controls(value):
    if isinstance(value, dict):
        return {
            key: clean_controls(item)
            for key, item in value.items()
            if key not in CONTROL_KEYS
        }
    if isinstance(value, list):
        return [clean_controls(item) for item in value]
    return value


def definitions(value):
    result = set()
    if isinstance(value, dict):
        if uuid_value(value.get("id")):
            result.add(value["id"])
        for item in value.values():
            result.update(definitions(item))
    elif isinstance(value, list):
        for item in value:
            result.update(definitions(item))
    return result


def json_references(value, key=""):
    """Exact structured identities only; never replace arbitrary prose substrings."""
    result = set()
    if isinstance(value, dict):
        for field, item in value.items():
            if uuid_value(field):
                result.add(field)
            elif ":" in field and all(uuid_value(part) for part in field.split(":")):
                result.update(field.split(":"))
            result.update(json_references(item, field))
    elif isinstance(value, list):
        for item in value:
            result.update(json_references(item, key))
    elif isinstance(value, str):
        if key not in TEXT_KEYS and uuid_value(value):
            result.add(value)
        result.update(match[2].lower() for match in TOKEN.findall(value))
    return result


def row_json(row):
    return {
        field: backup_contract.strict_json(value.encode())
        for field, value in row.items()
        if field.endswith("_json") and isinstance(value, str)
    }


def all_definitions(tables):
    identities = {row["id"] for rows in tables.values() for row in rows}
    for rows in tables.values():
        for row in rows:
            for value in row_json(row).values():
                identities.update(definitions(value))
    return identities


def references(table, row, *, markdown_notes=False):
    model = BY_TABLE[table]
    refs = set()
    for column in model.__table__.columns:
        if column.foreign_keys and row.get(column.name):
            if next(iter(column.foreign_keys)).column.table.name != "users":
                refs.add(row[column.name])
    if table == "topics" and row.get("merged_into_id"):
        refs.add(row["merged_into_id"])
    if table == "mistakes" and uuid_value(row.get("question_id")):
        refs.add(row["question_id"])
    for value in row_json(row).values():
        refs.update(json_references(value))
    for field in ("content", "stem", "answer"):
        if isinstance(row.get(field), str):
            for _, kind, identity, _ in TOKEN.findall(row[field]):
                if kind == "asset" or markdown_notes:
                    refs.add(identity.lower())
    return refs


def markdown(value, mapping, warnings=None):
    def replace(match):
        bang, kind, original, label = match.groups()
        identity = original.lower()
        if identity in mapping:
            return (
                f"{bang}[[{kind}:{mapping[identity]}"
                + (f"|{label}" if label is not None else "")
                + "]]"
            )
        if warnings is not None:
            warnings.add("未包含的笔记双链或图片已转为文字标记，不会指向原账户对象。")
        text = label or ("未包含的笔记" if kind == "note" else "未包含的图片")
        return re.sub(r"([\\`*_{}\[\]<>()!#|])", r"\\\1", text.replace("\n", " "))

    return TOKEN.sub(replace, value)


def remap_json(value, mapping, key=""):
    if isinstance(value, dict):
        result = {}
        for field, item in value.items():
            target = mapping.get(field, field)
            if ":" in field and all(uuid_value(part) for part in field.split(":")):
                target = ":".join(mapping.get(part, part) for part in field.split(":"))
            result[target] = remap_json(item, mapping, field)
        return result
    if isinstance(value, list):
        return [remap_json(item, mapping, key) for item in value]
    if isinstance(value, str):
        if key not in TEXT_KEYS and value in mapping:
            return mapping[value]
        return markdown(value, mapping)
    return value


def validate_envelope(manifest):
    expected = {
        "format",
        "kind",
        "source_course_id",
        "source_user_id",
        "course",
        "tables",
        "files",
        "warnings",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected:
        raise ValueError("课程包清单字段不完整或存在未知字段")
    if manifest["format"] != "hustudy-package-v1" or manifest["kind"] not in {
        "course",
        "folder",
    }:
        raise ValueError("不支持的课程包格式")
    if not uuid_value(manifest["source_course_id"]) or not uuid_value(
        manifest["source_user_id"]
    ):
        raise ValueError("课程包来源标识无效")
    if (
        not isinstance(manifest["warnings"], list)
        or len(manifest["warnings"]) > 100
        or any(not isinstance(w, str) or len(w) > 500 for w in manifest["warnings"])
    ):
        raise ValueError("课程包说明不合法")
    if len(encode(manifest).encode()) > MAX_METADATA:
        raise ValueError("课程包清单超过8MiB")
    tables = manifest["tables"]
    if not isinstance(tables, dict) or set(tables) != set(BY_TABLE):
        raise ValueError("课程包表集合不完整或含未知表")
    all_ids = backup_contract.ids(tables)
    row_ids = [identity for identities in all_ids.values() for identity in identities]
    if len(row_ids) != len(set(row_ids)) or manifest["source_user_id"] in row_ids:
        raise ValueError("课程包不同对象不能共用同一标识")
    if sum(map(len, tables.values())) > MAX_ROWS or len(tables["notes"]) > 2000:
        raise ValueError("课程包超过2000篇笔记或20000条业务记录")
    if any(tables[name] for name in OMITTED):
        raise ValueError("课程包不能携带任务、授权、账户设置或反馈")
    if manifest["kind"] == "folder" and any(
        rows for name, rows in tables.items() if name not in FOLDER_TABLES
    ):
        raise ValueError("文件夹包仅支持笔记、文件夹和图片")
    course = manifest["course"]
    if (
        not isinstance(course, dict)
        or tables["courses"] != [course]
        or course.get("id") != manifest["source_course_id"]
        or course.get("deleted_at") is not None
    ):
        raise ValueError("课程包必须仅包含一个有效来源课程")
    files = manifest["files"]
    if not isinstance(files, list) or len(files) > MAX_FILES:
        raise ValueError("课程包文件数量超过预算")
    file_ids = set()
    suffixes = {
        ".pdf",
        ".pptx",
        ".docx",
        ".md",
        ".markdown",
        ".txt",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }
    for item in files:
        if not isinstance(item, dict) or set(item) != {
            "id",
            "member",
            "course_id",
            "suffix",
            "sha256",
            "size_bytes",
        }:
            raise ValueError("课程包文件字段不合法")
        if (
            not uuid_value(item["id"])
            or item["id"] in file_ids
            or item["suffix"] not in suffixes
            or item["member"] != "files/" + item["id"] + item["suffix"]
        ):
            raise ValueError("课程包文件标识或类型不合法")
        if (
            item["course_id"] != course["id"]
            or type(item["size_bytes"]) is not int
            or not 0 < item["size_bytes"] <= 30 * 1024 * 1024
            or not isinstance(item["sha256"], str)
            or not re.fullmatch("[0-9a-f]{64}", item["sha256"])
        ):
            raise ValueError("课程包文件归属、大小或摘要不合法")
        file_ids.add(item["id"])
    if sum(item["size_bytes"] for item in files) > MAX_CONTENT:
        raise ValueError("课程包解压内容超过256MiB")
    return all_ids


class NoExistingRows:
    def get(self, _model, _identity):
        return None


def validate_rows(manifest):
    all_ids = validate_envelope(manifest)
    tables, user, course = (
        manifest["tables"],
        manifest["source_user_id"],
        manifest["source_course_id"],
    )
    paths = {"file:" + item["id"]: "file:" + item["id"] for item in manifest["files"]}
    decoded = backup_contract.validate(
        NoExistingRows(), user, user, MODELS, tables, all_ids, paths
    )
    for name, rows in tables.items():
        for row in rows:
            if row.get("course_id", course) != course or row["user_id"] != user:
                raise ValueError("课程包含跨课程或跨账户对象")
            if row.get("deleted") or row.get("deleted_at") or row.get("purge_after"):
                raise ValueError("课程包不包含回收站或删除对象")
            for value in row_json(row).values():
                if clean_controls(value) != value:
                    raise ValueError("课程包含可执行任务或授权元数据")
    from .note_folders import validate_tree

    validate_tree(tables["note_folders"])
    folders = {row["id"]: row for row in tables["note_folders"]}
    for row in tables["notes"]:
        if (
            row["revision"] < 1
            or not row["title"].strip()
            or row["deleted_at"] is not None
            or row["purge_after"] is not None
        ):
            raise ValueError("笔记状态不合法")
        note_backup._tags.validate_python(row["tags"])
        if row["folder_id"] and folders[row["folder_id"]]["course_id"] != course:
            raise ValueError("笔记文件夹归属不合法")
    known = all_definitions(tables) | {user}
    for name, rows in tables.items():
        for row in rows:
            unknown = references(name, row) - known
            if unknown:
                raise ValueError(f"课程包{name}包含缺失或无法识别的结构化关联")
    material_backup.verify_files(tables, manifest["files"])
    material_backup.verify_citations(tables, tables["citations"])
    blobs = {"file:" + item["id"]: item for item in manifest["files"]}
    from .documents import MIMES

    mime_types = {suffix: {mime} for suffix, mime in MIMES.items()} | {
        ".md": {"text/plain", "text/markdown", "text/x-markdown"},
        ".markdown": {"text/plain", "text/markdown", "text/x-markdown"},
        ".txt": {"text/plain"},
        ".png": {"image/png"},
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".webp": {"image/webp"},
    }
    for table, field in (
        ("documents", "storage_path"),
        ("document_versions", "source_path"),
        ("assets", "storage_path"),
    ):
        for row in tables[table]:
            if (
                row[field]
                and row["mime_type"] not in mime_types[blobs[row[field]]["suffix"]]
            ):
                raise ValueError("文件扩展名与业务MIME类型不匹配")
    for row in tables["document_versions"]:
        if row["preview_path"] and blobs[row["preview_path"]]["suffix"] != ".pdf":
            raise ValueError("兼容预览文件须为PDF")
    used = {
        row[field]
        for table, fields in {
            "documents": ["storage_path"],
            "document_versions": ["source_path", "preview_path"],
            "assets": ["storage_path"],
        }.items()
        for row in tables[table]
        for field in fields
        if row[field]
    }
    if used != set(paths):
        raise ValueError("课程包文件集合与业务引用不一致")
    return decoded
