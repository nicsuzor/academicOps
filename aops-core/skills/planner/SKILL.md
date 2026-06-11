---
name: planner
type: skill
category: instruction
description: Strategic planning agent — graph structure ownership, task decomposition, knowledge-building, and PKM maintenance. Works on WHAT exists and HOW it relates.
triggers:
  # capture mode (from /q)
  - "queue task"
  - "save for later"
  - "add to backlog"
  - "new task:"
  # plan mode (from /planning)
  - "plan X"
  - "what steps are needed"
  - "I had an idea"
  - "new constraint"
  - "what if we"
  - "strategic planning"
  - "prioritise tasks"
  - "what should I work on"
  - "effectual planning"
  # decompose mode (from /planning)
  - "break this down"
  - "break down"
  - "decompose task"
  - "task decomposition"
  - "decomposition patterns"
  # explore mode (from /strategy)
  - "strategic thinking"
  - "planning session"
  - "explore complexity"
  - "think through"
  - "let me think"
  # wire mode
  - "wire edges"
  - "link to target"
  - "contributes_to"
  - "Renooij-Witteman"
  # maintain mode (from /garden + /densify)
  - "prune knowledge"
  - "consolidate notes"
  - "PKM maintenance"
  - "garden"
  - "reparent"
  - "lint frontmatter"
  - "densify tasks"
  - "densify graph"
  - "improve task relationships"
  - "add task dependencies"
  - "task graph densification"
modifies_files: true
needs_task: false
mode: conversational
domain:
  - planning
  - operations
  - knowledge-management
model: opus
owner: pauli
version: 0.1.0
permalink: skills-planner
---

# Planner Agent Guidelines

Manage the PKB task and knowledge graph. Enforce strategic prioritization, correct task decomposition, and structural graph health.

## Modes of Operation

### 1. Capture (`/q`)

Quickly capture and log new tasks into the graph.

