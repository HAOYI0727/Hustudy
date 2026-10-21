"""M4 image contract. Access to pixels always passes M1 authorization."""

import math
from fastapi import HTTPException
from ..repositories.assets import active_asset


def check_images(db, user_id, course_id, images):
    if not isinstance(images, list) or len(images) > 8:
        raise HTTPException(422, "每题最多8张插图")
    clean = []
    for image in images:
        if not isinstance(image, dict) or set(image) - {"asset_id", "box", "alt"}:
            raise HTTPException(422, "插图结构不正确")
        asset = active_asset(db, image.get("asset_id"), user_id)
        if asset.course_id != course_id:
            raise HTTPException(404, "图片不属于本课程")
        box = image.get("box", [0, 0, 1, 1])
        if (
            not isinstance(box, list)
            or len(box) != 4
            or any(type(v) not in (float, int) or not math.isfinite(v) for v in box)
        ):
            raise HTTPException(422, "裁剪区域应为四个有限数字")
        x, y, w, h = box
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1.000001 or y + h > 1.000001:
            raise HTTPException(422, "裁剪区域应位于原图内，且不能为空")
        alt = image.get("alt", "题目插图")
        if not isinstance(alt, str) or len(alt) > 500:
            raise HTTPException(422, "插图说明最多500字")
        clean.append({"asset_id": asset.id, "box": box, "alt": alt})
    return clean
