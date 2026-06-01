---
name: taxonomy
title: Taxonomy — Canonical Definitions
type: reference
category: framework
description: Single source of truth for all framework concepts and their relationships
permalink: taxonomy
tags: [framework, taxonomy, canonical, reference]
---

# Taxonomy: Canonical Definitions

This document is the **single authoritative source** for all framework concepts. Every other document in the framework MUST use these terms consistently. When in doubt, this document wins.

---

## Core Principle: All Nodes Are One Object

Every node in the PKB is the same fundamental data structure. There is no structural difference between an "epic" and a "task" at the data level — both are graph nodes with the same fields and computed properties. The structural task-vs-epic distinction is removed; both are "tasks that may parent tasks."

**Labels** are **views on computed property ranges**, not structural types assigned to fixed tree depths. A task may be a leaf node or a parent node based on its scope and uncertainty — not because it happens to live at depth 3.

This matters because work decomposition is self-similar: decomposing a top-level parent task looks exactly like decomposing a leaf task. The stopping condition is residual uncertainty, which is a property of the node, not a function of its depth.

> **"Project" is not a hierarchy level.** See [Project (operational routing field)](#project-operational-routing-field) below — it is a polecat repo slug carried as task metadata, not a node type.

---

## The Compression Model

The task graph has intrinsic complexity — the full specification of all work, dependencies, and context. The hierarchy's job is to **compress** this into something that fits through the bottleneck of human working memory.

A flat todo list is a fixed-rate code: it treats every item as having the same complexity. The hierarchy is a **variable-rate code** that allocates more structure to high-complexity work and less to simple work.

Each level resolves a different kind of uncertainty:

| Level       | Uncertainty resolved         | Remaining uncertainty          |
| ----------- | ---------------------------- | ------------------------------ |
| Target      | What success looks like      | Which bodies of work to pursue |
| Parent Task | What to do and in what order | How to execute each step       |
| Task        | What to execute              | Nothing — ready to act         |

Targets stand outside the tree — they are strategic priorities linked to work via metadata, not parent edges. Within the tree, decomposition is `TASK → TASK → … → LEAF TASK`, nestable to whatever depth uncertainty demands.

**Compression principle**: Each level must be self-contained. Understanding a node should not require holding its grandparent's context in working memory. If it does, the decomposition has failed — information is leaking across compression boundaries.

---

## Core Computed Properties

Every node carries three core computed properties that drive both label assignment and tooling:

### scope

**What it measures**: Subtree size — the total count of descendants.

**How computed**: Recursive count of all children, grandchildren, etc., via Parent edges (with a cycle guard for invalid Parent cycles).

**What it tells you**: How much work lives under this node. High scope = strategic container. Low scope = leaf-level work.

### uncertainty

**What it measures**: Residual ambiguity — how much is still unknown about what exactly needs to be done. Range: `0.0` (fully specified) to `1.0` (vague).

**How computed**: Composite signal from:

- `has_children`: decomposed nodes have lower uncertainty than undecomposed equivalents at the same scope (high-scope nodes may still remain above task thresholds even when decomposed)
- `has_acceptance_criteria`: explicit success criteria reduce uncertainty
- `dep_resolution_ratio`: fraction of dependencies that are resolved
- `body_length`: fuller description signals more specified intent
- explicit confidence override: author can pin uncertainty directly

**What it tells you**: Whether a node is ready to act on. Low uncertainty = can execute. High uncertainty = needs more thinking or decomposition.

### criticality

**What it measures**: Impact on goal achievement — how much this node matters relative to the rest of the graph.

**How computed**: Normalized composite of:

- `downstream_weight` (internal input): count of nodes that depend (transitively) on this one completing — fed into `criticality`, not surfaced as a user-facing scalar
- `pagerank`: structural influence in the dependency graph
- `stakeholder_exposure`: explicit priority/stakeholder signals

**What it tells you**: Which nodes to work on first when time is scarce. High criticality = unblocks many downstream nodes. Low criticality = isolated or terminal work.

> **Note**: For user-facing prioritisation and ranking, use `focus_score` — the canonical composite that embeds severity, priority, `urgency` (deadline slack + decay), `downstream_weight`, stakeholder waiting, and `criticality`. See [[multi-parent]] §7 for the full model. Component fields (`urgency`, `downstream_weight`, `criticality`) remain visible in metadata for filtering and debugging, but should never be the headline ranking signal — ranking always goes through `focus_score`.

### depth and leaf

- **depth**: Distance from root (parent chain walk). Advisory — does not determine label.
- **leaf**: Boolean. True when the node has no children AND uncertainty is low. A structural indicator of decomposition completeness — not sufficient for execution readiness (which also requires resolved DependsOn edges).

---

## Labels as Property Ranges

These ranges map conventional labels to computed property values. They are **guidelines for navigation, not enforcement gates**. Tooling uses these to present a sensible default view; the properties drive actual scheduling.

| Label           | Scope | Uncertainty | Typical behaviour                                                                    |
| --------------- | ----- | ----------- | ------------------------------------------------------------------------------------ |
| **target**      | n/a   | n/a         | Strategic priority — declared by user. Outside the tree; linked to work by metadata. |
| **parent task** | 3+    | < 0.5       | Bundle of related work. May parent further tasks. No fixed scope ceiling.            |
| **task**        | 0–3   | < 0.3       | Near-zero entropy — ready to act. May parent further tasks where useful.             |

A large bounded effort with clear sub-structure is a top-level task with child tasks — not a different type. The label is a human-facing shorthand; the properties are authoritative.

**Why not fixed depth?** Forcing work into a rigid hierarchy causes two failure modes:

- Simple work gets **over-decomposed** — phantom layers created just to satisfy the hierarchy
- Complex work gets **under-decomposed** — months of work crammed into one node

Variable-rate decomposition stops when uncertainty is low enough to act — regardless of depth.

---

## Primary Node Types

The actionable types in the PKB:

| Type            | Description                                                                                                                          |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **target**      | A user-declared strategic priority. Stands outside the work tree — linked to work by metadata, never as a parent.                    |
| **parent task** | A bundle of related work. Tree root by default; may have a parent task for nesting. No depth limit.                                  |
| **task**        | A discrete deliverable, completable in a single focused session. May have a task parent.                                             |
| **learn**       | Observational tracking — a spike, discovery, or noted finding. Not directly actionable; resolves by decomposing into follow-up tasks |

The `classification` field carries additional semantic subtypes (bug, feature, spike, chore, etc.) without multiplying top-level types.

### Retired types

| Retired type | Replacement                                                                                                                                                                                                                                                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `goal`       | Use `target`. Goals were aliased to targets historically; the alias is removed. Targets never parent.                                                                                                                                                                                                                          |
| `project`    | The hierarchy level is gone. The word "project" now refers narrowly to a polecat repo — see [Project (operational routing field)](#project-operational-routing-field) below. Existing containers previously typed as project will be reclassified (typically to root-level tasks) per the migration in [[areas-not-projects]]. |

### `target` nodes

Targets represent user-declared strategic priorities — what success looks like. Targets are invisible-weight, non-actionable nodes that are excluded from "tasks to do" surfaces yet always propagate weight. They are reference/planning nodes, not work containers: they do not parent tasks, and they are excluded from the work tree. Tasks own `contributes_to` edges but never set a target's weight / consequence / severity.

**Key fields on target nodes:**

| Field         | Description                                                                                                                                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `consequence` | Prose description of what happens if the target is not achieved. Present on tasks too — used by the daily skill to surface stakes without editorial framing. |
| `severity`    | SEV0–SEV4 ladder for the consequences of missing the target. Drives downstream weighting via the contribution edges (see below).                             |

**How work links to targets:** via `contributes_to` edges in the metadata of a task — not via parent hierarchy. A task can contribute to multiple targets simultaneously. The planner enforces this: targets are never used as direct parents.

The edge is an object, not a bare ID — see [[multi-parent]] §1.6 for the canonical schema:

```yaml
contributes_to:
  - to: <target-id>
    stated_weight: Expected         # Renooij-Witteman verbal term, see below
    justification: "single sentence (ICD 203 style) explaining the belief"
    # Optional, for prototype-backed obligations:
    inherits_from: <prototype-id>
```

**Canonical fields**: `to`, `stated_weight`, `justification`. Aliases `weight` / `why` are accepted on read for backward compatibility but new edges should use canonical names.

**Weight is verbal, not numeric.** Raw decimals are rejected at parse. The Renooij-Witteman scale: `Impossible` (0.00) / `Improbable` (0.15) / `Uncertain` (0.25) / `Fifty-Fifty` (0.50) / `Expected` (0.75) / `Probable` (0.85) / `Certain` (1.00). Semantics are Birnbaum importance — the marginal probability that missing this task guarantees failure of the target. `Certain` = single point of failure; `Fifty-Fifty` = redundancy exists.

(Legacy `goals: []` metadata fields on existing nodes carry the same intent and should be migrated to `contributes_to` edges. The migration assigns a default `stated_weight: Expected` and a placeholder justification pending review.)

## Project (operational routing field)

**"Project" is a repository registered in `polecat.yaml`.** Carried on tasks as the `project: <slug>` metadata field. Polecat dispatch reads this field to choose the worktree for the worker (`polecat/cli.py` resolves `project_slug = task.project` against the registry).

| Property      | Value                                                                                                            |
| ------------- | ---------------------------------------------------------------------------------------------------------------- |
| Where defined | Top-level `projects:` block in `polecat.yaml`                                                                    |
| Carried as    | `project: <slug>` frontmatter field on tasks (and parent tasks that decompose into tasks needing dispatch)       |
| Required      | Yes — tasks without a routable `project` are undispatchable; `pkb_orphans` flags them                            |
| Validation    | Slug must match a `projects:` key, a `project_aliases` entry, or a per-project `aliases:` list in `polecat.yaml` |
| Inheritance   | Children inherit the parent's `project` unless explicitly overridden (most tasks just take the parent's value)   |

**Project is not a hierarchy level** and does not appear in the work-decomposition tree. It is purely operational — "which repo does the worker check out for this task?" Conceptual containers that used to be marked as project type (e.g. `qut`, `osb`, `tja`, `arc-future-fellowship`) are not projects in this sense; they are root-level tasks with no special type.

---

## Default Fallback Parent

Every task in the PKB must have a parent. When creating a task, agents and scripts should resolve the most contextually appropriate parent (such as the active parent task or project root).

However, during emergency session handovers, bails (`/dump`), or when capturing ad-hoc work where no parent is obvious, the `adhoc-sessions` node is the **default catch-all parent for resume/handover tasks**.

Skills like `/dump` or `/end-session` that need to rapidly persist a loose thread must use `parent="adhoc-sessions"` rather than failing or omitting the parent field.

---

## Edge Semantics and Cycle Policy

The graph is **directed but not required to be acyclic**. Cycles are a feature for some edge types and a pathology for others.

| Edge type         | Semantics                                                         | Cycles       | Notes / example                                                                                                                                                 |
| ----------------- | ----------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `parent`          | Containment: B is part of A                                       | Nonsensical  | Self-containment undefined — never valid. Strict tree (one parent).                                                                                             |
| `depends_on`      | Hard blocker: B cannot start until A completes                    | Pathological | A blocks B blocks A — decomposition failure, must fix                                                                                                           |
| `soft_depends_on` | Enabling: A makes B easier or better                              | Healthy      | Writing clarifies methodology, methodology improves writing                                                                                                     |
| `contributes_to`  | Strategic contribution: B advances target A (weighted, justified) | Pathological | A target should not contribute to a node that contributes to it. See [[multi-parent]] §1.6 for full schema. Carries `stated_weight` (verbal) + `justification`. |
| `closes`          | Completion: this node completes the target task / PR              | Pathological | A closes B — terminal; B is done as a result. Mutual closure undefined.                                                                                         |
| `link`            | Reference: A mentions B                                           | Irrelevant   | Cross-references carry no ordering — always fine                                                                                                                |
| `supersedes`      | Replacement: A replaces B                                         | Pathological | Mutual replacement undefined — never valid                                                                                                                      |
| `similar_to`      | Semantic similarity (auto-discovered)                             | Healthy      | Symmetric. Used for clustering and dedup proposals; never load-bearing for execution.                                                                           |

**Provenance fields, not edge types**: `inherits_from` (on `contributes_to` edges only) records which prototype an edge was materialised from. It's a one-time breadcrumb at edge creation, not a live reference — editing the prototype later does not retroactively rewrite existing edges.

### Cycle detection policy

**Hard cycles** (`parent`, `depends_on`, `contributes_to`, `closes`, `supersedes`): Detected via Tarjan's SCC across the union of these edge types. Any strongly connected component with more than one node, or any single-node SCC with a self-edge, is a structural failure requiring human review. Surfaced as errors.

**Soft cycles** (`soft_depends_on`, `similar_to`): Counted and reported but not flagged as errors. Mutual reinforcement is a normal property of academic work — writing clarifies thinking, thinking improves writing. Semantic similarity is symmetric by nature.

**Reference edges** (`link`): Cycles ignored — references carry no execution semantics.

### Dependencies as mutual information

When two tasks have high mutual information — knowing A's state tells you about B's state — they belong in the same container (parent task). When tasks are independent, they can live in different containers.

The tree hierarchy is a **spanning tree** of the underlying dependency graph. It captures containment but drops cross-cutting dependency edges. Tooling must surface full dependency chains ("blocked by X, which is blocked by Y"), not just immediate blockers.

---

## Priority Labels (P0–P4)

The single canonical definition of priority. Other framework documents MUST link here rather than redefine these labels locally.

| Label | Name          | Meaning                                                                                                                   |
| ----- | ------------- | ------------------------------------------------------------------------------------------------------------------------- |
| P0    | Critical      | Blocking work, deadline overdue, or active incident. Drop everything. The default for "urgent" — escalate immediately.    |
| P1    | Active intent | Important to the user right now; should be in-flight this week. Has near-term consequence if it slips.                    |
| P2    | Active work   | Routine in-flight work. Scheduled and in the active working window. Promoted deliberately from P3 by the user or planner. |
| P3    | Planned       | On the roadmap; not yet active. **Default for new tasks** — promoted to P2 when the user schedules them.                  |
| P4    | Backlog       | Logged for the record. May never be done; survives only because deletion is more expensive than retention.                |

**Lower number = higher priority.** When sorting "highest priority first", sort ascending by label number (`P0` before `P1` before `P2`, etc.).

**Priority is not urgency or severity.** Urgency is a time-decay function over `due` and slack (computed by the PKB; consumed as one component of `focus_score`, not used directly for ranking). Severity is a property of incidents (impact when they occur). Priority is the user-facing label that says "where does this slot in my queue right now?" — composed of, but distinct from, both. Skills that infer priority from deadlines (e.g. hydrator email capture) layer their own deadline-mapping rules on top of these definitions; they do not redefine the labels.

---

## Severity Ladder (SEV0–SEV4)

Severity is the SRE-style impact ladder for `type: target` nodes — the terminal obligations the rest of the graph protects. It is **not** a generic importance signal for tasks. The single canonical scale; framework documents MUST link here rather than redefine these levels locally. See the multi-parent spec (brain PKB) §1.2 for the full target-node specification.

| Level | Name       | Example                                                                                          |
| ----- | ---------- | ------------------------------------------------------------------------------------------------ |
| SEV0  | Negligible | Minor annoyance; no consequence beyond self. **Default for tasks.**                              |
| SEV1  | Low        | Small reputational or time cost.                                                                 |
| SEV2  | Moderate   | Meaningful commitment; recoverable if missed.                                                    |
| SEV3  | High       | Serious consequence; hard to recover.                                                            |
| SEV4  | Terminal   | Job loss, bankruptcy, severe health, legal. Lexicographic — any SEV4-committed target dominates. |

**Severity lives on targets, not tasks.** `compute_focus_scores` adds a flat bonus of `+5 000 / +10 000 / +20 000 / +100 000` for SEV1–4 to _any_ node carrying the field. That bonus is calibrated for terminal obligations and will invert the ready queue if applied to ordinary tasks. Tasks inherit urgency from targets via `contributes_to` edges (weighted by Birnbaum importance and discounted by slack), not by carrying severity directly. See [[../../planner/SKILL.md#severity-assignment-rules]] for filing guidance.

`goal_type` (`committed` / `aspirational` / `learning`) modifies how severity propagates: only `committed` targets receive the SEV4 lexicographic override. `aspirational` and `learning` use linear scalar weighting — moonshots cannot hijack the focus queue.

---

## Status Values and Transitions

| Status        | Meaning                                                                          |
| ------------- | -------------------------------------------------------------------------------- |
| `inbox`       | **Default.** Captured but not yet triaged — unknown priority, unknown readiness  |
| `ready`       | Decomposed to leaf tasks with all hard dependencies resolved                     |
| `queued`      | User has manually marked this task available for agent dispatch                  |
| `in_progress` | Claimed by an agent or human — actively being worked                             |
| `merge_ready` | Work complete and committed, waiting for review/merge                            |
| `review`      | Awaiting human review — either mid-flight attention or post-PR changes requested |
| `done`        | Complete — no further action required                                            |
| `blocked`     | Waiting on an external dependency that cannot be resolved internally             |
| `paused`      | Intentionally stopped with intent to resume — work was in-flight but deferred    |
| `someday`     | Parked idea — may never be worked; differs from `inbox` by explicit deferral     |
| `cancelled`   | Will not be done — decision made to drop                                         |

**Default is `inbox`**: Every new node starts as `inbox` regardless of how it was created.

**`ready` means decomposed**: A task graduates to `ready` once it has been decomposed into leaf tasks and all upstream `DependsOn` edges are resolved. Ready signals that the work is well-understood and unblocked — not that an agent should pick it up immediately.

**`queued` is a human gate**: The user manually promotes tasks from `ready` to `queued` to make them available for agent dispatch. This preserves human control over what agents work on next. Agents pull only from `queued`.

**Propagation**: Completion of a node should trigger readiness re-evaluation of all nodes that depend on it. The system surfaces dependency chains so that cascading unblocks are visible.

### Actionable vs. Ready

Framework reporting distinguishes between the **broad view** of all open work and the **narrow view** of what can be started right now:

- **Actionable**: Any task that is not in a terminal state (`done`, `cancelled`, `someday`). This encompasses the entire working set: `inbox`, `ready`, `queued`, `in_progress`, `merge_ready`, `review`, `blocked`, and `paused`. Most high-level dashboards (like the `/daily` note) report actionable counts.
- **Ready**: A subset of actionable work. Strictly limited to leaf tasks that are fully decomposed and have zero unmet dependencies. Tasks in `in_progress` or `review` are actionable but are **not** ready (as they are already claimed or awaiting feedback). Execution-oriented views (like `pkb tasks ready`) focus on this narrow subset.

---

## The Orchestration Layer

Separate from the task hierarchy, the orchestration layer describes how work is executed:

```
WORKFLOW (composable step arrangement for achieving a parent task)
  └─ STEP (one unit of work within a workflow)
      └─ SKILL (fungible instructions for HOW to execute a step)
          └─ PROCEDURE (skill-internal instructions, not fungible)
```

Workflows define WHAT to do and in WHAT order. Skills define HOW to do a single step. Skills are fungible — you can swap one for another that does the same thing. Procedures are skill-internal details that only make sense within that skill.

### Workflow

A **composable arrangement of steps** that describes how to achieve a parent task. Answers "WHAT do we do and in WHAT order?" — not "HOW do we do each step."

Workflows are the Bazaar's quality guarantee. By defining required steps (including verification), workflows ensure that work is good enough regardless of which agent performs it.

**Anti-pattern**: A workflow that contains detailed HOW-TO instructions. That's a skill.

**Anti-pattern**: A workflow embedded inside a skill file. A skill never contains a workflow.

### Step

One unit within a workflow. Has a clear purpose, an expected output, and may specify which skill is needed to execute it.

### Skill

Instructions to an individual agent about **HOW to achieve a workflow step**. Domain expertise packaged as a document: what tools to use, what quality criteria to meet, what patterns to follow.

**Skills are fungible.** A workflow step like "check my email" can be satisfied by any email skill (Outlook, Gmail, etc.). This is what enables the Bazaar model.

### Procedure

A **skill-internal instruction** describing HOW a specific skill accomplishes a task. Tightly coupled to its skill — meaningless outside of it.

**Location**: `skills/{name}/procedures/*.md`

**Test**: Could a different skill achieve the same outcome by following these instructions? If yes → workflow. If no → procedure.

---

## Key Principles

### 1. Labels emerge from properties, not position

A node acts as a parent task because its scope and uncertainty fall in a certain range, not because it lives at depth 3. Labels are navigation aids; properties drive scheduling and tooling.

### 2. Decompose until uncertainty is low enough to act

The stopping condition for decomposition is residual uncertainty, not depth. Stop when a node has clear acceptance criteria, resolved dependencies, and a body specific enough to execute in one session.

### 3. Hard dependency cycles are decomposition failures

If A blocks B and B blocks A, the decomposition is wrong. Restructure — either merge them, or identify a dependency direction. Soft dependency cycles (mutual reinforcement) are healthy and expected.

### 4. Ready means all blockers resolved

A task is only ready when its uncertainty is low AND all DependsOn edges point to completed nodes. "Leaf" is not sufficient.

### 5. The hierarchy provides context

Each level answers "why?" in terms of its parent. A task's purpose is explained by its parent task. The strategic "why" — which target a chain serves — is carried by `contributes_to` metadata at any level, not by a parent edge. If you can't trace a chain back to a containing parent task (and ultimately to one or more targets via metadata), something is misplaced.

### 6. Workflows orchestrate; skills execute; skills are fungible

Workflows define WHAT steps to take and in WHAT order. Skills define HOW to execute a step. A skill NEVER contains a workflow — it may contain procedures (skill-internal HOW-TO), but not orchestration. This separation is what makes the Bazaar model work.

---

## Quick Reference

### Is this a...?

| Question                                                                              | Answer                                              |
| ------------------------------------------------------------------------------------- | --------------------------------------------------- |
| User-declared strategic priority — what success looks like? Not work, doesn't parent. | **Target**                                          |
| A bundle of related work; may have sub-tasks under it; reviewable as one unit?        | **Parent Task**                                     |
| Scope 0–3, uncertainty < 0.3, single-session deliverable?                             | **Task**                                            |
| Discovery or spike — not directly actionable?                                         | **Learn**                                           |
| Sequence of steps describing WHAT to do?                                              | **Workflow**                                        |
| Instructions for HOW to do one step?                                                  | **Skill**                                           |
| A polecat repository slug carried on a task for dispatch routing?                     | **Project** (operational metadata, not a node type) |

### Status lifecycle

```
inbox → ready → queued → in_progress → merge_ready → done
                                     ↘ review
                                     ↘ blocked
                                     ↘ cancelled
```

- `inbox` is the default for all new nodes
- `ready` is set automatically when decomposition is complete and dependencies are resolved
- `queued` is set **manually by the user** — the human gate before agent dispatch
- Agents pull only from `queued`

### Edge type guide

| Relationship                                       | Use               |
| -------------------------------------------------- | ----------------- |
| B is part of A (containment)                       | `parent`          |
| B cannot start until A completes                   | `depends_on`      |
| A makes B easier/better                            | `soft_depends_on` |
| A advances strategic target B (weighted belief)    | `contributes_to`  |
| A completes / closes target B                      | `closes`          |
| A mentions or references B                         | `link`            |
| A replaces B                                       | `supersedes`      |
| A and B are semantically similar (auto-discovered) | `similar_to`      |

---

## Document Authority

This document supersedes any conflicting definitions in other framework files. If another document defines these terms differently, that document should be updated to reference this one.

**Referenced by**: all `SKILL.md` files, `aops-core/skills/planner/WORKFLOWS.md`, brain PKB (project: aops, topic: workflow-system-spec)

**Supersedes**: Fixed-depth waterfall definitions (Goal→Project→Epic→Task as structural types at fixed depths). The hierarchy is now `TASK → TASK → …`, with targets linked by metadata and "project" reserved for the polecat repo routing field. (Decision 2026-05-10.)
