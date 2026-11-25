# CLAUDE.md

Unofficial Home Assistant integration for Dreo devices (`custom_components/dreo/`, embedded PyDreo library in `pydreo/`).
Coding standards, structure and patterns: [.github/copilot-instructions.md](.github/copilot-instructions.md) (read only the section you need).

## Commands
- Gate before every push: `.claude/check.sh` (ruff, ruff format + complexipy on changed files, full pytest). Creates `.venv` on first run.
- Single tests: `.venv/bin/python -m pytest -q tests/dreo/test_switch.py`
- Complexity: `uvx complexipy` (limit 20 in `pyproject.toml`; existing functions above it are known debt, new or changed code must stay below).

## Rules
- Code, comments, commit messages English. New entities get a `translation_key` in `strings.json` and all `translations/*.json`.
- Heater changes: check `HEATERS.md` and the device definitions in `pydreo/models.py` (device ranges are in °F).
- Behaviour changes need a test; integration tests in `tests/dreo/integrationtests/` assert the entity lists per device (update them when adding entities).
- Diffs: `git diff --stat` first, then `git diff -U1 -- <file>`; never a bare `git diff` or `git log -p`.

## Working mode
- Main session briefs, checks, commits. Small changes (≤ ~3 files) directly.
- [implementer](.claude/agents/implementer.md) (Sonnet): larger features/refactors, max ~5 files / ~4 criteria per brief.
- [reviewer](.claude/agents/reviewer.md) (Sonnet): independent check of a branch against numbered criteria; reports only.
- [helper](.claude/agents/helper.md) (Haiku): fully specified mechanical jobs, fact finding, test runs.
- [docs](.claude/agents/docs.md) (Haiku): README, SUPPORTED_MODELS, DEVICE_OWNERS, HEATERS, RELEASE notes.
- Brief = goal, branch, files, numbered criteria K1…, commit attribution lines. Continue a stopped agent with SendMessage instead of starting a new one.
