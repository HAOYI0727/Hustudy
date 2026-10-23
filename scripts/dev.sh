#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=backend
export HUSTUDY_WORKER_AUTOSTART="${HUSTUDY_WORKER_AUTOSTART:-true}"
exec .venv/bin/python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend/app
