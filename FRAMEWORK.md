---
name: framework
title: Framework Paths and Configuration
type: reference
description: Session-resolved paths and environment configuration. Injected at session start.
permalink: framework-paths
tags: [framework, paths, configuration]
---

# Framework Paths and Configuration

**Before using Read, Glob, Grep, or Write tools**: Check this path table FIRST.
**If you get "Error reading file"**: You guessed wrong. Return here, use correct path.
**DO NOT fabricate paths** like `~/.config/aops/` - they don't exist.

## Resolved Paths (Use These Directly)

These are the **concrete absolute paths** for this session. Use them directly with Read/Write/Edit tools:

| Path | Value |
|------|-------|
| Framework root | `$AOPS` |
| User data | `$ACA_DATA` |
| Commands | `$AOPS/commands/` |
| Skills | `$AOPS/skills/` |
| Hooks | `$AOPS/hooks/` |
| Agents | `$AOPS/agents/` |
| Tests | `$AOPS/tests/` |
| Tasks | `$ACA_DATA/tasks/` |
| Projects | `$ACA_DATA/projects/` |

**Common files you may need:**
- User accommodations: [[ACCOMMODATIONS.md]] (in $ACA_DATA/)
- User context: [[CORE.md]] (in $ACA_DATA/)
- Project state: [[STATE.md]] (in $ACA_DATA/projects/aops/)
- Vision: [[VISION.md]] (in $ACA_DATA/projects/aops/)
- Roadmap: [[ROADMAP.md]] (in $ACA_DATA/projects/aops/)

## Path Reference

| Variable | Purpose |
|----------|---------|
| `$AOPS` | Framework source (SSoT for all framework files) |
| `$ACA_DATA` | User data (tasks, sessions, knowledge base) |
| `~/.claude/` | Runtime directory (symlinks → `$AOPS`, DO NOT edit here) |

**To edit framework files**: Always edit in `$AOPS/`, never in `~/.claude/` symlinks.

## bmem

**Always use `project="main"`** with all `mcp__bmem__*` tools.

## Environment Variable Architecture

**How hooks get environment variables:**

1. **`setup.sh`** creates `~/.claude/settings.local.json` with machine-specific paths (AOPS, ACA_DATA)
2. Claude Code reads `settings.local.json` and passes `env` values to all hooks
3. Hooks receive AOPS/ACA_DATA automatically - no hardcoding needed

**Key rules:**
- **NEVER hardcode paths** in framework files (settings.json, hooks, scripts)
- User-specific paths come from `settings.local.json` (created by setup.sh at install time)
- `~/.env` is for shell environment, NOT for Claude Code hooks
- If hooks don't have ACA_DATA: re-run `setup.sh`
