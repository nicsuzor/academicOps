---
name: rules
title: Enforcement Rules
type: reference
description: What rules are enforced, how, and evidence of effectiveness.
permalink: rules
tags: [framework, enforcement, moc]
---

# Enforcement Rules

**Purpose**: Current state of what's protected and how. For mechanism selection guidance, see [[ENFORCEMENT|docs/ENFORCEMENT.md]]. For architectural philosophy, see [[enforcement|specs/enforcement.md]].

## Active Rules

|Reference |Rule |Enforcement |
|---|---|---|
| Axiom x | ... | [[AGENTS.md]] |
| Axiom x | ... | [[AGENTS.md]] |
| Axiom x | ... | [[AGENTS.md]] |
| Axiom x | ... | [[AGENTS.md]] |
| Axiom x | ... | [[AGENTS.md]] |

### Path Protection (Deny Rules)

| Category | Pattern | Blocked Tools | Purpose | Evidence |
|----------|---------|---------------|---------|----------|
| Task files | `**/data/tasks/**` | Write, Edit, Bash | Force use of `/tasks` skill for workflow control | Agent redirects to skill |
| Claude config | `~/.claude/*.json` | Read, Write, Edit, Bash | Protect secrets (credentials, API keys) | No leaks |
| Claude runtime | `~/.claude/{hooks,skills,commands,agents}/**` | Write, Edit, Bash | Force edits via `$AOPS/` canonical source, not symlinks | Changes go to repo |
| Research records | `**/tja/records/**`, `**/tox/records/**` | Write, Edit, Bash | Research data immutable (AXIOMS #24) | Data integrity |

**Note**: Reading `~/.claude/hooks/**` etc IS allowed (skill invocation needs it).

### Pattern Blocking (PreToolUse Hook)

| Category | Pattern | Blocked Tools | Purpose | Evidence |
|----------|---------|---------------|---------|----------|
| Doc bloat | `*-GUIDE.md` | Write | MINIMAL principle - add to README instead | Blocks in logs |
| Doc bloat | `.md` > 200 lines | Write | Force chunking into focused files | Splits happen |
| Git: hard reset | `git reset --hard` | Bash | Preserve uncommitted work | No data loss |
| Git: clean | `git clean -[fd]` | Bash | Preserve untracked files | No data loss |
| Git: force push | `git push --force` | Bash | Protect shared history | No rewrites |
| Git: checkout all | `git checkout -- .` | Bash | Preserve local changes | No data loss |
| Git: stash drop | `git stash drop` | Bash | Preserve stashed work | No data loss |

### Commit-Time Validation (Pre-commit)

| Category | Hook | Purpose | Evidence |
|----------|------|---------|----------|
| File hygiene | trailing-whitespace, check-yaml/json/toml, mixed-line-ending | Clean commits | Auto-fixed |
| Code quality | shellcheck, eslint, ruff | Catch errors before commit | Lint errors blocked |
| Formatting | dprint | Consistent markdown/json/toml/yaml | Auto-formatted |
| Data integrity | bmem-validate | Valid frontmatter in `data/*.md` | Invalid blocked |
| Data purity | data-markdown-only | Only `.md` in `data/` (except `assets/`) | Non-md blocked |

---

## Source Files

| Mechanism | Authoritative Source |
|-----------|---------------------|
| Deny rules | `$AOPS/config/claude/settings.json` → `permissions.deny` |
| PreToolUse | `$AOPS/hooks/policy_enforcer.py` |
| Pre-commit | `$AOPS/../.pre-commit-config.yaml` (repo root) |

