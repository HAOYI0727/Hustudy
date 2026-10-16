#!/usr/bin/env bash
# Shared platform + M1 acceptance. Every test uses disposable data.
set -euo pipefail
cd "$(dirname "$0")/.."
ACCEPTANCE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hustudy-acceptance.XXXXXX")"
echo "验收日志目录：$ACCEPTANCE_DIR"
bash scripts/check.sh > "$ACCEPTANCE_DIR/check.log" 2>&1
npm run test:e2e --prefix frontend > "$ACCEPTANCE_DIR/e2e.log" 2>&1
.venv/bin/python scripts/verify_capacity.py --output "$ACCEPTANCE_DIR/capacity.json" > "$ACCEPTANCE_DIR/capacity.log" 2>&1
echo "共享检查、双引擎闭环与容量验收通过，详情见 $ACCEPTANCE_DIR"
