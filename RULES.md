---
name: rules
title: Enforcement Rules
type: reference
description: Current state of all enforcement mechanisms (auto-generated). Do not edit manually.
permalink: rules
tags: [framework, enforcement, configuration]
---

# Enforcement Rules

Current state of all enforcement mechanisms. **Auto-generated** — do not edit manually.

**Last updated**: 2025-12-15 12:15

**To regenerate**: Invoke [[academicOps/skills/framework]] with "update enforcement state"

---

## Deny Rules (settings.json)

Path-based access control via `~/.claude/settings.json` → `permissions.deny`:

### Task Protection
- `Write(/data/tasks/**)`
- `Write(*/data/tasks/**)`
- `Edit(/data/tasks/**)`
- `Edit(*/data/tasks/**)`
- `Bash(rm */data/tasks/**)`
- `Bash(mv */data/tasks/**)`
- `Bash(cp */data/tasks/**)`
- `Bash(git mv */data/tasks/**)`
- `Bash(git rm */data/tasks/**)`

### Claude Config Protection (Read)
- `Read(~/.claude/settings.json)`
- `Read(~/.claude/settings.local.json)`
- `Read(~/.claude/mcp.json)`
- `Read(~/.claude/.credentials.json)`

Note: Reading `~/.claude/hooks/**`, `skills/**`, `commands/**`, `agents/**` is allowed (needed for skill invocation).

### Claude Config Protection (Write/Edit)
- `Write(~/.claude/settings.json)`
- `Write(~/.claude/settings.local.json)`
- `Write(~/.claude/mcp.json)`
- `Write(~/.claude/.credentials.json)`
- `Write(~/.claude/hooks/**)`
- `Write(~/.claude/skills/**)`
- `Write(~/.claude/commands/**)`
- `Write(~/.claude/agents/**)`
- `Edit(~/.claude/settings.json)`
- `Edit(~/.claude/settings.local.json)`
- `Edit(~/.claude/mcp.json)`
- `Edit(~/.claude/.credentials.json)`
- `Edit(~/.claude/hooks/**)`
- `Edit(~/.claude/skills/**)`
- `Edit(~/.claude/commands/**)`
- `Edit(~/.claude/agents/**)`

### Claude Config Protection (Bash)
- `Bash(rm ~/.claude/settings*)`
- `Bash(rm ~/.claude/mcp.json)`
- `Bash(rm ~/.claude/.credentials.json)`
- `Bash(rm -rf ~/.claude/hooks)`
- `Bash(rm -rf ~/.claude/skills)`
- `Bash(rm -rf ~/.claude/commands)`
- `Bash(rm -rf ~/.claude/agents)`
- `Bash(mv ~/.claude/settings*)`
- `Bash(mv ~/.claude/mcp.json)`
- `Bash(mv ~/.claude/.credentials.json)`
- `Bash(mv ~/.claude/hooks)`
- `Bash(mv ~/.claude/skills)`
- `Bash(mv ~/.claude/commands)`
- `Bash(mv ~/.claude/agents)`

---

## PreToolUse Blocks (policy_enforcer.py)

Pattern-based blocking via `$AOPS/hooks/policy_enforcer.py`:

### Documentation Bloat Prevention
- **Write(*-GUIDE.md)** — blocks files ending in `-GUIDE.md`
- **Write(*.md > 200 lines)** — blocks markdown files exceeding 200 lines

### Git Safety
- `git reset --hard`
- `git clean -f` or `git clean -d`
- `git push --force`
- `git checkout -- .`
- `git stash drop`

---

## Pre-commit Hooks (.pre-commit-config.yaml)

Commit-time validation via `.pre-commit-config.yaml`:

### Standard Hygiene
- `trailing-whitespace`
- `check-yaml`
- `check-json` (excludes .vscode/, .claude/, .ipynb)
- `check-toml`
- `mixed-line-ending` (enforces LF)

### Linting
- `shellcheck` — shell script linting
- `eslint` — JS/TS linting
- `ruff` — Python linting + formatting
- `ruff-format` — Python formatting

### Local Hooks
- `dprint` — markdown/json/toml/yaml formatting
- `bmem-validate` — frontmatter validation for `data/*.md`
- `data-markdown-only` — blocks non-.md files in `data/` (except `data/assets/`)
