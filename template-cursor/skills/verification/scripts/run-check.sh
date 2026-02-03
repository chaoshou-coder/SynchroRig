#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO_ROOT"

echo "==> Running: make check"
if command -v make >/dev/null 2>&1; then
  make check
  exit 0
fi

echo "==> make not found; running Python commands directly"
python -m ruff format .
python -m ruff check . --fix
python -m ruff check .
python -m pytest -vv --tb=short tests/

echo "All checks passed!"

