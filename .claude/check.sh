#!/usr/bin/env bash
# Gate before pushing: ruff, format and complexity of changed files, full pytest run.
# Usage: .claude/check.sh [<base>]   (default base: origin/main)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
base="${1:-origin/main}"

if ! .venv/bin/python -c "import pytest, homeassistant" 2>/dev/null; then
  [[ -x .venv/bin/python ]] || uv venv -q .venv
  uv pip install -q -p .venv -r requirements.txt -r requirements.test.txt
fi

mapfile -t changed < <(git diff --name-only --diff-filter=d "$base" -- '*.py'; git ls-files --others --exclude-standard -- '*.py')

uvx -q ruff check .
if ((${#changed[@]})); then
  uvx -q ruff format --check "${changed[@]}"
  src=()
  for f in "${changed[@]}"; do [[ $f == custom_components/* ]] && src+=("$f"); done
  if ((${#src[@]})); then uvx -q complexipy "${src[@]}" -q; fi
fi
.venv/bin/python -m pytest -q -p no:cacheprovider --tb=line
