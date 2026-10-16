#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/ruff check backend/app backend/tests backend/migrations
PYTHONPATH=backend .venv/bin/python -m pytest -q
PYTHONPATH=backend .venv/bin/python scripts/verify_migrations.py
node scripts/verify_markdown.mjs
node scripts/verify_pdf.mjs
npm run test --prefix frontend
npm run build --prefix frontend
