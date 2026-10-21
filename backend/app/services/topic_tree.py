"""Course-owned hierarchy stored in Topic metadata; historical snapshots stay immutable."""

import json
from fastapi import HTTPException
from sqlalchemy import select, func
from ..models import Topic


def active_clause():
    return (
        func.coalesce(func.json_extract(Topic.sources_json, "$.deleted_by_user"), 0)
        == 0
    )


def is_deleted(row):
    return bool(json.loads(row.sources_json).get("deleted_by_user"))


def parent_id(row):
    return json.loads(row.sources_json).get("hierarchy", {}).get("parent_id")


def write_parent(row, value):
    data = json.loads(row.sources_json)
    data["hierarchy"] = {"parent_id": value}
    row.sources_json = json.dumps(data, ensure_ascii=False)


def rows(db, user_id, course_id):
    return db.scalars(
        select(Topic).where(
            active_clause(),
            Topic.user_id == user_id,
            Topic.course_id == course_id,
            Topic.merged_into_id.is_(None),
        )
    ).all()


def validate_links(links):
    if any(
        value is not None and not isinstance(value, str) for value in links.values()
    ):
        raise ValueError("标签父级必须是ID或空")
    for start in links:
        seen = set()
        current = start
        while current is not None:
            if current not in links or current in seen:
                raise ValueError("标签父级不可用或存在循环")
            seen.add(current)
            if len(seen) > 6:
                raise ValueError("知识标签最多6级")
            current = links[current]


def check_parent(db, user_id, course_id, node_id, target):
    links = {t.id: parent_id(t) for t in rows(db, user_id, course_id)}
    if target and target not in links:
        raise HTTPException(404, "父标签不存在或不属于当前课程")
    links[node_id] = target
    try:
        validate_links(links)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


def expand(db, user_id, course_id, ids):
    selected = set(str(i) for i in ids)
    topics = rows(db, user_id, course_id)
    for _ in range(6):
        selected.update(t.id for t in topics if parent_id(t) in selected)
    return selected
