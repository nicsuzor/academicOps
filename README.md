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

## Quick Start

```bash
# Required environment variables (add to ~/.bashrc or ~/.zshrc)
export AOPS="$HOME/src/academicOps"
export ACA_DATA="$HOME/writing/data"

# MCP server tokens (for GitHub and memory server authentication)
export GH_MCP_TOKEN="your-github-copilot-mcp-token"
export MEMORY_MCP_TOKEN="your-memory-server-token"

./setup.sh  # Creates ~/.claude/ symlinks, substitutes tokens into MCP config
```

**Core docs** (injected at session start):

- [AXIOMS.md](AXIOMS.md) - Inviolable principles
- [HEURISTICS.md](HEURISTICS.md) - Empirically validated rules
- [FRAMEWORK-PATHS.md](FRAMEWORK-PATHS.md) - Paths and configuration (generated)

## Architecture

The framework uses a **core + archived** structure:

- **Core plugin** (`plugins/aops-core/`): Minimal proven components with mechanical enforcement
- **Archived** (`archived/`): Non-core components preserved for reference

### Core Components (~30 files)

| Category   | Components                                                        |
| ---------- | ----------------------------------------------------------------- |
| Skills (6) | tasks, remember, python-dev, feature-dev, framework, audit        |
| Agents (4) | planner, prompt-hydrator, critic, custodiet                       |
| Hooks (3)  | router.py, unified_logger.py, user_prompt_submit.py               |
| Governance | 7 enforced axioms, 4 enforced heuristics (with mechanical checks) |

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

### Core Skills (Active)

| Skill       | Purpose                                                       |
| ----------- | ------------------------------------------------------------- |
| audit       | Comprehensive framework governance (structure, justification) |
| feature-dev | Test-first feature development workflow                       |
| framework   | Convention reference, categorical imperative                  |
| python-dev  | Production Python (fail-fast, typed, TDD)                     |
| remember    | Persist knowledge to markdown + memory server                 |
| tasks       | Task lifecycle management                                     |

### Archived Skills

Additional skills are preserved in `archived/skills/` for reference and potential reactivation:
analyst, annotations, convert-to-md, daily, dashboard, debug-headless, excalidraw, extractor, fact-check, flowchart, garden, ground-truth, introspect, osb-drafting, pdf, qa-eval, review, review-training, session-insights, training-set-builder, transcript

## Agents

### Core Agents (Active)

| Agent           | Purpose                                               |
| --------------- | ----------------------------------------------------- |
| prompt-hydrator | Context gathering + workflow selection (every prompt) |
| custodiet       | Ultra vires detector - authority checking             |
| critic          | Second-opinion review of plans/conclusions            |
| planner         | Implementation planning with memory + critic review   |

### Archived Agents

Preserved in `archived/agents/`: effectual-planner, framework-executor

## Infrastructure

- **Hooks**: Event-driven context injection (`hooks/`)
- **Skills**: Workflow instructions (`skills/`) - invoke via `Skill` tool
- **Memory**: `mcp__memory__*` tools for knowledge persistence
- **Plugin**: Core components bundled in `plugins/aops-core/`

See [[RULES.md]], [[WORKFLOWS.md]], [[VISION.md]] for details.
