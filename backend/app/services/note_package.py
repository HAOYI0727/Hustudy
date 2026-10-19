"""Portable notes with exact source bodies, relative links and verified images."""

from datetime import datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import time
from uuid import UUID
import zipfile

from fastapi import HTTPException
from sqlalchemy import select, func, cast, LargeBinary, or_
from ..core.config import get_settings
from ..core.database import begin_read_snapshot
from ..core.storage import LocalFileStorage, check_capacity
from ..models import Note, Course, Asset, Citation
from ..models.base import utc_now
from ..repositories.assets import available_assets
from ..repositories.materials import active_version
from .note_export_names import allocate_names, relative_link
from .note_folders import export_paths

MAX_CONTENT = 256 * 1024 * 1024
MAX_METADATA = 16 * 1024 * 1024
MAX_NOTES = 2000
MAX_REFERENCES = 10000
EXPORT_SECONDS = 120
TOKEN_RE = re.compile(r"(!?)\[\[(note|asset):([0-9a-fA-F-]{36})(?:\|([^\]]*))?\]\]")


def available_notes(user_id):
    return (
        (Note.user_id == user_id)
        & Note.deleted.is_(False)
        & or_(
            Note.course_id.is_(None),
            select(Course.id)
            .where(
                Course.id == Note.course_id,
                Course.user_id == user_id,
                Course.deleted_at.is_(None),
            )
            .exists(),
        )
    )


def digest(content):
    return hashlib.sha256(content).hexdigest()


