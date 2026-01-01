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

**Single entry point**: All work goes through `/do`, which transforms the main agent into an orchestration layer.

| Command | Role | When to Use |
|---------|------|-------------|
| `/do` | Full pipeline (context, plan, execute, verify) | All non-trivial work |
| `/meta` | Strategic brain + executor | Framework problems, design AND build |
| `/q` | Queue for later | Capture task without executing |

**/do Pipeline** (5 phases):
1. Context gathering (memory search, file discovery)
2. Task classification and planning skill selection
3. TodoWrite with CHECKPOINT items (QA gates)
4. Delegated execution to specialist skills
5. Verification against acceptance criteria
6. Cleanup (commit, push, memory)

**Framework Workflows** (loaded via `Skill("framework")`):
- `01-design-new-component` - Adding new hooks, skills, scripts, commands
- `02-debug-framework-issue` - Diagnosing framework component failures
- `03-experiment-design` - Testing hypotheses about behavior
- `06-develop-specification` - Collaborative spec development

## /do Command (Primary Entry Point)

The `/do` command transforms the main agent into an orchestration layer:

```
/do [your task]
    ↓
Main agent becomes orchestrator:
  0. CONTEXT - Memory search, file discovery, classification
  1. PLAN - TodoWrite with CHECKPOINT items, critic review
  2. EXECUTE - Delegate to subagents, verify each step
  3. VERIFY - Check against acceptance criteria
  4. CLEANUP - Commit, push, update memory
```

**Key insight**: Control the plan = control the work. CHECKPOINT items are QA gates that cannot be skipped.

Full instructions: `$AOPS/commands/do.md`

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
| Do something (with full context) | `/do your task here` |
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
| /do | Execute work with full context enrichment and guardrails |
| /audit | Comprehensive framework governance audit |
| /email | Extract action items from emails → tasks |
| /learn | Make minimal framework tweaks with tracking |
| /log | Log agent patterns to thematic learning files |
| /meta | Strategic brain + executor for framework work |
| /parallel-batch | Parallel file processing with skill delegation |
| /q | Queue task for later execution (delayed /do) |
| /qa | Verify outcomes against acceptance criteria |
| /review-training-cmd | Process review/source pair for training data |
| /strategy | Strategic thinking partner (no execution) |
| /task-viz | Task graph visualization (Excalidraw) |
| /ttd | TDD workflow |

## Skills

| Skill | Purpose |
|-------|---------|
| analyst | Research data analysis (dbt, Streamlit, stats) |
| fact-check | Verify factual claims against authoritative sources |
| audit | Comprehensive framework governance (structure, justification, index updates) |
| dashboard | Live Streamlit dashboard for tasks + sessions |
| excalidraw | Hand-drawn diagrams with organic layouts |
| extractor | Extract knowledge from archive documents |
| feature-dev | Test-first feature development workflow |
| framework | Convention reference, categorical imperative |
| garden | Incremental PKM maintenance (weeding, linking) |
| ground-truth | Establish ground truth labels for evaluation |
| learning-log | Log patterns to thematic learning files |
| osb-drafting | IRAC analysis for Oversight Board cases |
| pdf | Markdown → professional PDF |
| python-dev | Production Python (fail-fast, typed, TDD) |
| remember | Persist knowledge to markdown + memory server |
| review-training | Extract training pairs from matched documents |
| session-insights | Extract accomplishments + learnings from sessions |
| supervisor | Workflow templates (tdd, batch-review) |
| tasks | Task lifecycle management |
| training-set-builder | Build LLM training datasets from documents |
| transcript | Session JSONL → markdown |

**Invoke**: `Skill(skill="name")` or via commands that wrap them.

## Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| `sessionstart_load_axioms.py` | SessionStart | Inject AXIOMS.md, FRAMEWORK.md paths |
| `user_prompt_submit.py` | UserPromptSubmit | Context injection per prompt |

See [docs/HOOKS.md](docs/HOOKS.md) for hook architecture.

## Agents

Custom agents spawned via `Task(subagent_type="name")`:

| Agent | Purpose |
|-------|---------|
| critic | Second-opinion review of plans/conclusions |
| effectual-planner | Strategic planning under uncertainty (NOT implementation) |
| planner | Implementation planning with memory context + critic review |
| prompt-hydrator | Context gathering + workflow selection (invoked on every prompt) |

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

