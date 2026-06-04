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
- **Priority**: Default all captured tasks and subtasks to **P3**. Only assign P0–P2 if the user explicitly requests it.
- **Metadata**: Populate `due` (YYYY-MM-DD), `effort`, `consequence`, and `classification` (e.g., `spike`, `research`, or default execution) fields.
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

- **Prioritization**: Rank tasks strictly using the composite `focus_score` signal (which aggregates priority, age, and severity).
- **Execution Boundary**: Present the plan to the user and halt. Do not execute or dispatch tasks.

### 3. Decompose (`/planning`)

Break down epics into structured, verifiable single-session tasks.

- **Epistemics**: Establish concrete deliverables and observable verification criteria for all subtasks.
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

## Decision Surfacing Rules

Enforce the following classifications to save user attention:

- **DECIDE**: Clear best option exists. Make the choice, record it in the task, and execute immediately (do not defer or surface).
- **DEFER**: Missing runtime data. Document in the task body and wait.
- **SURFACE**: True trade-off, naming, or high-blast-radius framework change. Present options, recommendation, and reasoning to the user.

## Priority & Severity Assignment Rules

- **Tasks**: Default to **P3** and `severity: 0` (or omit). Do not assign high priority/severity to tasks based on agent importance estimates.
- **Targets**: May carry `severity` 1–4 and require explicit `consequence` prose.
- **Goals**: Represent identity commitments. Carry no severity, consequence, or due dates.
- **Deferrals**: Tasks waiting on other work must use `depends_on: [<id>]`, `status: blocked` (external events), or `status: someday` (parking). Do not leave deferrals in body prose.

## Output Expectations

- Keep planning summaries, trees, and recommendations extremely concise and focused on graph-level actions.

## Status Values

Canonical — see [[../remember/references/TAXONOMY.md#status-values-and-transitions]]. Typical flow: `inbox` → `ready` → `queued` → `in_progress` → `merge_ready` → `done` (with `blocked`, `paused`, `someday`, `cancelled` as alternatives).
