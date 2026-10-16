"""Shared serialization contract; callers supply only their own module models."""

from datetime import datetime, timezone
import json
from uuid import UUID
from sqlalchemy import (
    select,
    func,
    cast,
    LargeBinary,
    String,
    DateTime,
    Integer,
    Boolean,
    JSON,
)

MAX_METADATA = 16 * 1024 * 1024
MAX_ROWS = 100000


def serialize(db, user_id, models, filters=None):
    tables = {}
    for model in models:
        query = select(model).where(model.user_id == user_id)
        if filters and model.__tablename__ in filters:
            query = query.where(filters[model.__tablename__])
        count = db.scalar(
            query.with_only_columns(func.count(), maintain_column_froms=True)
        )
        if count > MAX_ROWS:
            raise ValueError("备份业务行超过预算")
        for column in model.__table__.columns:
            if isinstance(column.type, (String, JSON)):
                size = (
                    db.scalar(
                        query.with_only_columns(
                            func.sum(func.length(cast(column, LargeBinary))),
                            maintain_column_froms=True,
                        )
                    )
                    or 0
                )
                if size > MAX_METADATA:
                    raise ValueError("备份文本超过16MiB元数据预算")
        rows = []
        for row in db.scalars(query.order_by(model.id)):
            item = {}
            for column in model.__table__.columns:
                value = getattr(row, column.name)
                item[column.name] = (
                    value.astimezone(timezone.utc).isoformat()
                    if isinstance(value, datetime) and value.tzinfo
                    else value.replace(tzinfo=timezone.utc).isoformat()
                    if isinstance(value, datetime)
                    else value
                )
            rows.append(item)
        tables[model.__tablename__] = rows
    return tables


def assert_empty(db, user_id, models, filters=None):
    for model in models:
        query = select(model.id).where(model.user_id == user_id)
        if filters and model.__tablename__ in filters:
            query = query.where(filters[model.__tablename__])
        if db.scalar(query.limit(1)):
            raise ValueError("仅允许向没有任何业务数据的空账户恢复")


def validate(db, user_id, source_user, models, tables, all_ids, file_paths):
    """Validate before insertion; no foreign-module table reads."""
    result = {}
    for model in models:
        name = model.__tablename__
        rows = tables.get(name)
        if not isinstance(rows, list):
            raise ValueError("备份缺少模块表或结构不正确")
        columns = {column.name: column for column in model.__table__.columns}
        decoded = []
        for item in rows:
            if (
                not isinstance(item, dict)
                or set(item) != set(columns)
                or item.get("user_id") != source_user
            ):
                raise ValueError("备份字段或用户归属不正确")
            row = dict(item)
            for field, column in columns.items():
                value = row[field]
                if value is None:
                    if not column.nullable:
                        raise ValueError("备份必填字段为空")
                    continue
                field_type = (
                    column.type.impl if hasattr(column.type, "impl") else column.type
                )
                if isinstance(field_type, DateTime):
                    if not isinstance(value, str):
                        raise ValueError("备份时间类型不正确")
                    value = datetime.fromisoformat(value)
                    if value.tzinfo is None:
                        raise ValueError("备份时间必须带时区")
                    row[field] = value.astimezone(timezone.utc)
                elif isinstance(field_type, Boolean):
                    if type(value) is not bool:
                        raise ValueError("备份布尔类型不正确")
                elif isinstance(field_type, Integer):
                    if type(value) is not int:
                        raise ValueError("备份整数类型不正确")
                elif isinstance(field_type, String):
                    if not isinstance(value, str) or (
                        field_type.length and len(value) > field_type.length
                    ):
                        raise ValueError("备份文本类型或长度不正确")
                    if field.endswith("_json"):
                        parsed = strict_json(value.encode())
                        expected = (
                            list
                            if field in {"aliases_json", "questions_json"}
                            else dict
                        )
                        if not isinstance(parsed, expected):
                            raise ValueError("备份业务JSON结构不正确")
                elif isinstance(field_type, JSON):
                    if not isinstance(value, (dict, list)):
                        raise ValueError("备份JSON字段不正确")
                if field == "id" or column.foreign_keys:
                    if str(UUID(str(value))) != value:
                        raise ValueError("备份UUID必须使用规范小写格式")
                if field in {"source_path", "storage_path", "preview_path", "zip_path"}:
                    if value:
                        if value not in file_paths:
                            raise ValueError("备份引用不存在的文件")
                        row[field] = str(file_paths[value])
                    else:
                        row[field] = None if column.nullable else ""
                for foreign in column.foreign_keys:
                    table = foreign.column.table.name
                    if table == "users":
                        if value != source_user:
                            raise ValueError("备份含其他用户关系")
                        row[field] = user_id
                    elif value not in all_ids.get(table, set()):
                        raise ValueError("备份含缺失的关联对象")
            row["user_id"] = user_id
            if db.get(model, row["id"]) is not None:
                raise ValueError(
                    "备份UUID与当前数据库对象冲突，请恢复到新数据库的空账户"
                )
            decoded.append(row)
        result[name] = decoded
    return result


def apply(db, models, decoded):
    for model in models:
        for item in decoded[model.__tablename__]:
            db.add(model(**item))
        db.flush()


def ids(tables):
    result = {}
    total = 0
    for name, rows in tables.items():
        if not isinstance(rows, list):
            raise ValueError("备份表结构不正确")
        values = [item.get("id") for item in rows if isinstance(item, dict)]
        if len(values) != len(rows) or len(set(values)) != len(rows):
            raise ValueError("备份对象ID缺失或重复")
        for value in values:
            if not isinstance(value, str):
                raise ValueError("备份对象ID类型不正确")
            if str(UUID(value)) != value:
                raise ValueError("备份UUID格式不规范")
        result[name] = set(values)
        total += len(values)
    if total > MAX_ROWS:
        raise ValueError("备份业务行超过100000预算")
    return result


def strict_json(data):
    if len(data) > MAX_METADATA:
        raise ValueError("备份清单超过16MiB预算")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("备份JSON含重复字段")
            result[key] = value
        return result

    return json.loads(
        data,
        object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("非法JSON数值")),
    )
