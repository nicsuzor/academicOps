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
./setup.sh  # Creates ~/.claude/ symlinks
```

**Core docs** (injected at session start):

- [AXIOMS.md](AXIOMS.md) - Inviolable principles
- [HEURISTICS.md](HEURISTICS.md) - Empirically validated rules
- [FRAMEWORK.md](FRAMEWORK.md) - Paths and configuration

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

## Agents

| Agent             | Purpose                                               |
| ----------------- | ----------------------------------------------------- |
| prompt-hydrator   | Context gathering + workflow selection (every prompt) |
| custodiet         | Ultra vires detector - authority checking             |
| critic            | Second-opinion review of plans/conclusions            |
| planner           | Implementation planning with memory + critic review   |
| effectual-planner | Strategic planning under uncertainty                  |

## Architecture

- **Hooks**: Event-driven context injection (`hooks/`)
- **Skills**: Workflow instructions (`skills/`) - invoke via `Skill` tool
- **Memory**: `mcp__memory__*` tools for knowledge persistence

See [[RULES.md]], [[WORKFLOWS.md]], [[VISION.md]] for details.
