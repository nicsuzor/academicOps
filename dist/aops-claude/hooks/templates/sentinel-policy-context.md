---
name: sentinel-policy-context
title: Sentinel Gate — Context Injection for Blocked Destructive Op
category: template
description: |
  Context injected into agent when sentinel gate blocks a destructive
  operation on a protected user-environment path. Explains what was
  blocked and how to proceed safely.
---

**SENTINEL GATE: Destructive operation on protected path blocked.**

The operation you attempted targets a protected user-environment path
(e.g. `~/.gemini/extensions/`, `~/.claude/plugins/`, `~/.claude/*.json`,
`~/.gemini/settings.json`, `~/.config/gemini/`).

**Why this matters.** These paths contain live extension, plugin, and
configuration files that the agent framework depends on for correct
operation. Accidental deletion or modification can break the working
environment in ways that are difficult to recover from.

**What to do instead.**

1. Investigate BEFORE touching: read the file/directory to confirm it is
   actually broken or obsolete, not just different from what you expected.
2. If you believe the operation is safe, ask the user for explicit approval
   before proceeding.
3. If the operation is genuinely needed (e.g. reinstalling a corrupt
   extension), prefer backup-then-modify over delete-then-recreate.
4. To bypass in a specific session, the user can set `SENTINEL_GATE_MODE=off`
   in the shell environment — this is a conscious opt-out, not a workaround.

**Do not retry the blocked operation without user approval.**
