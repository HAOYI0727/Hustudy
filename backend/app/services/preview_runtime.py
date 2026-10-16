"""Local Office conversion capability; never returns filesystem paths to clients."""

import os
from pathlib import Path
import shutil

from ..core.config import get_settings

INSTALL_URL = "https://www.libreoffice.org/download/"


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
    available = bool(office_executable())
    return {
        "native_pdf": True,
        "office_available": available,
        "office_status": "available"
        if available
        else "configured_unavailable"
        if get_settings().libreoffice_path.strip()
        else "not_installed",
        "message": "已检测到本机Office转换器；实际结果以预览任务为准。"
        if available
        else "Office转换器路径不可执行，请检查后端HUSTUDY_LIBREOFFICE_PATH配置。"
        if get_settings().libreoffice_path.strip()
        else "未安装LibreOffice：PPTX/DOCX需先转换成PDF，原始PDF可直接预览。",
        "installation_url": INSTALL_URL,
    }
