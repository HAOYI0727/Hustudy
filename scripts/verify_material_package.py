"""Verify a course ZIP without extraction or app/database startup."""

import hashlib
import json
from pathlib import PurePosixPath
import sys
import zipfile


def verify_package(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [entry.filename for entry in infos]
        if len(names) != len(set(names)) or len(names) > 70000:
            raise ValueError("重复成员或成员数量超出预算")
        for entry in infos:
            member = PurePosixPath(entry.filename)
            if (
                member.is_absolute()
                or ".." in member.parts
                or "\\" in entry.filename
                or entry.is_dir()
            ):
                raise ValueError("成员路径不安全")
            if (
                entry.flag_bits & 1
                or (entry.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("不支持加密或符号链接成员")
        if sum(entry.file_size for entry in infos) > 256 * 1024 * 1024 + 65536:
            raise ValueError("展开内容超过预算")
        if archive.getinfo("manifest.json").file_size > 16 * 1024 * 1024:
            raise ValueError("元数据超过预算")
        manifest = json.loads(archive.read("manifest.json"))
        if (
            manifest.get("format") != "hustudy-material-package"
            or manifest.get("schema_version") != 1
        ):
            raise ValueError("资料包格式/版本不支持")
        expected = {"manifest.json", "README.md"}
        for item in manifest["files"]:
            if item["path"] in expected:
                raise ValueError("重复清单成员")
            expected.add(item["path"])
            info = archive.getinfo(item["path"])
            digest = hashlib.sha256()
            with archive.open(info) as stream:
                while block := stream.read(65536):
                    digest.update(block)
            if (
                info.file_size != item["size_bytes"]
                or digest.hexdigest() != item["sha256"]
            ):
                raise ValueError("文件hash/大小不符：" + item["path"])
        if expected != set(names):
            raise ValueError("文件清单与ZIP成员不一致")
        return {
            key: len(manifest[key])
            for key in (
                "documents",
                "versions",
                "chunks",
                "transcripts",
                "assets",
                "files",
            )
        }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "用法：python3 scripts/verify_material_package.py /path/to/package.zip"
        )
    try:
        counts = verify_package(sys.argv[1])
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        raise SystemExit("资料包校验失败：" + str(exc)) from exc
    print(
        "资料包版本/成员/字节/hash校验通过：" + json.dumps(counts, ensure_ascii=False)
    )