def hash_file(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(65536):
            value.update(block)
    return value.hexdigest()


def cleanup(path):
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def output_path(user_id, job_id, token):
    # Names are server UUIDs, never note titles or original filenames.
    root = Path(get_settings().storage_root)
    path = (
        root / str(UUID(user_id)) / "note-exports" / f"{UUID(job_id)}-{UUID(token)}.zip"
    )
    return LocalFileStorage(root).checked(path)


def citation_available(db, citation, user_id):
    if citation.availability != "active":
        return False
    try:
        active_version(db, citation.version_id, user_id)
        return True
    except HTTPException:
        return False


def sources_available(db, user_id, sources):
    for model, key, scope in (
        (Note, "notes", available_notes(user_id)),
        (Asset, "assets", available_assets(user_id)),
    ):
        ids = sources.get(key, [])
        selected = func.json_each(json.dumps(ids)).table_valued("value")
        if ids and db.scalar(
            select(func.count())
            .select_from(model)
            .where(model.id.in_(select(selected.c.value)), scope)
        ) != len(ids):
            return False
    for citation_id in sources.get("citations", []):
        citation = db.scalar(
            select(Citation).where(
                Citation.id == citation_id, Citation.user_id == user_id
            )
        )
        if not citation or not citation_available(db, citation, user_id):
            return False
    return True


def escape_label(value):
    return re.sub(
        r"([\\`*_{}\[\]<>()!#|])", r"\\\1", value.replace("\r", " ").replace("\n", " ")
    )


def snapshot(db, user_id, options=None):
    scope = available_notes(user_id)
    simple = options is not None
    include_images = options.get("include_images", False) if simple else True
    if simple:
        scope = scope & Note.id.in_(options["selected_ids"])
    byte_count = (
        db.scalar(
            select(func.sum(func.length(cast(Note.content, LargeBinary)))).where(scope)
        )
        or 0
    )
    if byte_count * 2 > MAX_CONTENT:
        raise ValueError("笔记正文超过256MiB导出预算")
    notes = db.scalars(
        select(Note).where(scope).order_by(Note.id).limit(MAX_NOTES + 1)
    ).all()
    if not notes or len(notes) > MAX_NOTES:
        raise ValueError("需要1–2000篇有效笔记才能导出")
    if simple and len(notes) != len(options["selected_ids"]):
        raise ValueError("所选笔记已删除或不可访问，请重新选择导出")
    lookup = {n.id: n for n in notes}
    asset_ids = set()
    references = 0
    for note in notes:
        for match in TOKEN_RE.finditer(note.content):
            references += 1
            if references > MAX_REFERENCES:
                raise ValueError("正文双链/图片引用超过10000项导出预算")
            if match[1] == "!" and match[2] == "asset":
                asset_ids.add(match[3].lower())
    if len(asset_ids) > MAX_REFERENCES:
        raise ValueError("引用图片超过10000张导出预算")
    selected = func.json_each(json.dumps(sorted(asset_ids))).table_valued("value")
    # Missing/foreign IDs are labels only, never metadata or file reads.
    assets = {
        asset.id: asset
        for asset in db.scalars(
            select(Asset)
            .where(Asset.id.in_(select(selected.c.value)), available_assets(user_id))
            .order_by(Asset.id)
        ).all()
    }
    citations_scope = (Citation.note_id.in_(lookup), Citation.user_id == user_id)
    quote_bytes = (
        db.scalar(
            select(func.sum(func.length(cast(Citation.quote, LargeBinary)))).where(
                *citations_scope
            )
        )
        or 0
    )
    if quote_bytes > MAX_METADATA:
        raise ValueError("来源摘录超过16MiB清单预算")
    citations = db.scalars(
        select(Citation)
        .where(*citations_scope)
        .order_by(Citation.id)
        .limit(MAX_REFERENCES + 1)
    ).all()
    if len(citations) > MAX_REFERENCES:
        raise ValueError("资料引用超过10000条导出预算")
    manifest = {
        "format": "hustudy-note-package",
        "schema_version": 1,
        "scope": "account_notes",
        "snapshot_at": utc_now().isoformat(),
        "notes": [],
        "assets": [],
        "citations": [],
        "files": [],
    }
    sources = {
        "notes": list(lookup),
        "assets": list(assets) if include_images else [],
        "citations": [],
    }
    files = []
    course_ids = {n.course_id for n in notes} | {a.course_id for a in assets.values()}
    courses = {
        course.id: course.name
        for course in db.scalars(
            select(Course).where(
                Course.id.in_(course_ids - {None}),
                Course.user_id == user_id,
                Course.deleted_at.is_(None),
            )
        ).all()
    }
    directories = allocate_names(
        [
            (course_id, courses.get(course_id, "未分类"), "")
            for course_id in sorted(course_ids, key=lambda key: key or "")
        ],
        fallback="未分类",
        limit=40,
    )
    note_paths = {}
    for course_id in directories:
        names = allocate_names(
            [(n.id, n.title, ".md") for n in notes if n.course_id == course_id],
            fallback="未命名笔记",
        )
        note_paths.update(
            {
                key: f"notes/{directories[course_id]}/{name}"
                for key, name in names.items()
            }
        )
    asset_paths = {}
    for course_id in directories:
        entries = []
        for asset in assets.values():
            if asset.course_id != course_id:
                continue
            suffix = {
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/webp": ".webp",
            }.get(asset.mime_type)
            if not suffix:
                raise ValueError("引用图片格式不支持")
            label = re.sub(
                r"\.(png|jpe?g|webp)$",
                "",
                asset.name or asset.original_filename,
                flags=re.IGNORECASE,
            )
            entries.append((asset.id, label, suffix))
        names = allocate_names(entries, fallback="图片")
        asset_paths.update(
            {
                key: f"assets/{directories[course_id]}/{name}"
                for key, name in names.items()
            }
        )
    for asset in assets.values():
        if not include_images:
            continue
        suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(
            asset.mime_type
        )
        if not suffix:
            raise ValueError("引用图片格式不支持")
        member = asset_paths[asset.id]
        manifest["assets"].append(
            {
                "id": asset.id,
                "file": member,
                "sha256": asset.sha256,
                "size_bytes": asset.size_bytes,
                "name": asset.name,
                "alt": asset.alt,
                "tags": asset.tags,
                "course_id": asset.course_id,
                "source_version_id": asset.source_version_id,
                "source_page": asset.source_page,
                "source_locator_type": asset.source_locator_type,
            }
        )
        files.append((member, Path(asset.storage_path), asset.size_bytes, asset.sha256))
    if simple:
        note_paths = export_paths(db, user_id, notes)
        if include_images:
            renamed = allocate_names(
                [
                    (
                        a.id,
                        re.sub(
                            r"\.(png|jpe?g|webp)$",
                            "",
                            a.name or a.original_filename,
                            flags=re.IGNORECASE,
                        ),
                        {
                            "image/png": ".png",
                            "image/jpeg": ".jpg",
                            "image/webp": ".webp",
                        }[a.mime_type],
                    )
                    for a in assets.values()
                ],
                fallback="图片",
            )
            new_paths = {key: "images/" + name for key, name in renamed.items()}
            changes = {asset_paths[key]: path for key, path in new_paths.items()}
            files = [
                (changes[path], source, size, sha) for path, source, size, sha in files
            ]
            for asset_info in manifest["assets"]:
                asset_info["file"] = new_paths[asset_info["id"]]
            asset_paths = new_paths
        else:
            asset_paths = {}
    for citation in citations:
        if digest(citation.quote.encode("utf-8")) != citation.quote_hash:
            raise ValueError("资料引用摘录hash不一致，请先检查笔记来源")
        available = citation_available(db, citation, user_id)
        if available:
            sources["citations"].append(citation.id)
        manifest["citations"].append(
            {
                key: getattr(citation, key)
                for key in (
                    "id",
                    "note_id",
                    "version_id",
                    "chunk_id",
                    "locator_type",
                    "locator_value",
                    "quote",
                    "quote_hash",
                    "source_kind",
                )
            }
            | {"availability": "active" if available else "unavailable"}
        )
    for note in notes:
        links, images = [], []
        md_path = note_paths[note.id]
        raw_path = "sources/" + md_path.removeprefix("notes/")

        def replace(match):
            bang, kind, target, label = match.groups()
            target = target.lower()
            if kind == "note" and not bang:
                active = target in lookup
                links.append(
                    {
                        "target_id": target,
                        "availability": "active" if active else "unavailable",
                    }
                )
                label = escape_label(
                    label or (lookup[target].title if active else "目标笔记不可用")
                )
                return (
                    f"[{label}]({relative_link(md_path, note_paths[target])})"
                    if active
                    else (
                        f"{label}（未随包导出或已不可用）"
                        if simple
                        else f"{label}（目标笔记不可用：{target}）"
                    )
                )
            if kind == "asset" and bang:
                active = target in asset_paths
                images.append(
                    {
                        "target_id": target,
                        "availability": "active" if active else "unavailable",
                    }
                )
                label = escape_label(label or "课程图片")
                return (
                    f"![{label}]({relative_link(md_path, asset_paths[target])})"
                    if active
                    else (
                        f"{label}（{'未附带图片' if target in assets else '图片不可用'}）"
                        if simple
                        else f"{label}（图片不可用：{target}）"
                    )
                )
            return match[0]

        original = note.content.encode("utf-8")
        transformed = (
            f"# {escape_label(note.title)}\n\n"
            + TOKEN_RE.sub(replace, note.content)
            + "\n"
        ).encode("utf-8")
        if simple:
            references = [
                item for item in manifest["citations"] if item["note_id"] == note.id
            ]
            if references:
                transformed += (
                    "\n## 资料来源\n\n"
                    + "\n\n".join(
                        f"{escape_label(str(item['locator_type']))} {escape_label(str(item['locator_value']))}"
                        + (
                            "（来源当前不可用）"
                            if item["availability"] != "active"
                            else ""
                        )
                        + "\n\n> "
                        + item["quote"].replace("\n", "\n> ")
                        for item in references
                    )
                    + "\n"
                ).encode("utf-8")
        manifest["notes"].append(
            {
                "id": note.id,
                "course_id": note.course_id,
                "title": note.title,
                "tags": note.tags,
                "revision": note.revision,
                "content_file": raw_path,
                "content_sha256": digest(original),
                "markdown_file": md_path,
                "markdown_sha256": digest(transformed),
                "links": links,
                "images": images,
            }
        )
        if not simple:
            files.append((raw_path, original, len(original), digest(original)))
        files.append((md_path, transformed, len(transformed), digest(transformed)))
    return manifest, files, sources


def build_package(db, user_id, output, options=None):
    started = time.monotonic()
    begin_read_snapshot(db)
    manifest, files, sources = snapshot(db, user_id, options)
    root = Path(get_settings().storage_root)
    storage = LocalFileStorage(root)
    storage.checked(output)
    total = 0
    try:
        check_capacity(output.parent)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(
            output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1
        ) as archive:
            for member, source, expected_size, expected_hash in files:
                check_capacity(output.parent)
                if isinstance(source, Path):
                    source = storage.checked(source)
                    if (
                        not source.resolve().is_relative_to((root / user_id).resolve())
                        or not source.is_file()
                    ):
                        raise ValueError("图片缺失或不在当前账户存储范围")
                    stream = source.open("rb")
                else:
                    stream = BytesIO(source)
                value, size = hashlib.sha256(), 0
                with stream, archive.open(member, "w") as target:
                    while block := stream.read(65536):
                        total += len(block)
                        size += len(block)
                        if (
                            total > MAX_CONTENT
                            or time.monotonic() - started > EXPORT_SECONDS
                        ):
                            raise ValueError("导出超过256MiB或120秒预算")
                        value.update(block)
                        target.write(block)
                if size != expected_size or value.hexdigest() != expected_hash:
                    raise ValueError("图片或正文的大小/hash与记录不一致")
                manifest["files"].append(
                    {"path": member, "size_bytes": size, "sha256": value.hexdigest()}
                )
            encoded = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
            if (
                len(encoded) > MAX_METADATA
                or total + len(encoded) > MAX_CONTENT
                or time.monotonic() - started > EXPORT_SECONDS
            ):
                raise ValueError("导出清单/内容或处理时间超过预算")
            if options is None:
                archive.writestr("manifest.json", encoded)
                archive.writestr(
                    "README.md",
                    "# Hustudy 笔记知识库\n\n从 notes/课程名/笔记标题.md 开始阅读；双链和 assets/课程名/图片名称 使用相对路径。同名课程/文件自动加序号，非法字符已清理，UUID保留在清单。sources/课程名/笔记标题.md 是逐字UTF-8原始正文（含UUID语法），用于hash对照。manifest.json包含标签、revision、课程UUID、资料摘录/定位/来源状态及每文件SHA-256。失效来源明确标记。未复制课程原件，不支持恢复为完整账户；恢复请使用系统的完整账户备份。此包为生成时已保存数据快照，不包含浏览器未保存草稿。\n",
                )
        return {
            "sources": sources,
            "counts": {
                key: len(manifest[key])
                for key in ("notes", "assets", "citations", "files")
            },
            "snapshot_at": datetime.fromisoformat(manifest["snapshot_at"]),
            "sha256": hash_file(output),
            "size_bytes": output.stat().st_size,
        }
    except Exception:
        cleanup(output)
        raise
    finally:
        db.rollback()
