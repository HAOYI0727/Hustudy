"""Image metadata and bounded directory search, without interpreting pixels."""

from fastapi import HTTPException
from sqlalchemy import select, func, or_, exists, update
from ..models import Asset
from ..models.base import utc_now
from ..repositories.assets import available_assets, active_asset
from ..schemas.assets import AssetPageResponse
from ..schemas.notes import AssetResponse


def asset_page(db, user_id, course_id, q, tag, origin, sort, offset, limit):
    scope = available_assets(user_id, course_id)
    labels = func.json_each(Asset.tags).table_valued("value")
    filters = [scope]
    if q.strip():
        needle = q.strip().lower()
        filters.append(
            or_(
                *(
                    func.instr(func.lower(field), needle) > 0
                    for field in (Asset.name, Asset.original_filename, Asset.alt)
                ),
                exists(
                    select(1)
                    .select_from(labels)
                    .where(func.instr(func.lower(labels.c.value), needle) > 0)
                ),
            )
        )
    if tag is not None:
        filters.append(
            exists(select(1).select_from(labels).where(labels.c.value == tag))
        )
    if origin == "captured":
        filters.append(Asset.source_locator_type.is_not(None))
    elif origin == "external":
        filters.append(Asset.source_locator_type.is_(None))
    order = {
        "newest": Asset.created_at.desc(),
        "oldest": Asset.created_at.asc(),
        "updated": Asset.updated_at.desc(),
        "name": Asset.name.asc(),
    }[sort]
    rows = db.scalars(
        select(Asset)
        .where(*filters)
        .order_by(order, Asset.id)
        .offset(offset)
        .limit(limit)
    ).all()
    total = db.scalar(select(func.count()).select_from(Asset).where(*filters))
    tags = db.scalars(
        select(labels.c.value)
        .select_from(Asset)
        .join(labels, func.json_valid(Asset.tags))
        .where(scope)
        .distinct()
        .order_by(labels.c.value)
        .limit(200)
    ).all()
    return AssetPageResponse(
        items=[AssetResponse.model_validate(row, from_attributes=True) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
        tags=tags,
    )


def organize_asset(db, user_id, asset_id, payload):
    active_asset(db, asset_id, user_id)
    values = payload.model_dump(exclude_unset=True, exclude={"revision"})
    changed = db.execute(
        update(Asset)
        .where(
            Asset.id == asset_id,
            available_assets(user_id),
            Asset.revision == payload.revision,
        )
        .values(**values, revision=Asset.revision + 1, updated_at=utc_now())
        .execution_options(synchronize_session=False)
    )
    if changed.rowcount != 1:
        db.rollback()
        row = active_asset(db, asset_id, user_id)
        raise HTTPException(
            409,
            {
                "message": "图片已在其他窗口修改，本地输入已保留",
                "server_asset": AssetResponse.model_validate(
                    row, from_attributes=True
                ).model_dump(mode="json"),
            },
        )
    db.commit()
    db.expire_all()
    return AssetResponse.model_validate(
        active_asset(db, asset_id, user_id), from_attributes=True
    )
