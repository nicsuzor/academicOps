---
name: readme
category: spec
title: academicOps Framework
type: reference
description: Human feature guide - capabilities, workflows, and how things fit together.
permalink: readme
audience: humans
tags: [framework, overview, features]
---

# academicOps Framework

Academic support framework for Claude Code. Minimal, fight bloat aggressively.

See [[documentation-architecture]] for document purposes. Agents use [[FRAMEWORK.md]] for paths.

## Quick Start

- **Paths**: [FRAMEWORK.md](FRAMEWORK.md) (injected at session start)
- **Principles**: [AXIOMS.md](AXIOMS.md) (injected at session start)
- **Heuristics**: [HEURISTICS.md](HEURISTICS.md) (injected at session start)
- **File tree**: [INDEX.md](INDEX.md)
- **Workflow selection**: See [specs/workflow-selection.md](specs/workflow-selection.md) (DRAFT - decision pending)

## How It Works

See [[FLOW]] for the complete execution flow diagram.

See [[docs/ENFORCEMENT.md]] for practical enforcement guide, [[specs/enforcement.md]] for architecture.

## Installation

| Environment                   | Setup                                                | Documentation                           |
| ----------------------------- | ---------------------------------------------------- | --------------------------------------- |
| **Full** (laptop, WSL, VM)    | `./setup.sh`                                         | Creates `~/.claude/` symlinks           |
| **Limited** (Claude Code Web) | `python scripts/sync_web_bundle.py /path/to/project` | See [WEB-BUNDLE.md](docs/WEB-BUNDLE.md) |

**Auto-sync**: The sync script automatically installs a git hook for auto-updates. See docs/WEB-BUNDLE.md for GitHub Actions workflow.

## Workflows

**Prompt hydration**: Every prompt is hydrated by the `prompt-hydrator` agent before execution, which selects the appropriate workflow and provides TodoWrite guidance.

| Command | Role                       | When to Use                          |
| ------- | -------------------------- | ------------------------------------ |
| `/meta` | Strategic brain + executor | Framework problems, design AND build |
| `/q`    | Queue for later            | Capture task without executing       |
| `/pull` | Execute next queued task   | Work through the queue               |

**Workflow Pipeline** (automatic via prompt hydration):

1. Context gathering (memory search, file discovery)
2. Task classification and workflow selection
3. TodoWrite with CHECKPOINT items (QA gates)
4. Delegated execution to specialist skills
5. Verification against acceptance criteria
6. Cleanup (commit, push, memory)

**Framework Workflows** (loaded via `Skill("framework")`):

- `01-design-new-component` - Adding new hooks, skills, scripts, commands
- `02-debug-framework-issue` - Diagnosing framework component failures
- `03-experiment-design` - Testing hypotheses about behavior
- `06-develop-specification` - Collaborative spec development

See [[WORKFLOWS.md]] for the complete workflow catalog and agent mandates.

## Knowledge Architecture

| Layer          | Document                       | Nature                                                                 |
| -------------- | ------------------------------ | ---------------------------------------------------------------------- |
| **Axioms**     | [AXIOMS.md](AXIOMS.md)         | Inviolable principles. No exceptions.                                  |
| **Heuristics** | [HEURISTICS.md](HEURISTICS.md) | Empirically validated rules. Updated via `/reflect` approval workflow. |
| **Practices**  | `Skill(skill="framework")`     | Conventions derived from axioms. How things get done.                  |

## Glossary

| Term        | Definition                                                           |
| ----------- | -------------------------------------------------------------------- |
| **Skill**   | Workflow instructions in [skills](skills/) - invoke via `Skill` tool |
| **Command** | User-invokable `/slash` command in `commands/`                       |
| **Hook**    | Python script triggered by Claude Code events in `hooks/`            |
| **Agent**   | Spawnable subagent via `Task` tool (`subagent_type`)                 |

## Common Tasks

| I want to...              | Use                          |
| ------------------------- | ---------------------------- |
| See what's available      | `/aops`                      |
| Queue a task for later    | `/q task description`        |
| Pull next task from queue | `/pull`                      |
| Extract tasks from email  | `/email`                     |
| Get framework help        | `/meta your question`        |
| Run TDD workflow          | `/ttd`                       |
| Visualize my tasks        | `/task-viz`                  |
| Log a framework pattern   | `/log category: observation` |
| Verify work is complete   | `/qa`                        |
| Get task recommendations  | `/task-next`                 |

## Commands

