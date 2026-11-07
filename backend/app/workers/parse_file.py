"""Isolated parser process; output is only structured source text."""

import json
import sys
from pathlib import Path
from ..services.materials import parse_document

if __name__ == "__main__":
    source, output = map(Path, sys.argv[1:])
    try:
        if not source.is_file():
            raise FileNotFoundError
        chunks = parse_document(source, source.suffix)
        if not chunks:
            raise ValueError("没有可提取的正文；扫描件可使用原页预览")
        if sum(len(chunk["text"]) for chunk in chunks) > 10_000_000:
            raise ValueError("解析正文超过资源预算")
        output.write_text(
            json.dumps({"chunks": chunks}, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        output.write_text(
            json.dumps(
                {"error": "无法读取原件或写入解析结果，请检查文件与存储状态"},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception as error:
        message = str(error)
        safe_messages = (
            "没有可提取的正文；扫描件可使用原页预览",
            "解析正文超过资源预算",
            "PDF 没有可提取文本；扫描件请使用原页查看并人工转录",
            "缺少 pypdf 依赖，无法解析 PDF",
            "缺少 python-docx 依赖，无法解析 DOCX",
            "缺少 python-pptx 依赖，无法解析 PPTX",
        )
        output.write_text(
            json.dumps(
                {
                    "error": message
                    if message in safe_messages
                    else "正文解析失败，请核对原件是否损坏或加密"
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
