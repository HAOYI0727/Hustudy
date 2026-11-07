"""Local Office conversion capability; never returns filesystem paths to clients."""

import os
from pathlib import Path
import shutil

from ..core.config import get_settings

INSTALL_URL = "https://www.libreoffice.org/download/"
# Large lecture decks can legitimately take several minutes to export. Keep
# the preview lease longer than conversion + validation/publication; the core
# lane also recovers expired jobs while the preview lane is still converting.
CONVERSION_TIMEOUT_SECONDS = 600
PREVIEW_LEASE_SECONDS = CONVERSION_TIMEOUT_SECONDS + 60


def office_executable() -> str | None:
    configured = get_settings().libreoffice_path.strip()
    if configured:
        path = Path(configured)
        return (
            str(path)
            if path.is_absolute() and path.is_file() and os.access(path, os.X_OK)
            else None
        )
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if executable:
        return executable
    candidate = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    return (
        str(candidate)
        if candidate.is_file() and os.access(candidate, os.X_OK)
        else None
    )


def preview_capabilities():
    settings = get_settings()
    if not settings.office_compatibility_enabled:
        return {
            "native_pdf": True,
            "office_available": False,
            "office_status": "disabled_by_config",
            "message": "服务器已关闭兼容PDF转换；PPTX/DOCX仍可直接原格式阅读，PDF可直接按页阅读。",
            "installation_url": INSTALL_URL,
        }
    available = bool(office_executable())
    return {
        "native_pdf": True,
        "office_available": available,
        "office_status": "available"
        if available
        else "configured_unavailable"
        if settings.libreoffice_path.strip()
        else "not_installed",
        "message": "已检测到本机Office转换器；实际结果以预览任务为准。"
        if available
        else "Office转换器路径不可执行，请检查后端HUSTUDY_LIBREOFFICE_PATH配置。"
        if settings.libreoffice_path.strip()
        else "未安装LibreOffice：原格式PPTX/DOCX仍可直接阅读，兼容PDF按需功能不可用。",
        "installation_url": INSTALL_URL,
    }
