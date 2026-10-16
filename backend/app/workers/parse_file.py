"""Isolated parser process; output is only structured source text."""

import json
import sys
from pathlib import Path
from ..services.materials import parse_document

if __name__ == "__main__":
    source, output = map(Path, sys.argv[1:])
    try:
        chunks = parse_document(source, source.suffix)
        if not chunks:
            raise ValueError("没有可提取的正文；扫描件可使用原页预览")
        if sum(len(chunk["text"]) for chunk in chunks) > 10_000_000:
            raise ValueError("解析正文超过资源预算")
        output.write_text(
            json.dumps({"chunks": chunks}, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as error:
        output.write_text(
            json.dumps({"error": str(error)[:1000]}, ensure_ascii=False),
            encoding="utf-8",
        )
