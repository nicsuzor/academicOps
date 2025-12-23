---
name: rules
title: Enforcement Rules Map
type: reference
description: What rules are enforced, where, and how. MoC for enforcement mechanisms.
permalink: rules
tags: [framework, enforcement, moc]
---

# Enforcement Rules

What's protected, how it's enforced, and where to find the source.

For **mechanism details** (how each enforcement level works): [[skills/framework/ENFORCEMENT.md]]

---

## Quick Reference

| Category | What's Protected | Mechanism | Source |
|----------|------------------|-----------|--------|
| Task files | `**/data/tasks/**` | Deny rules | `config/claude/settings.json` |
| Claude config | `~/.claude/*` | Deny rules | `config/claude/settings.json` |
| Research records | `**/tja/records/**`, `**/tox/records/**` | Deny rules | `config/claude/settings.json` |
| Doc bloat | `*-GUIDE.md`, `.md` > 200 lines | PreToolUse block | `hooks/policy_enforcer.py` |
| Git safety | Destructive commands | PreToolUse block | `hooks/policy_enforcer.py` |
| Data integrity | Format validation | Pre-commit | `.pre-commit-config.yaml` |

---

## Deny Rules (settings.json)

**Mechanism**: Claude Code's built-in permission system. Glob patterns, hard block.

**Source**: `$AOPS/config/claude/settings.json` → `permissions.deny`

### Task Files

**Pattern**: `**/data/tasks/**`
**Blocked tools**: Write, Edit, Bash (rm, mv, cp, git mv, git rm)
**Why**: Tasks require workflow control via `/tasks` skill

### Claude Config

**Pattern**: `~/.claude/*` (settings.json, settings.local.json, mcp.json, .credentials.json, hooks/**, skills/**, commands/**, agents/**)
**Blocked tools**: Read (sensitive files), Write, Edit, Bash (rm, mv)
**Why**: Prevents agents from modifying their own constraints
**Note**: Reading hooks/skills/commands/agents IS allowed (needed for skill invocation)

### Research Records

**Pattern**: `**/tja/records/**`, `**/tox/records/**`
**Blocked tools**: Write, Edit, Bash (rm, mv)
**Why**: Research data is immutable (AXIOMS #24)

---

## PreToolUse Blocks (policy_enforcer.py)

**Mechanism**: Hook intercepts tool calls, blocks on pattern match. Exit code 2 = block.

**Source**: `$AOPS/hooks/policy_enforcer.py`

### Documentation Bloat

| Pattern | Type | Why |
|---------|------|-----|
| `*-GUIDE.md` | Filename suffix | MINIMAL principle - add to README instead |
| `.md` > 200 lines | Line count | Split into focused chunks |

### Git Safety

**Pattern type**: Regex on Bash commands

| Blocked | Why |
|---------|-----|
| `git reset --hard` | Destroys uncommitted work |
| `git clean -f` / `-d` | Deletes untracked files |
| `git push --force` | Rewrites shared history |
| `git checkout -- .` | Discards all changes |
| `git stash drop` | Loses stashed work |

---

## Pre-commit Hooks

**Mechanism**: Validates files at commit time. Blocks commit on failure.

**Source**: `$AOPS/../.pre-commit-config.yaml` (repo root)

### File Hygiene

- Trailing whitespace removal
- YAML/JSON/TOML syntax validation
- LF line endings enforced

### Linting

- `shellcheck` — shell scripts
- `eslint` — JS/TS
- `ruff` — Python (lint + format)

### Data Integrity

| Hook | What | Pattern |
|------|------|---------|
| `dprint` | Format markdown, json, toml, yaml | Various extensions |
| `bmem-validate` | Frontmatter validation | `^data/.*\.md$` |
| `data-markdown-only` | Block non-.md in data/ | `^data/(?!assets/).*$` exclude `.md` |

---

## Maintenance

This is a **curated MoC**, not auto-generated. When enforcement sources change:

1. Edit the source file (settings.json, policy_enforcer.py, or .pre-commit-config.yaml)
2. Update this file to reflect the change
3. Keep categories grouped by purpose, not by source file
