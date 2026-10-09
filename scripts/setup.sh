#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then PYTHON_BIN="$candidate"; break; fi
  done
fi
if [ -z "$PYTHON_BIN" ]; then echo "未找到 Python 3.11/3.12，请先安装 Python 3.12。" >&2; exit 1; fi
case "$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" in
  3.11|3.12) : ;;
  *) echo "需要 Python 3.11 或 3.12，当前为 $($PYTHON_BIN --version)" >&2; exit 1;;
esac
if [ ! -d .venv ]; then "$PYTHON_BIN" -m venv .venv; fi
.venv/bin/python -m pip install -r backend/requirements.txt
if [ ! -f .env ]; then cp .env.example .env; fi
if [ ! -d frontend/node_modules ]; then npm install --prefix frontend; fi
echo "环境初始化完成。启动后端：.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload"
echo "启动前端：npm run dev --prefix frontend"
