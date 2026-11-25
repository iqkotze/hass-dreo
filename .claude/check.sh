#!/usr/bin/env bash
# Gate before pushing: ruff, format, complexity ratchet, full pytest run (same checks as CI).
# Usage: .claude/check.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if ! .venv/bin/python -c "import pytest, homeassistant" 2>/dev/null; then
  [[ -x .venv/bin/python ]] || uv venv -q .venv
  uv pip install -q -p .venv -r requirements.txt -r requirements.test.txt
fi

uvx -q ruff check .
uvx -q ruff format --check .
# Complexity ratchet: fails only for new functions above 20 or known ones that got worse (complexipy-snapshot.json).
uvx -q complexipy -q
.venv/bin/python -m pytest -q -p no:cacheprovider --tb=line
