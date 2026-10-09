#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import ast
from pathlib import Path
files = list(Path("backend").rglob("*.py"))
for path in files:
    ast.parse(path.read_text(), filename=str(path))
print(f"Python AST syntax check passed: {len(files)} files")
PY
if command -v ruff >/dev/null 2>&1; then
  ruff check backend/app backend/tests
else
  echo "ruff is not installed; skipped lint (install backend/requirements.txt first)"
fi
