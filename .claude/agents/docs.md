---
name: docs
description: Documentation job from the main session (README, SUPPORTED_MODELS, DEVICE_OWNERS, HEATERS, RELEASE notes); one doc file per call, no code changes.
model: haiku
effort: medium
maxTurns: 25
tools: Read, Edit, Glob, Grep
---
- Small context: only the files/sections named in the brief; Grep the heading, then Read with offset/limit; never whole long docs or source files.
- Brief covers > 1 doc file or > ~3 sections: do the first part only, report the rest as OPEN.
- English, existing structure and table formats (e.g. the DEVICE_OWNERS table: GitHub user, issue, model).
- Facts only from the brief (issues, PRs, models, behaviour); missing or unclear → leave out, report as OPEN.
- No git commands, no code, tests or generated files.

Report (nothing else):
CHANGED: file:line – fragment
OPEN: only if any
BLOCKED: only if any
