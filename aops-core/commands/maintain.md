---
name: maintain
type: command
category: instruction
description: Surface (don't block) target/prototype graph hygiene issues — missing consequence prose, edges without `why:`, SEV4 weak-prose flags.
triggers:
  - "maintain"
  - "graph hygiene"
  - "anti-inflation"
  - "target hygiene"
  - "consequence audit"
modifies_files: false
needs_task: false
mode: execution
domain:
  - operations
  - planning
allowed-tools: Read, Grep, Glob, Skill, mcp__pkb__list_tasks, mcp__pkb__get_task, mcp__pkb__pkb_context, mcp__pkb__graph_json
permalink: commands/maintain
---

# /maintain — Anti-Inflation Surface

**Purpose**: Run the target/prototype graph-hygiene checks defined by the multi-parent-edges spec and report findings. **Surface only — never block, never auto-fix.** The user (or `planner` in maintain mode) decides whether to act on each finding.

> Spec: `projects/aops/specs/pkb/multi-parent-edges.md` §1.5, §2.3, §2.4, §6 Q4.
>
> Canonical procedure: **`aops-core/skills/planner/SKILL.md` §"Anti-Inflation Surface (Target/Prototype Graph Hygiene)"** (around the `### Anti-Inflation Surface` heading; checks 1–3 are defined verbatim there). This command orchestrates those checks; it does not redefine them.

## Workflow

Invoke the planner skill in **maintain** mode and request the Anti-inflation activity. The planner owns the actual graph-walking logic — `/maintain` is the user-facing entry point that ensures the four hygiene findings are reported in a consistent shape.

```
Skill(skill="planner", args="maintain: anti-inflation")
```

If the planner skill is unavailable, fall back to running the three checks inline by reading frontmatter via `mcp__pkb__list_tasks` and `mcp__pkb__pkb_context`. **Do not call any write tool** (`update_task`, `complete_task`, etc.) — these checks are read-only.

## Findings Format

Report results as four labelled sections. Every section is a **review prompt**, not an action queue. Use the headings below verbatim so downstream tooling and tests can locate them.

### 1. Targets missing `consequence` prose

> Spec: §1.4 mandates `consequence` on every target/prototype. AC#1.

List every `type: target` (or alias `type: goal` per `aops-core/skills/remember/references/TAXONOMY.md`) node whose `consequence` field is empty, missing, or whitespace-only:

```
Targets missing consequence prose (SURFACE):
  - [task-id] [[Title]] — severity: N, goal_type: <committed|aspirational|learning>
```

If none, write `No targets are missing consequence prose.` Do not omit the section.

### 2. `contributes_to` edges missing `why:` / `justification:`

> Spec: §2.3 defers justification enforcement to review skills. AC#2.

List every `contributes_to` edge whose `why:` (alias) and `justification:` (canonical) fields are both missing, empty, or whitespace-only:

```
contributes_to edges missing justification (SURFACE):
  - [source-task-id] → [target-id] (stated_weight: <term>)
```

If none, write `No contributes_to edges are missing justification.` Do not omit the section.

### 3. SEV4 targets with weak consequence prose (advisory heuristic)

> Spec: §1.5 defers semantic checks to review skills. AC#3. Heuristic — the keyword list lives in `aops-core/skills/planner/SKILL.md` under "Severe-state keyword list" and is the SSoT.

For every active `type: target` node with `severity: 4`, scan the `consequence` prose with case-insensitive whole-word matching against the planner's documented severe-state keyword list. If **none** match, surface the target:

```
SEV4 targets with weak consequence prose (advisory — heuristic):
  - [task-id] [[Title]] — consequence: "<first 80 chars>…"
```

False positives are expected. The user decides whether to rewrite or accept. If none, write `No SEV4 targets flagged by the weak-prose heuristic.` Do not omit the section.

### 4. Active SEV4-committed target concurrency

> Spec: §6 Q4. AC#4 — `/maintain` mirrors `/daily`'s warning so the surface is reachable on demand without waiting for the morning briefing.

Count `type: target` nodes where `goal_type: committed`, `severity: 4`, and `status: active` (or any non-terminal status: `queued`, `ready`, `in_progress`). The cap is **2**. If `count > 2`, emit:

```
SEV4-committed concurrency exceeded: N active (cap = 2). Review or downgrade.
```

If `count <= 2`, write `SEV4-committed concurrency within cap (N active, cap = 2).`

## Constraints

- **Surface only.** `/maintain` reports findings; it never edits frontmatter, never moves tasks between statuses, never resolves edges.
- **Do not block.** None of these findings stop tool use anywhere else in the system.
- **Do not duplicate the planner's logic.** If a check needs sharpening, edit `aops-core/skills/planner/SKILL.md` (the SSoT). This command links to the procedure, it does not re-state it.
- **No auto-fix language.** Use "review", "advisory", "consider" — not "fixed", "resolved", "corrected".

## Arguments

- `/maintain` — run all four checks against the entire graph
- `/maintain <project>` — scope to one project (passes `project=<slug>` through to `list_tasks`)

## Relationship to Other Commands

- **`/daily`**: Surfaces AC#4 (SEV4-committed concurrency) once per morning briefing in the Status section. `/maintain` is the on-demand counterpart that also runs AC#1–3.
- **`/q` and `/planning`**: Capture and decomposition. `/maintain` does not file follow-up tasks for findings — that's the user's call.
- **planner `maintain` mode**: Owns the procedures. `/maintain` invokes it.
