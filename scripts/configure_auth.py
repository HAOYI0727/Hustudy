"""Initialize an ignored local signing secret without exposing or rotating valid keys."""

import os
import io
from pathlib import Path
import re
import secrets
import tempfile

from dotenv import dotenv_values


def configure(path: Path) -> bool:
    if path.is_symlink():
        raise ValueError("拒绝写入符号链接配置")
    content = path.read_text() if path.exists() else ""
    current = dotenv_values(stream=io.StringIO(content)).get("HUSTUDY_JWT_SECRET")
    if current and current != "change-this-in-development":
        if len(current) < 32:
            raise ValueError("已有自定义JWT密钥不足32字符，请在后端配置中设置强密钥")
        path.chmod(0o600)
        return False
    lines = [
        line
        for line in content.splitlines()
        if not re.match(r"\s*(?:export\s+)?HUSTUDY_JWT_SECRET\s*=", line)
    ]
    lines.append("HUSTUDY_JWT_SECRET=" + secrets.token_urlsafe(48))
    descriptor, name = tempfile.mkstemp(prefix=".env.tmp_", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as output:
            output.write("\n".join(lines) + "\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
    return True


if __name__ == "__main__":
    try:
        changed = configure(Path(__file__).resolve().parents[1] / ".env")
        print("已初始化本地JWT密钥（未显示）" if changed else "保留已有JWT密钥")
    except ValueError as error:
        raise SystemExit(str(error)) from error
