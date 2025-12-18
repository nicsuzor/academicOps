---
title: Framework Enforcement Mechanisms
type: reference
permalink: framework-enforcement
description: Reference guide for enforcement mechanisms that influence agent behavior and control execution
tags:
  - enforcement
  - hooks
  - policies
---

# Framework Enforcement Mechanisms

Reference for mechanisms that influence agent behavior.

## Quick Reference

| Level | Mechanism | Strength | Best For |
|-------|-----------|----------|----------|
| 1 | Ad-hoc prompts | Soft | One-time guidance |
| 2 | CLAUDE.md + `@` includes | Persistent | Project conventions, composable rules |
| 3 | SessionStart injection | JIT | Core principles, paths, user context |
| 4 | UserPromptSubmit routing | JIT | Skill suggestions per-prompt |
| 5a | PreToolUse warn (exit 1) | Medium | Agent should reconsider |
| 5b | PreToolUse block (exit 2) | Hard | Pattern-based blocking |
| 6 | Deny rules | Hard | Path-based access control |
| 7 | Pre-commit hooks | Hard | Data integrity validation |

---

## Level 1: Ad-hoc Prompts

Direct guidance in conversation. Zero setup, not persistent.

**Use**: Experimenting with patterns before formalizing.

---

## Level 2: CLAUDE.md + `@` Includes

`CLAUDE.md` auto-loads at session start. Supports `@file.md` syntax to compose content from other files (README, style guides, etc.).

**Structure**: Keep CLAUDE.md minimal; use `@` includes for modular content that may be shared or updated independently.

**Limits**: Advisory only—agents can ignore. Long files get skimmed.

---

## Level 3: SessionStart Injection

`sessionstart_load_axioms.py` injects multiple files as `additionalContext`:

- **FRAMEWORK.md** — resolved paths (prevents path guessing)
- **AXIOMS.md** — inviolable principles
- **HEURISTICS.md** — empirical rules
- **CORE.md** — user context and preferences

This ensures critical context loads even if CLAUDE.md is bypassed or skimmed. More prominent than CLAUDE.md because it appears in active context.

---

## Level 4: UserPromptSubmit Routing

`../../hooks/prompt_router.py` analyzes every user message and injects:

1. **Focus reminder** — prevents over-elaboration
2. **Skill routing** — keyword matching → "MANDATORY: Call Skill(skill='X')"
3. **Classifier offer** — when no keyword match, suggests Haiku semantic classification

More timely than CLAUDE.md because it's fresh in context at decision point.

---

## Level 5: PreToolUse Hooks

[[../../hooks/policy_enforcer.py]] can warn or block tool execution.

**Exit code semantics** (per Claude Code docs):

| Exit | Behavior | Message shown to |
|------|----------|------------------|
| 0 | Allow | JSON stdout processed (user in verbose mode) |
| 1 | Warn but allow | stderr shown to **user AND agent** |
| 2 | Block | stderr shown to **agent only** |

**Key insight**: Exit code 1 enables **soft enforcement** — agent sees warning and can self-correct without blocking the operation.

**Authoritative source**: [[../../hooks/policy_enforcer.py]]

**Use cases**:
- Exit 2 (block): Pattern is dangerous AND detectable before execution
- Exit 1 (warn): Pattern is questionable, agent should reconsider

---

## Level 6: settings.json Deny Rules

Built-in permission system blocks specific paths.

**Authoritative source**: [[../../config/claude/settings.json]] → `permissions.deny`

**To view**: `cat ~/.claude/settings.json | jq '.permissions.deny'`

**Use**: Paths that should NEVER be directly accessed.

---

## Level 7: Pre-commit Hooks

Final gate before persistence.

**Authoritative source**: [[../../.pre-commit-config.yaml]]

**Use**: Data format must be valid before commit.

---

## Decision Guide

| Need | Mechanism |
|------|-----------|
| Agent should know X (always) | CLAUDE.md or SessionStart |
| Agent should know X (once) | Ad-hoc prompt |
| Reminder at decision time | UserPromptSubmit hook |
| Agent should reconsider X | PreToolUse warn (exit 1) |
| Agent must not do X (pattern) | PreToolUse block (exit 2) |
| Agent must not do X (path) | Deny rule |
| Data must be valid | Pre-commit hook |
