"""M3 snapshot/restore boundary; account coordinator never reads note tables."""

from ..core import backup_contract as contract
from ..models import (
    Note,
    NoteLink,
    Citation,
    AssetReference,
    NoteFolder,
    NoteTrashPolicy,
)
from ..models.base import utc_now
from datetime import timedelta
from ..schemas.notes import NoteTags
from ..schemas.note_organization import folder_name
from .note_folders import validate_tree
from pydantic import TypeAdapter

MODELS = [NoteFolder, Note, NoteLink, Citation, AssetReference, NoteTrashPolicy]
_tags = TypeAdapter(NoteTags)


def upgrade_legacy_tags(tables):
    """Only called for a verified 0012 manifest by the account coordinator."""
    rows = tables.get("notes")
    if not isinstance(rows, list):
        raise ValueError("备份笔记表结构不正确")
    for row in rows:
        if not isinstance(row, dict) or "tags" in row:
            raise ValueError("旧版本备份笔记字段不正确")
        row["tags"] = []


def upgrade_legacy_folders(tables):
    if "note_folders" in tables or not isinstance(tables.get("notes"), list):
        raise ValueError("旧版本文件夹集合不正确")
    for row in tables["notes"]:
        if not isinstance(row, dict) or "folder_id" in row:
            raise ValueError("旧版本笔记文件夹字段不正确")
        row["folder_id"] = None
    tables["note_folders"] = []


def snapshot(db, user_id):
    return contract.serialize(db, user_id, MODELS), []


def upgrade_legacy_trash(tables):
    if "note_trash_policies" in tables or not isinstance(tables.get("notes"), list):
        raise ValueError("旧版本回收站结构不正确")
    now = utc_now()
    for row in tables["notes"]:
        if not isinstance(row, dict) or "deleted_at" in row or "purge_after" in row:
            raise ValueError("旧版本回收站字段不正确")
        row["deleted_at"] = now.isoformat() if row.get("deleted") else None
        row["purge_after"] = (
            (now + timedelta(days=30)).isoformat() if row.get("deleted") else None
        )
    tables["note_trash_policies"] = []


def empty(db, user_id):
    contract.assert_empty(db, user_id, MODELS)


def validate(db, user_id, source_user, tables, all_ids, paths):
    decoded = contract.validate(
        db, user_id, source_user, MODELS, tables, all_ids, paths
    )
    policies = decoded["note_trash_policies"]
    if len(policies) > 1:
        raise ValueError("备份回收站策略重复")
    days = policies[0]["retention_days"] if policies else 30
    if (days is not None and not 1 <= days <= 365) or any(
        p["revision"] < 1 for p in policies
    ):
        raise ValueError("备份回收站保留天数或版本不正确")
    for row in decoded["notes"]:
        if row["revision"] < 1 or row["deleted"] != (row["deleted_at"] is not None):
            raise ValueError("备份笔记删除状态不一致")
        expected = (
            row["deleted_at"] + timedelta(days=days)
            if row["deleted"] and days is not None
            else None
        )
        if row["purge_after"] != expected:
            raise ValueError("备份回收站清理期限不一致")
        if _tags.validate_python(row["tags"]) != row["tags"]:
            raise ValueError("备份笔记标签未规范化")
    folders = {row["id"]: row for row in decoded["note_folders"]}
    validate_tree(list(folders.values()))
    for row in folders.values():
        if folder_name(row["name"]) != row["name"] or row["revision"] < 1:
            raise ValueError("备份文件夹名称或版本不正确")
    for row in decoded["notes"]:
        if (
            row["folder_id"]
            and folders[row["folder_id"]]["course_id"] != row["course_id"]
        ):
            raise ValueError("备份笔记文件夹跨课程")
    return decoded


def apply(db, decoded):
    pending = list(decoded["note_folders"])
    added = set()
    while pending:
        ready = [
            row
            for row in pending
            if row["parent_id"] is None or row["parent_id"] in added
        ]
        if not ready:
            raise ValueError("备份文件夹层级无效")
        for row in ready:
            db.add(NoteFolder(**row))
            added.add(row["id"])
            pending.remove(row)
        db.flush()
    contract.apply(db, MODELS[1:], decoded)
