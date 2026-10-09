#!/usr/bin/env bash
set -euo pipefail
python3 -m uvicorn app.main:app --app-dir backend --reload
