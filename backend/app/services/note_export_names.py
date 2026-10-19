"""Readable, portable names; stable UUIDs stay in the package manifest."""

from datetime import timezone
import posixpath
import re
import unicodedata
from urllib.parse import quote
from zoneinfo import ZoneInfo


def safe_name(value, fallback="未命名", limit=60):
    value = unicodedata.normalize("NFKC", value or "")
    value = "".join(
        char for char in value if not unicodedata.category(char).startswith("C")
    )
    value = re.sub(r'[<>:"/\\|?*]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")[:limit].rstrip(" .")
    # Leave room for collision counters and extensions on 255-byte filesystems.
    while len(value.encode("utf-8")) > 220:
        value = value[:-1]
    value = value.rstrip(" .")
    if not value:
        value = fallback
    if re.fullmatch(
        r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", value.split(".")[0], re.IGNORECASE
    ):
        value = "_" + value
    return value


def allocate_names(entries, fallback="未命名", limit=60):
    """Input (key,label,extension) is ordered by UUID; collisions use visible counts."""
    result, used = {}, set()
    for key, label, extension in entries:
        base = safe_name(label, fallback, limit)
        name, number = base + extension, 1
        while unicodedata.normalize("NFKC", name).casefold() in used:
            number += 1
            name = f"{base}（{number}）{extension}"
        used.add(unicodedata.normalize("NFKC", name).casefold())
        result[key] = name
    return result


def relative_link(source, target):
    return quote(posixpath.relpath(target, posixpath.dirname(source)), safe="/")


def archive_filename(created_at, zone):
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    local = created_at.astimezone(ZoneInfo(zone))
    stamp = local.strftime("%Y-%m-%d_%H-%M-%S-") + f"{local.microsecond // 1000:03d}"
    return f"Hustudy-笔记知识库-{stamp}.zip"
