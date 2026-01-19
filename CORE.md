---
title: Framework Paths and Configuration
type: instruction
description: Session-resolved paths and environment configuration. Injected at session start.
---

## Python Tooling

**Always use `uv run`** for Python commands in this framework:
- `uv run python script.py` (not `python script.py`)
- `uv run pytest tests/` (not `pytest tests/`)
- `uv run ruff check .` (not `ruff check .`)

This ensures the correct virtual environment and dependencies are used without manual activation.

## Memory System

User memories are strictly organised with a clear distinction between:

- **Episodic Memory** (Observations): Time-stamped events, what happened when. "I tried X and it failed." "Meeting decided Y."
- **Semantic Memory** (Current State): Timeless truths, always up-to-date. "X doesn't work because Y." "Our approach is Z."

### Three Storage Systems

| System | Purpose | When to Use |
|--------|---------|-------------|
| **bd issues** | Operational tracking | Tasks, bugs, observations, experiments, decisions-in-progress |
| **$ACA_DATA markdown** | Knowledge SSoT | Synthesized truths, project context, goals, general knowledge |
| **Memory server** | Semantic search index | Markdown + closed bd issues with learnings - enables `mcp__memory__retrieve_memory` |

### Automatic Sync: Closed Issues → Memory

When a bd issue is closed with a `--reason` (documented learning), it's automatically synced to the memory server via PostToolUse hook. This makes learnings from closed issues searchable alongside synthesized knowledge.

- **Tagged**: `bd-issue`, `closed`, `type:<issue_type>`, `priority:P<n>`
- **Content**: Title, description, close_reason (learning), closed date
- **Search**: `mcp__memory__retrieve_memory(query="...")` finds both markdown AND closed issue learnings

### Decision Tree

```
Is this a task or observation? (time-stamped, "agent did X")
  → YES: bd create or bd update (NOT remember skill)

Is this synthesized knowledge? (timeless truth, "X is Y")
  → YES: Skill(skill="remember") → writes markdown + memory server

Need to search existing knowledge?
  → USE: mcp__memory__retrieve_memory(query="...")
```

### Key Rules

1. **Memory is the knowledge source** - Agents MUST check `mcp__memory__retrieve_memory` when starting tasks or needing context. This is how you access user knowledge, project history, and learned patterns. Don't guess - search memory first.
2. **Markdown is SSoT** - Memory server is derived, not authoritative
3. **Remember skill dual-writes** - Always use it for new knowledge (ensures sync)
4. **bd for observations** - Don't create markdown files for time-stamped events
5. **Synthesis flow**: bd observations → patterns emerge → remember skill → semantic docs → close bd issue

### Insight Capture

When you discover something worth preserving:
- **Operational insight** (bug found, approach tried): `bd create` or comment on existing issue
- **Knowledge insight** (pattern, principle, fact): `Skill(skill="remember")`
- **Both**: Create bd issue for tracking, use remember skill for the knowledge

**To persist knowledge**: Use `Skill(skill="remember")` (blocking) or spawn background Task with `run_in_background=true` (seamless).

**To search**: Use `mcp__memory__retrieve_memory(query="...")`.

**To repair sync**: Run remember skill's sync workflow (reconciles markdown → memory server).
