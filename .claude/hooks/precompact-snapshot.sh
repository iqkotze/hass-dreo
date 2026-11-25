#!/usr/bin/env bash
# Saves the transcript and the git status of this repo before a compact.
# Called by the PreCompact hook in .claude/settings.json with the hook JSON on stdin.
# Manual run: echo '{"trigger":"manual"}' | .claude/hooks/precompact-snapshot.sh
# Output: ~/.claude/compact-snapshots/<repo>/<timestamp>-<trigger>/, the newest 10 are kept.
set -euo pipefail

input="$(cat)"
field() { python3 -c 'import json, sys; print(json.loads(sys.argv[1]).get(sys.argv[2]) or "")' "$input" "$1"; }
transcript="$(field transcript_path)"
trigger="$(field trigger)"
repo="$(git -C "${CLAUDE_PROJECT_DIR:-$(field cwd)}" rev-parse --show-toplevel)"
base="$HOME/.claude/compact-snapshots/$(basename "$repo")"
dir="$base/$(date +%Y-%m-%d_%H%M%S)-${trigger:-unknown}"
mkdir -p "$dir"

if [[ -n "$transcript" && -f "$transcript" ]]; then
  cp "$transcript" "$dir/transcript.jsonl"
fi

{
  echo "## $(basename "$repo") ($(git -C "$repo" branch --show-current))"
  git -C "$repo" status --short
  git -C "$repo" log --oneline -3 2>/dev/null || echo "(no commits)"
} >"$dir/git-status.md"

ls -1dt "$base"/*/ | tail -n +11 | xargs -r rm -rf
echo "{\"systemMessage\": \"Snapshot saved to $dir\"}"