| Command              | Purpose                                                                                      |
| -------------------- | -------------------------------------------------------------------------------------------- |
| /aops                | Show framework capabilities                                                                  |
| /audit-framework     | Comprehensive framework governance audit                                                     |
| /diag                | Quick diagnostic of what's loaded in session                                                 |
| /email               | Extract action items from emails → tasks                                                     |
| /learn               | Make minimal framework tweaks with tracking                                                  |
| /log                 | Log agent patterns to thematic learning files                                                |
| /meta                | Strategic brain + executor for framework work                                                |
| /pull                | Get and run a task from the queue                                                            |
| /q                   | Queue user task for later (→ task system)                                                    |
| /qa                  | Verify outcomes against acceptance criteria                                                  |
| /reflect             | Self-audit process compliance; see also `/session-insights current` for automated reflection |
| /remind              | Queue agent work for later (→ bd issues)                                                     |
| /review-training-cmd | Process review/source pair for training data                                                 |
| /strategy            | Strategic thinking partner (no execution)                                                    |
| /task-next           | Get 2-3 task recommendations (should/enjoy/quick)                                            |
| /task-viz            | Task graph visualization (Excalidraw)                                                        |
| /ttd                 | TDD workflow (alias for /supervise tdd)                                                      |

## Skills

| Skill                | Purpose                                                                            |
| -------------------- | ---------------------------------------------------------------------------------- |
| analyst              | Research data analysis (dbt, Streamlit, stats)                                     |
| annotations          | Scan and process inline HTML comments for human-agent collaboration                |
| audit                | Comprehensive framework governance (structure, justification, index updates)       |
| convert-to-md        | Batch convert documents (DOCX, PDF, XLSX, etc.) to markdown                        |
| daily                | Daily note lifecycle - morning briefing, task recommendations                      |
| dashboard            | Live Streamlit dashboard for tasks + sessions                                      |
| debug-headless       | Debug Claude Code or Gemini CLI in headless mode with full output capture          |
| excalidraw           | Hand-drawn diagrams with organic layouts                                           |
| extractor            | Extract knowledge from archive documents                                           |
| fact-check           | Verify factual claims against authoritative sources                                |
| feature-dev          | Test-first feature development workflow                                            |
| flowchart            | Create clear, readable Mermaid flowcharts                                          |
| framework            | Convention reference, categorical imperative                                       |
| garden               | Incremental PKM maintenance (weeding, linking)                                     |
| ground-truth         | Establish ground truth labels for evaluation                                       |
| introspect           | Test framework self-knowledge from session context alone                           |
| learning-log         | Log patterns to thematic learning files                                            |
| osb-drafting         | IRAC analysis for Oversight Board cases                                            |
| pdf                  | Markdown → professional PDF                                                        |
| python-dev           | Production Python (fail-fast, typed, TDD)                                          |
| qa-eval              | Black-box quality assurance for verifying work against specifications              |
| remember             | Persist knowledge to markdown + memory server                                      |
| review               | Assist in reviewing academic work (papers, dissertations, drafts)                  |
| review-training      | Extract training pairs from matched documents                                      |
| session-insights     | Extract accomplishments + learnings; session-end reflection with heuristic updates |
| tasks                | Task lifecycle management                                                          |
| training-set-builder | Build LLM training datasets from documents                                         |
| transcript           | Session JSONL → markdown                                                           |

**Invoke**: `Skill(skill="name")` or via commands that wrap them.

## Hooks

| Hook                          | Trigger          | Purpose                                     |
| ----------------------------- | ---------------- | ------------------------------------------- |
| `sessionstart_load_axioms.py` | SessionStart     | Inject AXIOMS.md, FRAMEWORK.md, HEURISTICS  |
| `user_prompt_submit.py`       | UserPromptSubmit | Prompt hydration + context injection        |
| `hydration_gate.py`           | UserPromptSubmit | Spawn prompt-hydrator for workflow guidance |
| `custodiet_gate.py`           | PostToolUse      | Ultra vires detection (authority checking)  |
| `autocommit_state.py`         | PostToolUse      | Auto-commit state file changes              |
| `router.py`                   | UserPromptSubmit | Intent routing and skill matching           |

See [docs/HOOKS.md](docs/HOOKS.md) for hook architecture.

## Agents

Custom agents spawned via `Task(subagent_type="name")`:

| Agent             | Purpose                                                          |
| ----------------- | ---------------------------------------------------------------- |
| critic            | Second-opinion review of plans/conclusions                       |
| custodiet         | Ultra vires detector - catches agents acting beyond authority    |
| effectual-planner | Strategic planning under uncertainty (NOT implementation)        |
| planner           | Implementation planning with memory context + critic review      |
| prompt-hydrator   | Context gathering + workflow selection (invoked on every prompt) |

Built-in Claude Code agents (also available):

- `Explore` - Fast codebase exploration
- `Plan` - Implementation planning
- `general-purpose` - General tasks (use with `Skill("python-dev")` for Python work)

## Scripts

| Script                     | Purpose                                                     |
| -------------------------- | ----------------------------------------------------------- |
| `regenerate_task_index.py` | Rebuild task index from all `type: task` files in $ACA_DATA |
| `sync_web_bundle.py`       | Sync framework to project repositories                      |

**Run**: `cd $AOPS && uv run python scripts/<script>.py`

## Testing

- **Unit tests**: `tests/` (270 tests, 98% pass)
- **Integration tests**: `tests/integration/` (require Claude CLI)
- **Run**: `uv run pytest tests/`

## Memory Server

Use `mcp__memory__*` tools to store and retrieve memories. Memory server is accessed via remote connection over Tailscale.
