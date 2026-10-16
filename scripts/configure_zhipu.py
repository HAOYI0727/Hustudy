"""Store a user-supplied key locally without command arguments or output."""

import argparse
import getpass
import os
from pathlib import Path
import re
import sys
import tempfile


def configure(root, key):
    if not re.fullmatch(r"[A-Za-z0-9._-]{16,512}", key):
        raise ValueError("API key format is invalid")
    path = root / ".env"
    if path.is_symlink():
        raise ValueError("Refusing a symbolic-link .env")
    content = path.read_text() if path.exists() else (root / ".env.example").read_text()
    updates = {
        "HUSTUDY_LLM_PROVIDER": "zhipu",
        "HUSTUDY_LLM_MODEL": "glm-4.7-flash",
        "HUSTUDY_LLM_ENDPOINT": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "HUSTUDY_ZHIPU_API_KEY": key,
    }
    lines = [
        line for line in content.splitlines() if line.partition("=")[0] not in updates
    ]
    lines.extend(f"{name}={value}" for name, value in updates.items())
    with tempfile.NamedTemporaryFile(
        mode="w", dir=root, prefix=".env.tmp_", delete=False
    ) as stream:
        temp = Path(stream.name)
        try:
            os.chmod(temp, 0o600)
            stream.write("\n".join(lines) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        except Exception:
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdin", action="store_true")
    args = parser.parse_args()
    key = (
        sys.stdin.readline().strip()
        if args.stdin
        else getpass.getpass("Zhipu API key (hidden): ")
    )
    try:
        configure(Path(__file__).resolve().parents[1], key)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    print("Configured backend .env (mode 0600). Restart API and worker to load.")
