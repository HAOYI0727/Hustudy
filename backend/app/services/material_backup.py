"""M1 account snapshot adapter; derived ZIP bytes are intentionally rebuildable."""

from pathlib import Path
import hashlib
from uuid import uuid4
from sqlalchemy import select
from ..core import backup_contract as contract
from ..core.config import get_settings
from ..core.storage import LocalFileStorage
from ..models import (
    Course,
    Document,
    DocumentVersion,
    DocumentChunk,
    Asset,
    ManualTranscript,
    ProcessingJob,
    MaterialExport,
)

MODELS = [
    Document,
    DocumentVersion,
    DocumentChunk,
    Asset,
    ProcessingJob,
    ManualTranscript,
    MaterialExport,
]
FILTERS = {
    "processing_jobs": ProcessingJob.type.not_in(["ACCOUNT_BACKUP", "ACCOUNT_RESTORE"])
}


def snapshot(db, user_id):
    tables = contract.serialize(db, user_id, MODELS, FILTERS)
    courses = {
        row.id
        for row in db.scalars(
            select(Course).where(Course.user_id == user_id, Course.deleted_at.is_(None))
        )
    }
    documents = {row["id"]: row for row in tables["documents"]}
    versions = {row["id"]: row for row in tables["document_versions"]}
    active_docs = {
        key
        for key, row in documents.items()
        if not row["deleted_at"] and row["course_id"] in courses
    }
    store = LocalFileStorage(Path(get_settings().storage_root))
    files, cache = [], {}

    def attach(row, field, course_id, active, expected_hash=None):
        value = row[field]
        if not active or not value:
            row[field] = None if field in {"preview_path", "zip_path"} else ""
            return
        source = store.checked(Path(value))
        scope = store.root / user_id / (course_id or "")
        if not source.is_relative_to(scope) or not source.is_file():
            raise ValueError("备份来源文件缺失或不在本人课程目录")
        if source not in cache:
            suffix = source.suffix.lower()
            if suffix not in {
                ".pptx",
                ".pdf",
                ".docx",
                ".md",
                ".markdown",
                ".txt",
                ".png",
                ".jpg",
                ".webp",
            }:
                raise ValueError("备份文件类型不受支持")
            key = str(uuid4())
            cache[source] = "file:" + key
            files.append(
                {
                    "id": key,
                    "course_id": course_id,
                    "member": "files/" + key + suffix,
                    "suffix": suffix,
                    "source": source,
                    "expected_hash": expected_hash,
                }
            )
        row[field] = cache[source]

    for row in tables["documents"]:
        attach(
            row,
            "storage_path",
            row["course_id"],
            row["id"] in active_docs,
            row["sha256"],
        )
    for row in tables["document_versions"]:
        parent = documents[row["document_id"]]
        active = parent["id"] in active_docs
        attach(row, "source_path", parent["course_id"], active, row["sha256"])
        attach(
            row,
            "preview_path",
            parent["course_id"],
            active and row["preview_status"] == "SUCCEEDED",
        )
    withdrawn = {
        row["chunk_id"]
        for row in tables["manual_transcripts"]
        if row["status"] == "WITHDRAWN"
    }
    for row in tables["document_chunks"]:
        if (
            versions[row["version_id"]]["document_id"] not in active_docs
            or row["id"] in withdrawn
        ):
            row["text"] = ""
    for row in tables["manual_transcripts"]:
        if (
            versions[row["version_id"]]["document_id"] not in active_docs
            or row["status"] == "WITHDRAWN"
        ):
            row["text"] = ""
    for row in tables["assets"]:
        source = versions.get(row["source_version_id"])
        active = not row["deleted"] and (
            row["course_id"] is None or row["course_id"] in courses
        )
        active = active and (
            row["source_version_id"] is None
            or (source and source["document_id"] in active_docs)
        )
        attach(row, "storage_path", row["course_id"], active, row["sha256"])
    for row in tables["material_exports"]:
        row["zip_path"] = None
    return tables, files


def empty(db, user_id):
    contract.assert_empty(db, user_id, MODELS, FILTERS)


def validate(db, user_id, source_user, tables, all_ids, paths):
    decoded = contract.validate(
        db, user_id, source_user, MODELS, tables, all_ids, paths
    )
    documents = {row["id"]: row for row in decoded["documents"]}
    used = set()
    for name, fields in {
        "documents": ["storage_path"],
        "document_versions": ["source_path", "preview_path"],
        "assets": ["storage_path"],
    }.items():
        for original, row in zip(tables[name], decoded[name]):
            course = (
                documents[row["document_id"]]["course_id"]
                if name == "document_versions"
                else row["course_id"]
            )
            scope = (
                Path(get_settings().storage_root).absolute()
                / user_id
                / (course or "_global")
            )
            for field in fields:
                if row[field]:
                    if not Path(row[field]).is_relative_to(scope):
                        raise ValueError("恢复文件与所属课程不一致")
                    used.add(original[field])
    if used != set(paths):
        raise ValueError("备份含未被业务对象引用的文件")
    for job in decoded["processing_jobs"]:
        if job["status"] not in {"SUCCEEDED", "FAILED", "CANCELLED"} or job["type"] in {
            "ACCOUNT_BACKUP",
            "ACCOUNT_RESTORE",
        }:
            raise ValueError("备份不能恢复活动任务或控制任务")
        job["lease_token"], job["lease_until"] = None, None
    return decoded


def apply(db, decoded):
    contract.apply(db, MODELS, decoded)
    from .search import index_version

    for row in decoded["document_versions"]:
        index_version(db, row["id"])


def require_sources(db, user_id, sources):
    from fastapi import HTTPException
    from ..repositories.materials import active_version
    from ..repositories.assets import active_asset

    try:
        for key in sources.get("versions", []):
            active_version(db, key, user_id)
        for key in sources.get("assets", []):
            active_asset(db, key, user_id)
        for key in sources.get("transcripts", []):
            row = db.get(ManualTranscript, key)
            if (
                not row
                or row.user_id != user_id
                or row.status not in {"CONFIRMED", "SUPERSEDED"}
            ):
                raise ValueError("备份人工来源已撤回")
            active_version(db, row.version_id, user_id)
    except HTTPException as error:
        raise ValueError("备份来源已删除或撤权，请重新生成") from error


def verify_files(tables, files):
    blobs = {"file:" + row["id"]: row for row in files}
    for name, field in [
        ("documents", "storage_path"),
        ("document_versions", "source_path"),
        ("assets", "storage_path"),
    ]:
        for row in tables[name]:
            if row[field]:
                blob = blobs.get(row[field])
                if (
                    not blob
                    or row["sha256"] != blob["sha256"]
                    or row["size_bytes"] != blob["size_bytes"]
                ):
                    raise ValueError("备份文件与业务对象的hash/字节数不一致")


def verify_citations(tables, citations):
    chunks = {row["id"]: row for row in tables["document_chunks"]}
    for row in citations:
        chunk = chunks.get(row["chunk_id"])
        if (
            not chunk
            or chunk["version_id"] != row["version_id"]
            or row["quote_hash"] != hashlib.sha256(row["quote"].encode()).hexdigest()
        ):
            raise ValueError("备份引用版本、片段或摘录hash不一致")
        if (
            row["locator_type"] != chunk["locator_type"]
            or row["locator_value"] != chunk["locator_value"]
        ):
            raise ValueError("备份引用定位与来源不一致")
        if chunk["text"] and row["quote"] not in chunk["text"]:
            raise ValueError("备份摘录不在对应原文中")
