---
title: Automation Framework Vision
type: note
category: spec
permalink: aops-vision
tags:
  - framework
  - vision
  - planning
---

# academicOps Vision

**Last updated**: 2026-02-19

> **Why this file matters**: Agents have no persistent memory. VISION.md defines the end state - what we're building and why. Update when fundamental direction changes (rare). Keep out: implementation details, current status.

## What This Is

A constitutional automation framework for academic work. academicOps operates through four mechanisms:

### 1. Synchronous workflow enforcement (local, real-time)

In every local session, the framework defines and enforces universal and modular workflows. Hooks, the hydrator, and custodiet ensure agents use the skills we provide and follow the procedures we define — in real time, as work happens.

- SessionStart loads principles ([[AXIOMS.md|AXIOMS]], [[HEURISTICS.md|HEURISTICS]])
- Prompt hydration transforms terse inputs into structured execution plans
- Custodiet detects drift and scope violations during execution
- Workflows embed quality gates appropriate to each task type

### 2. Asynchronous quality assurance (GitHub as automation hub)

GitHub serves as the coordination layer for agents and humans. PR pipelines run automated review workflows — strategic review, custodiet compliance, QA verification — asynchronously after work is submitted. This catches what synchronous enforcement misses and provides the audit trail.

- PR Pipeline: Setup → Strategic Review → Custodiet → QA → Ready for Review
- Polecat workers execute tasks autonomously via GitHub Issues
- CI/CD enforces linting, type checking, and gatekeeper checks

### 3. Baseline capabilities (tasks, memory, management)

The framework provides infrastructure that every session and every project depends on:

- **Task system** — hierarchical task graph with dependencies, decomposition, and lifecycle tracking
- **Memory server** — semantic search over institutional knowledge, persisted across sessions
- **Knowledge architecture** — three-repo model (`$AOPS/` public framework, `$ACA_DATA/` private knowledge, project repos)

### 4. Domain-specific academic tools

Generic but academically-focused capabilities that support research workflows:

- Citation management (zotmcp + Zotero)
- Research data analysis (/analyst skill + dbt + Streamlit)
- Document conversion and PDF generation
- Email triage and task capture
- Writing style enforcement

**Scope**: Supports academic work across ALL repositories.

## Core Architecture: Prompt Hydration

Every user prompt is hydrated before execution:

```
PROMPT → HYDRATE → EXECUTE (following plan)
```

### HYDRATE (prompt-hydrator agent)

**Purpose**: Transform terse prompt into a complete execution plan

The hydrator receives the user prompt along with session history and memory context, then outputs:

1. **Intent**: What the user actually wants
2. **Workflow**: Which workflow template applies
3. **TodoWrite Plan**: Concrete steps with per-step skill assignments
4. **Guardrails**: Constraints based on workflow + domain

### Key Principles

1. **Single decision point** — Hydrator makes all routing/skill decisions upfront
2. **Skills match per-step** — Each step can invoke its own skill
3. **Workflows define quality** — Each workflow embeds appropriate CHECKPOINTs
4. **Agent follows plan** — Main agent executes steps without re-deciding

## Knowledge Architecture

### Repository Model

| Repo          | Purpose             | Sharing                   |
| ------------- | ------------------- | ------------------------- |
| `$AOPS/`      | Framework machinery | Public (no personal data) |
| `$ACA_DATA/`  | Personal knowledge  | Never shared              |
| Project repos | Code + docs         | Collaborators only        |

### Information Flow

```
Session Start → AXIOMS + HEURISTICS + CORE loaded
Every Prompt  → HYDRATE (context) → ROUTE (workflow) → ORCHESTRATE (steps)
Each Step     → Skill matched JIT → Execute → Verify
Session End   → Knowledge extracted → Memory persisted
```

- **Session start**: Principles and user context loaded via SessionStart hook
- **Every prompt**: Three-stage pipeline ensures appropriate handling
- **Each step**: Skills matched just-in-time based on step's domain
- **Session end**: Decisions and learnings captured to knowledge base

## Success Criteria

1. **Zero-friction capture** - Ideas flow from any input (voice, email, notes) to organized context
2. **Consistent quality** - Writing matches style guide, citations formatted correctly
3. **Nothing lost** - Tasks tracked, knowledge searchable, context surfaces when needed
4. **Fail-fast** - Problems caught immediately, no silent failures
5. **Minimal maintenance** - Framework doesn't require constant babysitting

## Constraints

### Must Work Within

- Solo academic schedule (fragmented time, context switching)
- ADHD accommodations (zero-friction, clear boundaries)
- Cross-device workflow (multiple computers)
- Private data (secure and confidential)
- Academic standards (publication-quality required)

### Must Not Require

- Extensive configuration
- Manual maintenance
- Perfect inputs
- Full-time developer support

## Non-Goals

- ❌ Autonomous research decisions
- ❌ Replacing expert judgment
- ❌ Speed over quality
- ❌ Generic/formulaic output

## Design Philosophy

1. **Fail-fast** - No defaults, no silent failures, demand explicit configuration
2. **Modular** - Each component works independently, composes into workflows
3. **Minimal** - Fight bloat aggressively, one golden path
4. **Dogfooding** - Use real research projects as test cases

## Self-Curating Framework

The framework should become increasingly self-aware and self-improving:

1. **Agent-ready instructions** - Core docs ([[AXIOMS.md|AXIOMS]], [[HEURISTICS.md|HEURISTICS]]) contain only actionable rules, no explanations or evidence
2. **Evidence-informed changes** - Framework changes are motivated by consolidated diagnostic data, not ad-hoc observations
3. **Closed-loop learning** - Observations → bd issues → Diagnostics → Changes → Validation
4. **Framework introspection** - The [[archived/specs/framework-skill.md|framework skill]] understands the whole system and enforces consistency before accepting additions
5. **Bounded growth** - Logs don't grow forever; they consolidate into actionable diagnostics then archive
6. **Session-end reflection** - At session end, automatically analyze behavior patterns and suggest heuristic updates. User approves with one click, no manual observation writing. Zero friction for framework improvement.