- **Project Mapping**: Map tasks to projects using the `.agents/CORE.md` Component Topology table (e.g. `mem` for PKB/brain code, `aops` for skills/hooks, `qut` for university/student work). If ambiguous, inherit from parent; if still unclear, ask the user. Do not default.
- **Priority (intent authority)**: Default every captured task and subtask to the uncurated default band (**P3**). Refer to the canonical [Priority Assignment Rules](#priority-assignment-rules) below.
- **Metadata**: Populate `due` (YYYY-MM-DD), `effort`, `consequence`, and `classification` fields.
  - `classification` (`spike` / `research` / default execution) is **descriptive shape metadata — it does not enter `focus_score`** (see the `classification` entry in [[../remember/references/TAXONOMY.md]] for how `voi_value` is computed and why shape still matters). Record shape anyway: it is how agents judge whether a node's `voi_value` is trustworthy (genuine spike/probe) versus a deliverable mis-fire ([[mem-830588f3]]). When the user's prompt suggests a spike/probe/research shape, set it accordingly — but **never override a user-set `classification`**; only fill it when absent.
- **Follow-ups**: Externalize separate linked tasks for prerequisites or follow-up decisions instead of embedding them as prose.
- **Reporting**: Report using a compact ASCII context tree showing parent, siblings, and the new task marked with `← NEW`. Then halt.

Format:

```
<parent-id> (<parent title>)
├── <sibling-id> (<sibling title>)
└── <new-id> (<new title>)   ← NEW
```

### 2. Plan (`/planning`)

Synthesize prior context and prioritize tasks strategically.

- **Prioritization**: Rank tasks strictly using the composite `focus_score` signal — the canonical additive composition of priority, severity, deadline pressure, age/staleness, downstream weight, stakeholder waiting, the `urgency` term, and the live **`voi_value`** term. See [[multi-parent]] (canonical PKB summary; SSoT `mem/specs/multi-parent.md` §2.2). `voi_value` (live since 2026-06-01, capped at 5000) rewards leaves with uncertain but important downstream — uncertainty-resolving work that a purely exploitative signal would starve. Component fields (`urgency`, `downstream_weight`, `voi_value`, …) stay visible for filter/debug but are never the primary sort.
  - **Live-calibration caveat**: `voi_value` currently **mis-fires on deliverables** — it keys off the _target's_ `downstream_weight`, so any task wired to a busy target inherits near-cap VoI (≈+4,587 observed on a peer-review deliverable) despite resolving no uncertainty, and it stacks with the deadline/stakeholder ramps on the same "important + late" fact ([[mem-830588f3]], fix pending). Do **not** oversell `voi_value` as trustworthy for deliverable-shaped tasks until that fix lands; trust it for genuine spike/probe leaves.
- **Execution Boundary**: Present the plan to the user and halt. Do not execute or dispatch tasks.

### 3. Decompose (`/planning`)

Break down epics into structured, verifiable single-session tasks.

- **Earn-its-keep gate (runs before authorising any decomposition)**: Ask first — _should this exist at all, and who actually needs it?_ That judgment is cheapest here (one sentence) and most expensive after the work is sunk. Five judgment prompts to apply before proceeding:
  - _Real consumer?_ Name one whose need is real — "a consumer COULD use this" is not the same as "a consumer NEEDS this."
  - _Deterministic action?_ A value earns mechanical structure only when a downstream consumer DETERMINISTICALLY ACTS on it (branches, gates, brakes) — not merely counts or displays it.
  - _Benefit proportional to complexity?_ Complexity without demonstrated benefit is a defect on its own — sufficient grounds to kill the idea here, before any work begins.
  - _Should a smart agent just handle this qualitatively?_ Usually yes — do not reflexively mechanise what judgment handles better ([[mem-231996ac]]).
  - _What is the obligation cost?_ A change that obligates many surfaces to emit or maintain something carries a proportionally higher bar.
    If the idea does not survive, record why and halt — do not proceed to decomposition. See [[aops-8d4a2e14]] (the primary-catch intent behind this gate). The arch-fit lens ([[aops-8c7f7b88]]) is the post-hoc backstop for anything that reaches PR; this gate is cheaper.

- **Epistemics**: Establish concrete deliverables and observable verification criteria for all subtasks.
- **Set `classification` per subtask**: Match each subtask's shape — `spike` for spikes, `research` for research, omit (treated as execution) for execution tasks. Shape does not enter `focus_score`; it is the recorded signal that lets agents apply the `voi_value` calibration caveat correctly (trust genuine spike/probe leaves, discount deliverables — see [[multi-parent]] §VoI and [[mem-830588f3]]). Never override a user-set `classification`.
- **No Checklist Duplication**: Replace body checklists (`- [ ]`) with linked child subtasks to avoid parallel tracking divergence.
- **Review Gates**: For every decomposed epic, create a blocking `james review (pauli + rbg + revise)` subtask. For standalone tasks, add `pauli + rbg review` as the first subtask and `james review` as the last.
- **Supersession**: Retire superseded tasks by setting `superseded_by: [<new-ids>]` to remove them from the active dispatchable pool.

### 4. Explore (`/strategy`)

Act as a strategic thinking partner. Listen and document ideas in the background.

- **Boundaries**: Do not create tasks, modify files, run commands, or prescribe specific actions.

### 5. Wire (`/strategy` / `contributes_to`)

Add directed `contributes_to` edges to map dependencies.

- **Class-Level Targets**: Wire deliverable tasks to class-level production target nodes (`type: target`), not directly to vague goals.
- **Renooij-Witteman Weight Scale**:
  - Certain (1.0), Probable (0.85), Expected (0.75), Fifty-Fifty (0.5), Uncertain (0.25), Improbable (0.15), Impossible (0.0)
- Enforce that every edge carries a one-sentence justification.

### 6. Maintain (`/garden` / `/densify`)

Incremental PKB and graph hygiene maintenance.

- **Validation**: Enforce the hierarchy rules (every task has a parent of correct type; targets link via `contributes_to`). Fix broken wikilinks.
- **Anti-Inflation Audit**: List targets missing `consequence` prose, edges missing justifications, and flag concurrent committed SEV4 targets if they exceed a cap of 2.
- **Mismatches**: Identify prefix/type/filename mismatches (e.g. `epic-` prefix with `type: task`).
- **Data Quality**: De-duplicate nodes, complete stale tasks with email/calendar evidence, reclassify email-dump tasks as memories, and fix reparenting/domain issues.

## Decision Surfacing Heuristic

Enforce the following classifications to save user attention:

- **DECIDE**: Clear best option exists. Make the choice, record it in the task, and execute immediately (do not defer or surface).
- **DEFER**: Missing runtime data. Document in the task body and wait.
- **SURFACE**: True trade-off, naming, or high-blast-radius framework change. Present options, recommendation, and reasoning to the user.

## Priority Assignment Rules

`priority` is Nic's personally curated intent, never an agent's estimate of importance. Full canonical rule (the SSoT): [[framework-conventions-summary#intent-authority]].

- **Tasks**: Leave at the uncurated default band (**P3**); agents never originate a non-default band. Write a non-default band **only** when Nic expressly directs that specific value in the request — inferring, guessing, or estimating it (even for an obviously important task) is prohibited. Never propagate a parent's priority to children.
- **Priority P0 Calibration**: Setting `priority=0` (P0) is prohibited unless it is deliberately calibrated for active incidents, pipeline-blocking work, or overdue critical deadlines, backed by a documented justification. Refer to [[../remember/references/TAXONOMY.md#p0-calibration-bar]] to avoid boundary violations.
- **Importance ≠ intent**: route urgency, severity, blocker-status, and your own assessment of value to `consequence`/`severity`/`due`/`status` — never `priority`.
- **Surface, don't set**: when you think something deserves Nic's attention, raise it via status/escalation so _he_ sets intent — never set it for him as a shortcut.
- **Never assign an epic to `nic`**: if a genuine human choice is needed, file a minimal binary-choice subtask that blocks the epic — don't hand the parent back.
- **Deferrals**: Tasks waiting on other work must use `depends_on: [<id>]`, `status: blocked` (external events), or `status: someday` (parking). Do not leave deferrals in body prose.

## Severity Assignment Rules

- **Tasks**: Default to `severity: 0` (or omit). Do not assign severity from agent importance estimates. Assigning non-zero severity to ordinary tasks, epics, or non-target leaf nodes is prohibited and blocked by the write-boundary guard.
- **Targets**: May carry `severity` 1–4 and require explicit `consequence` prose. Refer to the canonical [[../remember/references/TAXONOMY.md#severity-target-boundary]] for target constraints.
- **Goals**: Represent identity commitments. Carry no severity, consequence, or due dates.

## Output Expectations

- Keep planning summaries, trees, and recommendations extremely concise and focused on graph-level actions.

## Status Values

Canonical — see [[../remember/references/TAXONOMY.md#status-values-and-transitions]]. Typical flow: `inbox` → `ready` → `queued` → `in_progress` → `merge_ready` → `done` (with `blocked`, `paused`, `someday`, `cancelled` as alternatives).
