"""A PPTX preview page must correspond to the original slide ordinal."""

from pathlib import Path
import zipfile
from xml.etree import ElementTree


def pptx_slide_count(source: Path) -> int:
    with zipfile.ZipFile(source) as package:
        entry = package.getinfo("ppt/presentation.xml")
        if entry.file_size > 4 * 1024 * 1024:
            raise ValueError("PPTX幻灯片目录超出预算")
        root = ElementTree.fromstring(package.read(entry))
    return len(
        root.findall(
            "{http://schemas.openxmlformats.org/presentationml/2006/main}sldIdLst/{http://schemas.openxmlformats.org/presentationml/2006/main}sldId"
        )
    )


def check_preview_mapping(source: Path, preview: Path) -> None:
    if source.suffix.lower() != ".pptx":
        return
    from pypdf import PdfReader

    try:
        expected = pptx_slide_count(source)
        actual = len(PdfReader(str(preview)).pages)
    except Exception as exc:
        raise ValueError("无法核对课件预览页号，请重新生成预览") from exc
    if expected != actual:
        raise ValueError(
            "旧预览未完整保留幻灯片（含隐藏页），请重新生成预览以保持页号一致"
        )
