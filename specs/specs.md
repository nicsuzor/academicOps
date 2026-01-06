---
title: Technical Specifications
permalink: aops-specs
type: index
category: spec
tags: [aops, specs, architecture, design]
---

# Technical Specifications

**Status**: Index file (always current)

## Spec Organization

```mermaid
graph TD
    A[Specs Index] --> B[Core Architecture]
    A --> C[Agent Behavior]
    A --> D[Features]
    A --> E[Infrastructure]
    A --> F[Skills]

    B --> B1[meta-framework]
    B --> B2[enforcement]
    B --> B3[knowledge-management-philosophy]

    C --> C1[prompt-hydration]
    C --> C2[ultra-vires-custodiet]

    D --> D1[dashboard-skill]
    D --> D2[task-list-overwhelm]

    E --> E1[framework-health]
    E --> E2[testing-framework-overview]

    F --> F1[analyst-skill]
    F --> F2[framework-skill]
    F --> F3[session-insights-skill]
    F --> F4[tasks-skill]
```

Design documents for the academicOps framework. Per [[AXIOMS]] #29: one spec per feature, timeless.

## Spec Lifecycle

| Status | Meaning |
|--------|---------|
| `draft` | In development, not yet approved |
| `approved` | Approved design, awaiting implementation |
| `implemented` | Built and working |
| `requirement` | User story, not yet designed |

## Core Architecture

- [[meta-framework]] - Strategic partner design (implemented)
- [[knowledge-management-philosophy]] - Everything capture, just-in-time delivery
- [[enforcement]] - Enforcement layers and mechanisms
- [[spec-maintenance]] - Ensure specs remain single source of truth (implemented)

## Agent Behavior

- [[specs/prompt-hydration]] - Context gathering, classification, workflow selection (draft)
- [[ultra-vires-custodiet]] - Semantic authority enforcement (draft)
- [[conclusion-verification-hook]] - Verify claims have evidence (draft)
- [[plan-quality-gate]] - Critic review before presenting plans (requirement)
- [[framework-aware-operations]] - Agents know framework architecture (requirement)

## Features

- [[task-list-overwhelm]] - Task state index and synthesis (in progress)
- [[session-transcript-extractor]] - Generate readable transcripts (implemented as /transcript skill)
- [[parallel-batch-command]] - Parallel file processing (implemented as /parallel-batch skill)
- [[email-to-tasks-workflow]] - Email to task extraction (draft)
- [[tasks-mcp-server]] - Task CRUD via MCP (draft)

## Infrastructure

- [[framework-health]] - Health metrics, pre-commit hooks, CI/CD enforcement (implemented)
- [[testing-framework-overview]] - Test types and requirements
- [[multi-terminal-sync]] - Cross-device state sync (requirement)
- [[informed-improvement-options]] - Context7 + research before fixes (requirement)

## Skills

- [[analyst-skill]] - dbt/Streamlit data analysis with transformation boundaries (implemented)
- [[dashboard-skill]] - Cognitive load dashboard for task and session monitoring (implemented)
- [[framework-skill]] - Categorical governance for framework changes (implemented)
- [[garden-skill]] - Incremental PKM maintenance (weeding, linking, synthesizing) (implemented)
- [[python-dev-skill]] - Fail-fast Python with type safety (implemented)
- [[feature-dev-skill]] - Test-first development workflow (implemented)
- [[remember-skill]] - Knowledge persistence to markdown + memory server (implemented)
- [[session-insights-skill]] - Session mining and heuristic evolution (implemented)
- [[supervisor-skill]] - Multi-agent orchestration with quality gates (implemented)
- [[tasks-skill]] - Task lifecycle management (implemented)
- [[transcript-skill]] - JSONL to markdown session transcripts (implemented)
- [[learning-log-skill]] - Pattern documentation via GitHub Issues (implemented)
