"""Document ingestion helpers used by the synchronous Phase 1 worker.

The parser returns source ordered chunks. Optional format libraries are imported
inside the relevant branch so a missing dependency produces an observable
document failure instead of silently indexing an empty file.
"""

from pathlib import Path
from typing import Dict, List


def _markdown_chunks(text: str) -> List[Dict[str, object]]:
    chunks: List[Dict[str, object]] = []
    start = 0
    current_heading = "文档"
    buffer: List[str] = []

    def flush() -> None:
        nonlocal start, buffer
        body = "\n".join(buffer).strip()
        if body:
            end = start + len(body)
            chunks.append({"locator_type": "heading", "locator_value": current_heading, "text": body, "start_offset": start, "end_offset": end})
            start = end + 1
        buffer = []

    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            flush()
            current_heading = line.lstrip("# ").strip() or "文档"
        else:
            buffer.append(line)
    flush()
    return chunks


def parse_document(path: Path, suffix: str) -> List[Dict[str, object]]:
    suffix = suffix.lower()
    if suffix in {".md", ".markdown", ".txt"}:
        return _markdown_chunks(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("缺少 pypdf 依赖，无法解析 PDF") from exc
        chunks = []
        for page_no, page in enumerate(PdfReader(str(path)).pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                chunks.append({"locator_type": "page", "locator_value": str(page_no), "text": text, "start_offset": 0, "end_offset": len(text)})
        if not chunks:
            raise RuntimeError("PDF 没有可提取文本；扫描件请使用原页查看并人工转录")
        return chunks
    if suffix == ".docx":
        try:
            from docx import Document as WordDocument
        except ImportError as exc:
            raise RuntimeError("缺少 python-docx 依赖，无法解析 DOCX") from exc
        chunks = []
        ordinal = 0
        for block in WordDocument(str(path)).iter_inner_content():
            text = getattr(block, "text", "").strip()
            if not text and hasattr(block, "rows"):
                text = "\n".join(" | ".join(cell.text.strip() for cell in row.cells) for row in block.rows).strip()
            if text:
                ordinal += 1
                chunks.append({"locator_type": "docx_block", "locator_value": str(ordinal), "text": text, "start_offset": 0, "end_offset": len(text)})
        return chunks
    if suffix == ".pptx":
        try:
            from pptx import Presentation
        except ImportError as exc:
            raise RuntimeError("缺少 python-pptx 依赖，无法解析 PPTX") from exc
        chunks = []
        for slide_no, slide in enumerate( Presentation(str(path)).slides, start=1):
            texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    texts.append(shape.text.strip())
            body = "\n".join(texts).strip()
            if body:
                chunks.append({"locator_type": "slide", "locator_value": str(slide_no), "text": body, "start_offset": 0, "end_offset": len(body)})
        return chunks
    raise RuntimeError(f"不支持的文件格式：{suffix}")
