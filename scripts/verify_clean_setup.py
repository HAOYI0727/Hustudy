"""Rebuild a disposable source copy with locked dependencies; no user data/secrets."""

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python", required=True, help="Python 3.12 executable for fresh venv"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    interpreter = str(Path(args.python).resolve())
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("HUSTUDY_", "VITE_", "PYTHONPATH"))
    }
    results = []
    with tempfile.TemporaryDirectory(prefix="hustudy-clean-") as scratch:
        target = Path(scratch) / "source"
        target.mkdir()
        ignore = shutil.ignore_patterns(
            "node_modules",
            "dist",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            "*.pyc",
            "test-results",
            "playwright-report",
            "*.tsbuildinfo",
        )
        for directory in ("backend", "frontend", "scripts", "fixtures"):
            shutil.copytree(root / directory, target / directory, ignore=ignore)
        shutil.copy2(root / ".env.example", target / ".env.example")
        env.update(
            {
                "PYTHON_BIN": interpreter,
                "PIP_CACHE_DIR": str(Path(scratch) / "pip-cache"),
                "npm_config_cache": str(Path(scratch) / "npm-cache"),
            }
        )
        for command in (["bash", "scripts/setup.sh"], ["bash", "scripts/check.sh"]):
            started = time.perf_counter()
            # Output is synthetic test logs; configure_auth never prints generated secrets.
            result = subprocess.run(command, cwd=target, env=env)
            results.append(
                {
                    "command": command,
                    "exit_code": result.returncode,
                    "seconds": round(time.perf_counter() - started, 3),
                }
            )
            if result.returncode:
                break
        report = {
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "host": platform.platform(),
            "python_requested": Path(interpreter).name,
            "commands": results,
            "passed": len(results) == 2 and all(r["exit_code"] == 0 for r in results),
            "isolation": "Fresh temporary source copy, new Python venv and npm ci. Only backend/frontend/scripts/fixtures and .env.example copied; no .git/.env/data/user uploads/existing venv/node_modules. Temporary tree removed on exit.",
            "limits": "Same host and already available system tools/Python; not a separate machine/OS. No live browsers or external model calls.",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(
            "Clean-source report:",
            args.output,
            "PASS" if report["passed"] else "FAIL",
            flush=True,
        )
        return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
