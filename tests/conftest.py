"""Shared paths for tests. Use CURSOR_ROOT so CI (no .cursor) uses template-cursor."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Prefer .cursor (local); fall back to template-cursor (CI / fresh clone)
CURSOR_ROOT = ROOT / ".cursor" if (ROOT / ".cursor").exists() else ROOT / "template-cursor"
