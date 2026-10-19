"""Developer verifier for legacy manifest-based M3 packages only.

Simple user exports have no manifest and are validated inside the application.
"""

import hashlib
import json
from pathlib import PurePosixPath
import sys
import zipfile


def verify(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(names) > 15002 or len(names) != len(set(names)):
            raise ValueError("包内成员数量或重复路径不正确")
        if sum(item.file_size for item in infos) > 256 * 1024 * 1024 + 4096:
            raise ValueError("解压内容超过预算")
        for name in names:
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts or "\\" in name or ":" in name:
                raise ValueError("包内含不安全路径")
        if archive.getinfo("manifest.json").file_size > 16 * 1024 * 1024:
            raise ValueError("清单超过预算")
        manifest = json.loads(archive.read("manifest.json"))
        if (
            manifest["format"] != "hustudy-note-package"
            or manifest["schema_version"] != 1
        ):
            raise ValueError("不支持的笔记包格式")
        files = {entry["path"]: entry for entry in manifest["files"]}
        if len(files) != len(manifest["files"]) or set(names) != {
            *files,
            "manifest.json",
            "README.md",
        }:
            raise ValueError("清单与包内文件不一致")
        for name, entry in files.items():
            digest = hashlib.sha256()
            size = 0
            with archive.open(name) as stream:
                while block := stream.read(65536):
                    digest.update(block)
                    size += len(block)
            if size != entry["size_bytes"] or digest.hexdigest() != entry["sha256"]:
                raise ValueError("文件hash或大小不一致：" + name)
        for note in manifest["notes"]:
            for kind in ("content", "markdown"):
                if files[note[kind + "_file"]]["sha256"] != note[kind + "_sha256"]:
                    raise ValueError("笔记正文hash与文件清单不一致")
        for asset in manifest["assets"]:
            if files[asset["file"]]["sha256"] != asset["sha256"]:
                raise ValueError("图片hash与文件清单不一致")
        for citation in manifest["citations"]:
            if (
                hashlib.sha256(citation["quote"].encode("utf-8")).hexdigest()
                != citation["quote_hash"]
            ):
                raise ValueError("来源摘录hash不一致")
        return len(manifest["notes"]), len(manifest["assets"]), len(files)


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("用法：python scripts/verify_note_package.py 笔记包.zip")
        notes, assets, files = verify(sys.argv[1])
        print(
            f"校验通过：{notes}篇笔记，{assets}张图片，{files}个文件；正文/图片/来源hash一致。"
        )
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as error:
        print(f"校验失败：{error}", file=sys.stderr)
        sys.exit(1)
