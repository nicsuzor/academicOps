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

**Last updated**: 2026-03-20

> **Why this file matters**: Agents have no persistent memory. VISION.md defines the end state — what we're building and why. Update when fundamental direction changes. Keep out: implementation details, current status.

## Research Programme

We are studying how knowledge workers — academics in particular — integrate AI into daily professional life while maintaining epistemic integrity.

We distinguish between **tool capability** (executing tasks) and **quality assurance** (evaluating and relying on generated outputs). Tool capabilities are improving rapidly. What doesn't go away is the need for the knowledge worker to assure themselves that the work is right and that the _right work_ is being done.

The key value the framework provides: **you can delegate execution to AI without delegating judgment**. The framework is the structural guarantee that academic integrity obligations are enforced at the right moments — even when the human isn't paying attention.

The framework itself is the research instrument. We dogfood it daily, observe where quality assurance breaks down, and evolve in response.

## What This Is

A lightweight automation framework for academic work. academicOps has four layers:

### 1. Task management (the foundation)

The task system is the backbone. Everything flows through it.

- **Hierarchical task graph**: Goal → Project → Epic → Task → Action
- **PKB server** (Rust): semantic search, graph store, task CRUD, memory — single binary, deployed everywhere
- **Task lifecycle**: capture → decompose → prioritise → execute → verify → complete
- **Zero-friction capture**: ideas flow from any input (voice, email, notes, conversation) into the task graph

### 2. Skills (how work gets done)

Skills are Claude Code extensions that know how to do specific things. Core skills handle framework operations (daily notes, task management, planning, reflection). Domain skills handle academic work (citations, PDF generation, email triage, data analysis).

- Skills are modular — each works independently
- Domain skills are **fungible** — they exist only because no better external solution exists yet, and are designed to be replaced
- Skills compose into workflows but don't prescribe sequence

### 3. Async quality assurance (GitHub as coordination layer)

GitHub serves as the coordination layer for agents and humans. PR pipelines run review workflows asynchronously after work is submitted. This catches what real-time enforcement misses and provides the audit trail.

- PR pipeline: lint → agent review → merge prep → human approval
- CI/CD enforces structural checks
- Polecat workers can execute tasks via GitHub Issues (experimental)

### 4. Session infrastructure

Hooks and configuration that make every Claude Code session framework-aware:

- SessionStart loads principles and context
- Autocommit keeps state synced
- Session transcripts captured for reflection
- Cross-device sync via git

## What We've Learned

The framework has a recurring failure mode: **over-engineering coordination mechanisms that cost more to maintain than the problems they solve.** We've reset twice now (Jan 2026, March 2026).

**The pattern**: Building elaborate coordination infrastructure to control agent behaviour, when the actual value comes from (a) good task management, (b) good skills, and (c) review at boundaries.

**What we've definitively cut:**

- **Workflow obligation profiles**: The "integrity obligation profiles with composable overlays" framing. Academically interesting, practically unused.
- **Enforcement ladder**: Graduated enforcement spec with 7 levels. Over-engineered for the problem.

**What we're re-evaluating (not cut, but need to earn their keep):**

- **Hydrator**: Good concept (enrich tasks with context before execution). Enforcement gate (blocking all tools until hydrated) is the problem, not the skill itself. Needs to be useful without being mandatory for simple tasks.
- **Custodiet**: Drift detection concept is sound. Needs evidence it catches things that async PR review wouldn't.
- **Gate system**: Per-gate assessment needed. Commit gate (preventing stranded work) is valuable. Hydration gate (blocking all tools) is too aggressive.

**How we prevent this recurring:**

- Every component has a feature node in the PKB with user stories, AC, and assessment criteria
- Assessment criteria: used without enforcement? reduces real friction? agents understand it? survives neglect?
- Components that fail assessment get flagged during normal work, not in dramatic resets
- See epic `academicops-a442fd70` in PKB for the living component registry

## Knowledge Architecture

### Repository Model

| Repo          | Purpose             | Sharing                   |
| ------------- | ------------------- | ------------------------- |
| `$AOPS/`      | Framework machinery | Public (no personal data) |
| `$ACA_DATA/`  | Personal knowledge  | Never shared              |
| Project repos | Code + docs         | Collaborators only        |

### Design Principle: Dumb Server, Smart Agent

The PKB server does deterministic computation (search, CRUD, graph traversal). All judgment lives in the LLM. The server never decides what's important, relevant, or correct — it returns data and the agent interprets it.

## Success Criteria

1. **Zero-friction capture** — Ideas flow from any input to organized context
2. **Fit-for-purpose output** — Work serves the person it was made for, evaluated qualitatively
3. **Nothing lost** — Tasks tracked, knowledge searchable, context surfaces when needed
4. **Fail-fast** — Problems caught immediately, no silent failures
5. **Minimal maintenance** — Framework doesn't require constant babysitting
6. **Right work, done well** — Quality assured at boundaries, not by controlling execution

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

- Autonomous research decisions
- Replacing expert judgment
- Speed over quality
- Generic/formulaic output
- Coordination infrastructure that costs more than it saves

## Design Philosophy

1. **Qualitative over quantitative** — Evaluate fitness-for-purpose, not compliance with templates
2. **Delegate agency** — Specify WHAT and WHY, not HOW. Trust agents.
3. **Fail-fast** — No defaults, no silent failures
4. **Modular** — Each component works independently, composes when needed
5. **Minimal** — Fight bloat aggressively. A working simple system beats an elegant complex one.
6. **Dogfooding** — Use real work as the test case. The framework improves as a side-effect of doing normal academic work, not through dedicated framework-building sessions.
7. **Core vs. fungible** — Task management, memory, and QA infrastructure are core. Domain skills are replaceable. The framework should shrink when external tools improve.
8. **Components earn their keep** — Every component is assessed against clear criteria (used voluntarily? reduces friction? agents understand it? survives neglect?). Components that fail get flagged and fixed or removed. See PKB epic `academicops-a442fd70`.
9. **Learn from resets** — When the framework gets too complex, understand why. Document the pattern, not just the cut. The "What We've Learned" section is as important as the architecture.
