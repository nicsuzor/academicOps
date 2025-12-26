---
name: readme
title: academicOps Framework
type: reference
description: Academic support framework for Claude Code. Entry point and feature inventory.
permalink: readme
tags: [framework, overview, features]
---

# academicOps Framework

Academic support framework for Claude Code. Minimal, fight bloat aggressively.

## Quick Start

- **Paths**: [[FRAMEWORK.md]] (injected at session start)
- **Principles**: [[AXIOMS.md]] (injected at session start)
- **Heuristics**: [[HEURISTICS.md]] (injected at session start)
- **File tree**: [[INDEX.md]]

## Knowledge Architecture

| Layer | Document | Nature |
|-------|----------|--------|
| **Axioms** | [[AXIOMS.md]] | Inviolable principles. No exceptions. |
| **Heuristics** | [[HEURISTICS.md]] | Empirically validated rules. Revisable via `/log adjust-heuristic`. |
| **Practices** | `Skill(skill="framework")` | Conventions derived from axioms. How things get done. |

## Glossary

| Term | Definition |
|------|------------|
| **Skill** | Workflow instructions in [[skills]] - invoke via `Skill` tool |
| **Command** | User-invokable `/slash` command in `commands/` |
| **Hook** | Python script triggered by Claude Code events in `hooks/` |
| **Agent** | Spawnable subagent via `Task` tool (`subagent_type`) |

## Commands

| Command | Purpose | Invocation |
|---------|---------|------------|
| /meta | Strategic brain + executor | Slash command |
| /email | Extract action items from emails → tasks | Slash command |
| /log | Log patterns to thematic learning files | Slash command |
| /transcript | Generate session transcripts | Slash command |
| /analyze-session | Semantic session analysis | Slash command |
| /task-viz | Task graph visualization (Excalidraw) | Slash command |
| /qa | Verify against acceptance criteria | Slash command |
| /ttd | TDD orchestration workflow | Slash command |
| /parallel-batch | Parallel file processing | Slash command |

## Skills

| Skill | Purpose | Invocation |
|-------|---------|------------|
| analyst | Research data analysis (dbt, stats) | `Skill(skill="analyst")` |
| remember | Store and retrieve memories via memory server | `Skill(skill="remember")` |
| framework | Convention reference, categorical imperative | `Skill(skill="framework")` |
| osb-drafting | IRAC analysis, citation verification | `Skill(skill="osb-drafting")` |
| pdf | Markdown → professional PDF | `Skill(skill="pdf")` |
| python-dev | Production Python (fail-fast, typed) | `Skill(skill="python-dev")` |
| tasks | Task management + email extraction | `Skill(skill="tasks")` or `/email` |
| transcript | Session JSONL → markdown | `Skill(skill="transcript")` |
| session-analyzer | Semantic session analysis | `Skill(skill="session-analyzer")` |
| learning-log | Pattern logging to thematic files | `Skill(skill="learning-log")` |
| dashboard | Live task + session activity dashboard | `uv run streamlit run skills/dashboard/dashboard.py` |
| reference-map | Extract framework file references → JSON graph | `Skill(skill="reference-map")` |
| link-audit | Analyze and clean up framework file references | `Skill(skill="link-audit")` |
| session-insights | Batch transcripts + mining for framework learnings | `Skill(skill="session-insights")` |

## Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| `sessionstart_load_axioms.py` | SessionStart | Inject AXIOMS.md, FRAMEWORK.md paths |
| `user_prompt_submit.py` | UserPromptSubmit | Context injection on every prompt |
| `prompt_router.py` | UserPromptSubmit | Keyword → skill suggestions |

See [[docs/HOOKS.md]] for hook architecture, [[docs/OBSERVABILITY.md]] for logging/debugging.

## Agents

| Agent | Purpose | Invocation |
|-------|---------|------------|
| Explore | Fast codebase exploration | `Task(subagent_type="Explore")` |
| Plan | Implementation planning | `Task(subagent_type="Plan")` |
| critic | Second-opinion review of plans/conclusions | `Task(subagent_type="critic", model="haiku")` |

**Note**: For Python development, use `general-purpose` subagent and invoke `Skill(skill="python-dev")` first.

**Mandatory**: Use critic agent to review plans before presenting to user.

## Testing

- **Unit tests**: `tests/` (270 tests, 98% pass)
- **Integration tests**: `tests/integration/` (require Claude CLI)
- **Run**: `uv run pytest tests/`

## Memory Server

Use `mcp__memory__*` tools to store and retrieve memories. Memory server is accessed via remote connection over Tailscale.

