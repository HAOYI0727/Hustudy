#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=backend
.venv/bin/python -m app.workers.materials &
WORKER_PID=$!
trap 'kill "$WORKER_PID" 2>/dev/null || true' EXIT INT TERM
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload
