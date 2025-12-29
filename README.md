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

- **Paths**: [FRAMEWORK.md](FRAMEWORK.md) (injected at session start)
- **Principles**: [AXIOMS.md](AXIOMS.md) (injected at session start)
- **Heuristics**: [HEURISTICS.md](HEURISTICS.md) (injected at session start)
- **File tree**: [INDEX.md](INDEX.md)
- **Workflow selection**: See [specs/workflow-selection.md](specs/workflow-selection.md) (DRAFT - decision pending)

## Installation

| Environment | Setup | Documentation |
|-------------|-------|---------------|
| **Full** (laptop, WSL, VM) | `./setup.sh` | Creates `~/.claude/` symlinks |
| **Limited** (Claude Code Web) | `python scripts/sync_web_bundle.py /path/to/project` | See [WEB-BUNDLE.md](docs/WEB-BUNDLE.md) |

**Auto-sync**: The sync script automatically installs a git hook for auto-updates. See docs/WEB-BUNDLE.md for GitHub Actions workflow.

## Workflows

Two orchestration approaches exist. Selection criteria are under development.

| Command | Role | When to Use |
|---------|------|-------------|
| `/meta` | Strategic brain + executor (full tool access) | Framework problems end-to-end, design AND build |
| `/supervise` | Strict delegator via hypervisor agent | Structured work with quality gates, delegates to subagents |

**Hypervisor Workflows** (`/supervise {description}`):
The hypervisor agent orchestrates multi-step work with phases 0-5 (planning → implementation → QA). Workflow templates are planned but not yet implemented - describe the workflow approach in your prompt.

**Framework Workflows** (loaded via `Skill("framework")`):
- `01-design-new-component` - Adding new hooks, skills, scripts, commands
- `02-debug-framework-issue` - Diagnosing framework component failures
- `03-experiment-design` - Testing hypotheses about behavior
- `06-develop-specification` - Collaborative spec development

**Open question**: How should agents choose between these? See [specs/workflow-selection.md](specs/workflow-selection.md).

## Knowledge Architecture

| Layer | Document | Nature |
|-------|----------|--------|
| **Axioms** | [AXIOMS.md](AXIOMS.md) | Inviolable principles. No exceptions. |
| **Heuristics** | [HEURISTICS.md](HEURISTICS.md) | Empirically validated rules. Revisable via `/log adjust-heuristic`. |
| **Practices** | `Skill(skill="framework")` | Conventions derived from axioms. How things get done. |

## Glossary

| Term | Definition |
|------|------------|
| **Skill** | Workflow instructions in [skills](skills/) - invoke via `Skill` tool |
| **Command** | User-invokable `/slash` command in `commands/` |
| **Hook** | Python script triggered by Claude Code events in `hooks/` |
| **Agent** | Spawnable subagent via `Task` tool (`subagent_type`) |

## Common Tasks

| I want to... | Use |
|--------------|-----|
| See what's available | `/aops` |
| Capture a quick idea | `/q your idea here` |
| Work on next priority task | `/pull` |
| Add a task | `/add task description` |
| Extract tasks from email | `/email` |
| Get framework help | `/meta your question` |
| Run TDD workflow | `/ttd` |
| Visualize my tasks | `/task-viz` |
| Log a framework pattern | `/log category: observation` |
| Verify work is complete | `/qa` |

## Commands

| Command | Purpose |
|---------|---------|
| /aops | Show framework capabilities (this README) |
| /add | Quick-add a task from session context |
| /consolidate | Consolidate LOG.md entries into thematic files |
| /diag | Quick diagnostic of what's loaded in session |
| /audit | Comprehensive framework governance audit |
| /email | Extract action items from emails → tasks |
| /learn | Make minimal framework tweaks with tracking |
| /log | Log agent patterns to thematic learning files |
| /meta | Strategic brain + executor for framework work |
| /parallel-batch | Parallel file processing with skill delegation |
| /pull | Process next high-priority task |
| /q | Quick capture idea → prompt queue |
| /qa | Verify outcomes against acceptance criteria |
| /review-training-cmd | Process review/source pair for training data |
| /strategy | Strategic thinking partner (no execution) |
| /supervise | Orchestrate multi-agent workflow with quality gates |
| /task-viz | Task graph visualization (Excalidraw) |
| /ttd | TDD workflow (alias for `/supervise tdd`) |

## Skills

| Skill | Purpose |
|-------|---------|
| analyst | Research data analysis (dbt, Streamlit, stats) |
| dashboard | Live Streamlit dashboard for tasks + sessions |
| audit | Comprehensive framework governance (structure, justification, index updates) |
| excalidraw | Hand-drawn diagrams with organic layouts |
| extractor | Extract knowledge from archive documents |
| feature-dev | Test-first feature development workflow |
| framework | Convention reference, categorical imperative |
| framework-debug | Investigate session logs for framework issues |
| framework-review | Analyze transcripts for improvement opportunities |
| garden | Incremental PKM maintenance (weeding, linking) |
| ground-truth | Establish ground truth labels for evaluation |
| learning-log | Log patterns to thematic learning files |
| link-audit | Clean up framework file references |
| osb-drafting | IRAC analysis for Oversight Board cases |
| pdf | Markdown → professional PDF |
| python-dev | Production Python (fail-fast, typed, TDD) |
| reference-map | Extract framework references → graph |
| remember | Persist knowledge to markdown + memory server |
| review-training | Extract training pairs from matched documents |
| session-insights | Extract accomplishments + learnings from sessions |
| supervisor | Generic multi-agent workflow orchestrator |
| task-expand | Intelligent task breakdown with dependencies |
| tasks | Task lifecycle management |
| training-set-builder | Build LLM training datasets from documents |
| transcript | Session JSONL → markdown |

**Invoke**: `Skill(skill="name")` or via commands that wrap them.

## Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| `sessionstart_load_axioms.py` | SessionStart | Inject AXIOMS.md, FRAMEWORK.md paths |
| `user_prompt_submit.py` | UserPromptSubmit | Context injection per prompt |
| `prompt_router.py` | UserPromptSubmit | Intent routing + skill suggestions |

See [docs/HOOKS.md](docs/HOOKS.md) for hook architecture.

## Agents

Custom agents spawned via `Task(subagent_type="name")`:

| Agent | Purpose |
|-------|---------|
| critic | Second-opinion review of plans/conclusions |
| hypervisor | Multi-step workflow orchestrator (phases 0-5) |
| intent-router | LLM intent classifier (Haiku) |
| effectual-planner | Strategic planning under uncertainty (NOT implementation) |
| prompt-writer | Transform fragments into executable prompts |

Built-in Claude Code agents (also available):
- `Explore` - Fast codebase exploration
- `Plan` - Implementation planning
- `general-purpose` - General tasks (use with `Skill("python-dev")` for Python work)

## Testing

- **Unit tests**: `tests/` (270 tests, 98% pass)
- **Integration tests**: `tests/integration/` (require Claude CLI)
- **Run**: `uv run pytest tests/`

## Memory Server

Use `mcp__memory__*` tools to store and retrieve memories. Memory server is accessed via remote connection over Tailscale.

