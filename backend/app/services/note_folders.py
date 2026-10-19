"""Owned folder tree, bounded traversal and portable export names."""

from fastapi import HTTPException
from sqlalchemy import select, update
from ..models import NoteFolder, User
from .courses import owned_course
from .note_export_names import allocate_names, safe_name

MAX_DEPTH = 6
MAX_FOLDERS = 500


def lock_owner(db, user_id):
    db.execute(update(User).where(User.id == user_id).values(id=User.id))
    db.expire_all()


def owned_folder(db, user_id, folder_id, course_id=None):
    row = db.scalar(
        select(NoteFolder).where(
            NoteFolder.id == folder_id, NoteFolder.user_id == user_id
        )
    )
    if row is None or (course_id is not None and row.course_id != course_id):
        raise HTTPException(404, "文件夹不存在或不在当前课程")
    owned_course(db, user_id, row.course_id)
    return row


def check_placement(db, user_id, folder_id, course_id):
    if folder_id is not None:
        row = owned_folder(db, user_id, folder_id)
        if row.course_id != course_id:
            raise HTTPException(422, "笔记和文件夹必须属于同一课程")


def validate_tree(rows):
    """Also used on decoded backup rows before any restore writes."""
    by_id = {row["id"]: row for row in rows}
    siblings, counts = set(), {}
    for row in rows:
        key = (row["course_id"], row["parent_id"], row["name"].casefold())
        if key in siblings:
            raise ValueError("同级文件夹名称重复")
        siblings.add(key)
        counts[row["course_id"]] = counts.get(row["course_id"], 0) + 1
        if counts[row["course_id"]] > MAX_FOLDERS:
            raise ValueError("每个课程最多500个文件夹")
        current, seen = row, set()
        while current:
            if current["id"] in seen:
                raise ValueError("文件夹不能移动到自身或子文件夹")
            seen.add(current["id"])
            if len(seen) > MAX_DEPTH:
                raise ValueError("文件夹最多支持6级")
            parent = current["parent_id"]
            if parent is None:
                break
            current = by_id.get(parent)
            if current is None or current["course_id"] != row["course_id"]:
                raise ValueError("父文件夹缺失或跨课程")


def tree_rows(db, user_id, course_id):
    return [
        {k: getattr(row, k) for k in ("id", "name", "parent_id", "course_id")}
        for row in db.scalars(
            select(NoteFolder).where(
                NoteFolder.user_id == user_id, NoteFolder.course_id == course_id
            )
        )
    ]


def export_paths(db, user_id, notes):
    folders = {}
    pending = {note.folder_id for note in notes if note.folder_id}
    for _ in range(MAX_DEPTH):
        if not pending:
            break
        rows = db.scalars(
            select(NoteFolder).where(
                NoteFolder.user_id == user_id, NoteFolder.id.in_(pending)
            )
        ).all()
        folders.update({row.id: row for row in rows})
        pending = {
            row.parent_id
            for row in rows
            if row.parent_id and row.parent_id not in folders
        }
    needed = set()
    for note in notes:
        parent = note.folder_id
        seen = set()
        while parent:
            if parent in seen or len(seen) >= MAX_DEPTH:
                raise ValueError("笔记文件夹层级不正确")
            seen.add(parent)
            folder = folders.get(parent)
            if folder is None or folder.course_id != note.course_id:
                raise ValueError("笔记文件夹归属不正确")
            needed.add(parent)
            parent = folder.parent_id
    paths = {}

    def allocate(parent, prefix):
        # Reserve images at the root; files and folders share a name namespace.
        entries = [("reserved-images", "images", "")] if parent is None else []
        entries += [
            ("folder:" + key, safe_name(folders[key].name, "文件夹", 24), "")
            for key in sorted(needed)
            if folders[key].parent_id == parent
        ]
        entries += [
            ("note:" + n.id, n.title, ".md")
            for n in sorted(notes, key=lambda n: n.id)
            if n.folder_id == parent
        ]
        names = allocate_names(entries, fallback="未命名笔记")
        for key, name in names.items():
            if key == "reserved-images":
                continue
            kind, identity = key.split(":", 1)
            if kind == "folder":
                allocate(identity, prefix + name + "/")
            else:
                paths[identity] = prefix + name

    allocate(None, "")
    return paths
