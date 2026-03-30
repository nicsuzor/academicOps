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

### The planning insight

The framework's distinctive contribution is **rigorous, emergent, just-in-time planning in environments of high uncertainty**. Academic research operates under genuine uncertainty — not risk (known probability distribution) but uncertainty (unknown unknowns). Traditional project management assumes you know what needs doing and just need to schedule it. Research doesn't work like that. The question changes as you learn. The methodology adapts to what the data reveals. Parallel threads converge in ways you couldn't predict at the start.

AI agents make this worse, not better, by default. Agents are biased toward action — they want to DO things, fast. Research requires the opposite: careful, laborious, iterative decomposition where you figure out what you don't know before you commit to a path. The framework's job is to ensure that planning is at least as rigorous as execution — that tasks are decomposed to an appropriate level _before_ an agent picks them up, that parallel threads are brought back together, and that momentum is maintained without sacrificing depth.

This means the decomposition and planning layer is not overhead — it IS the value. A well-decomposed task graph, where every decision is gated on evidence and every thread has a convergence point, is the primary mechanism by which the framework ensures research quality. The QA lenses verify after the fact; the planning prevents errors before they happen.

### Academic QA is fundamentally different from code QA

Code errors are cheap, testable, and reversible (revert the PR). Academic errors are expensive, hard to detect, and often irreversible (wrong methodology → wasted compute → wrong conclusions; hallucinated references → retracted paper). Agents default to "fast and plausible" — they'll justify a single-pass analysis, skip variance testing, and produce flowing prose with fabricated citations.

**The framework's central QA mechanism is composable review.** Different types of academic work require different review lenses. A methodology design needs adversarial methodological critique. Citation-heavy writing needs systematic source verification. Draft emails need tone and alignment review. Student marking needs consistency and rubric fidelity review. No single review process fits all academic work.

The framework provides:

1. **A library of review lenses** — independent, composable review agents that each bring a specific critical perspective (methodology critique, citation verification, argument review, voice review, etc.)
2. **Review-aware decomposition** — the planner always builds appropriate review tasks into the task graph based on the type of work being decomposed
3. **Human judgment at decision points** — reviews surface issues; the human decides what to do about them

This is not the old enforcement infrastructure (custodiet, gates, obligation profiles). Review lenses are invoked as tasks in the graph, not as hooks blocking execution. They compose like workflow steps, not like compliance checks.

The framework itself is the research instrument. We dogfood it daily, observe where quality assurance breaks down, and evolve in response.

## What This Is

A lightweight automation framework for academic work. academicOps has four layers:

### 1. Task management (the foundation)

The task system is the backbone. Everything flows through it.

- **Hierarchical task graph**: Project → Epic → Task → Action (goals link via `goals: []` metadata)
- **PKB server** (Rust): semantic search, graph store, task CRUD, memory — single binary, deployed everywhere
- **Task lifecycle**: capture → decompose → prioritise → execute → verify → complete
- **Zero-friction capture**: ideas flow from any input (voice, email, notes, conversation) into the task graph

### 2. Skills (how work gets done)

Skills are Claude Code extensions that know how to do specific things. Core skills handle framework operations (daily notes, task management, planning, reflection). Domain skills handle academic work (citations, PDF generation, email triage, data analysis).

- Skills are modular — each works independently
- Domain skills are **fungible** — they exist only because no better external solution exists yet, and are designed to be replaced
- Skills compose into workflows but don't prescribe sequence

### Agents as domain experts (the bazaar model)

Instead of loading different rule files into a general-purpose agent based on detected context, the framework uses **specialist agents with embedded domain expertise**. Each agent carries its own principles and applies them to any work type — planning, reviewing, or executing.

- **Academic integrity**: the research skill owns academic rules (citation, data immutability, methodology ownership)
- **Engineering standards**: the dev-standards agent owns development rules (fail-fast, DRY, version control, credential isolation)
- **Framework operations**: the framework-ops agent owns framework rules (dogfooding, skills read-only, no workarounds, agentic-first)
- **Universal axioms**: always active, loaded at session start for all agents

You invoke the right agents for the job. Rules live local to the entity that enforces them, not in central files that need a context-detection mechanism to load. This is the bazaar model (P#49) applied to governance: multiple independent agents with their own perspective, rather than one central agent switching modes.

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
- **Intentions infrastructure**: Three disconnected priority systems (P0-P4 priority, `intentions.yaml`, daily "My priorities") caused confusion. Consolidated to one signal: PKB priority is the sole ranking signal, daily note "My priorities" is the SSoT for today-specific focus. `/intend` command removed, `intentions.yaml` deleted.

**What we're re-evaluating (not cut, but need to earn their keep):**

- **Hydrator**: Good concept (enrich tasks with context before execution). Enforcement gate (blocking all tools until hydrated) is the problem, not the skill itself. Needs to be useful without being mandatory for simple tasks.
- **Custodiet**: Drift detection concept is sound. Needs evidence it catches things that async PR review wouldn't.
- **Gate system**: Per-gate assessment needed. Handover gate (requires reflection) is valuable. Commit gate was removed because it competed with handover signals. Hydration gate (blocking all tools) is too aggressive.

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
10. **Skills express philosophy, not procedures** — Skill instructions should explain the goal and trust the agent to figure out how to achieve it. Do not write skills as restrictive mode-selection routers with rigid taxonomies. A feature is a feature — it exists for a reason, expressed as user stories. QA should demonstrate whether a feature in actual use achieves its goals, whether that means analyzing transcripts, driving a browser, reviewing logs, or inspecting output. The skill describes what "good" looks like; the agent decides how to get there.
