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

| Level       | Uncertainty resolved                   | Remaining uncertainty          |
| ----------- | -------------------------------------- | ------------------------------ |
| Goal        | Who I am / what I commit to (identity) | Which targets to pursue        |
| Target      | What success looks like (milestone)    | Which bodies of work to pursue |
| Parent Task | What to do and in what order           | How to execute each step       |
| Task        | What to execute                        | Nothing — ready to act         |

Goals and targets stand outside the tree — they are strategic nodes linked to work via metadata, not parent edges. Within the tree, decomposition is `TASK → TASK → … → LEAF TASK`, nestable to whatever depth uncertainty demands.

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

> **Note**: For user-facing prioritisation and ranking, use `focus_score` — the canonical composite (additive integer composition) that embeds severity, priority, deadline pressure, age/staleness, `downstream_weight`, stakeholder waiting, an `urgency` term, and a live value-of-information term (`voi_value`, live since 2026-06-01, capped at 5000). See [[multi-parent]] §2.2 for the full, current model. Component fields (`downstream_weight`, `criticality`, `uncertainty`, and the surfaced `voi_value` / `urgency` debug values) remain visible in metadata for filtering, classification, and debugging, but ranking always goes through `focus_score` and should never be driven off a single component. (Cross-repo TAXONOMY SSoT reconciliation is tracked separately under [[mem-3820aa50]].)

### depth and leaf

- **depth**: Distance from root (parent chain walk). Advisory — does not determine label.
- **leaf**: Boolean. True when the node has no children AND uncertainty is low. A structural indicator of decomposition completeness — not sufficient for execution readiness (which also requires resolved DependsOn edges).

---

## Labels as Property Ranges

These ranges map conventional labels to computed property values. They are **guidelines for navigation, not enforcement gates**. Tooling uses these to present a sensible default view; the properties drive actual scheduling.

| Label           | Scope | Uncertainty | Typical behaviour                                                                                         |
| --------------- | ----- | ----------- | --------------------------------------------------------------------------------------------------------- |
| **goal**        | n/a   | n/a         | Identity commitment — declared by user. Outside the tree; never a parent. No severity/consequence/due.    |
| **target**      | n/a   | n/a         | Milestone — declared by user. Outside the tree; linked to work by metadata. Carries severity+consequence. |
| **parent task** | 3+    | < 0.5       | Bundle of related work. May parent further tasks. No fixed scope ceiling.                                 |
| **task**        | 0–3   | < 0.3       | Near-zero entropy — ready to act. May parent further tasks where useful.                                  |

A large bounded effort with clear sub-structure is a top-level task with child tasks — not a different type. The label is a human-facing shorthand; the properties are authoritative.

**Why not fixed depth?** Forcing work into a rigid hierarchy causes two failure modes:

- Simple work gets **over-decomposed** — phantom layers created just to satisfy the hierarchy
- Complex work gets **under-decomposed** — months of work crammed into one node

Variable-rate decomposition stops when uncertainty is low enough to act — regardless of depth.

---

## Goals, Targets, and Work — the three tiers

The PKB separates **why / what / how**. `goal` and `target` are **strategic nodes beside the work tree** (reference tier): never parents, never in "to-do" surfaces, connected to work only by `contributes_to`. `epic`/`task`/`learn` are the **work tree** and the only actionable tier.

- **`goal` — identity (why).** An identity-level commitment: _who I am / how I define myself_. **Unquantifiable** — you cannot count "achievement," and there is no meaningful consequence-of-missing an identity. So a goal has **no `severity`, no `consequence`, no `due`**. Roots of meaning (~10), e.g. _World-Class Academic Profile_. Out of the work tree: never a parent, never parented.
- **`target` — milestone (what).** A tangible, **countable, measurable** output/milestone — _done / not done_. Carries the quantifiable stakes: **`severity` (SEV0–SEV4) + `consequence`** (+ optional `due`). The unit that propagates weight into the work tree, e.g. _Deliver LLB242 marks by deadline_. Out of the work tree: never a parent, never parented. Advances ≥1 goal via `contributes_to`.
- **`epic` / `task` / `learn` — work (how).** Verbs. The only actionable tier (`ACTIONABLE_TYPES`) and the only nodes in the parent-child tree (`EPIC → EPIC|TASK → …`). Advances outcomes via `contributes_to` to **targets** (or directly to **goals**).

Linkage (out-of-tree, via `contributes_to`): `task/epic → target → goal`. The `to:` of a `contributes_to` edge may be a **target or a goal**. Linkage is metadata, not structure — never parent-child, never affects tree traversal; goals & targets are excluded from orphan detection (parentless is correct). **Severity lives only on targets** and propagates down `contributes_to` (Birnbaum); goals carry no severity. `goal` is **not** an alias of `target` — the 2026-05-10 retirement is reversed; distinct coexisting types.

---

## Primary Node Types

The actionable types in the PKB:

| Type            | Description                                                                                                                                                                                                                             |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **goal**        | An identity-level commitment (_who I am / how I define myself_). Outside the work tree — never a parent, never parented. No severity, consequence, or due. Linked TO by targets or work tasks (epics/tasks/learn) via `contributes_to`. |
| **target**      | A user-declared strategic milestone. Stands outside the work tree — linked to work by metadata, never as a parent. Carries `severity` + `consequence`. Advances ≥1 goal via `contributes_to`.                                           |
| **parent task** | A bundle of related work. Tree root by default; may have a parent task for nesting. No depth limit.                                                                                                                                     |
| **task**        | A discrete deliverable, completable in a single focused session. May have a task parent.                                                                                                                                                |
| **learn**       | Observational tracking — a spike, discovery, or noted finding. Not directly actionable; resolves by decomposing into follow-up tasks                                                                                                    |

The `classification` field carries additional semantic subtypes (bug, feature, spike, chore, etc.) without multiplying top-level types. It is **descriptive only — it does not enter `focus_score`**: the live `voi_value` term is computed from graph structure (leaf status, dependency resolution, `contributes_to` target uncertainty × edge weight × downstream weight — see [[multi-parent]] §VoI), not from `classification`. A recorded `spike` / `research` shape is how agents judge whether a node's `voi_value` is trustworthy (genuine probe) versus a deliverable mis-fire ([[mem-830588f3]]). Agents may set it from task shape but **must never override a user-set `classification`**.

### Retired types

| Retired type | Replacement                                                                                                                                                                                                                                                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `project`    | The hierarchy level is gone. The word "project" now refers narrowly to a polecat repo — see [Project (operational routing field)](#project-operational-routing-field) below. Existing containers previously typed as project will be reclassified (typically to root-level tasks) per the migration in [[areas-not-projects]]. |

### `target` nodes

Targets represent user-declared strategic milestones — tangible, measurable outputs (_done / not done_). They sit between `goal` nodes (the identity tier above) and the work tree (epics/tasks/learn). Targets are invisible-weight, non-actionable nodes that are excluded from "tasks to do" surfaces yet always propagate weight. They are reference/planning nodes, not work containers: they do not parent tasks, and they are excluded from the work tree. Tasks own `contributes_to` edges but never set a target's weight / consequence / severity. Targets advance ≥1 goal via their own `contributes_to` edges.

**Key fields on target nodes:**

| Field         | Description                                                                                                                                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `consequence` | Prose description of what happens if the target is not achieved. Present on tasks too — used by the daily skill to surface stakes without editorial framing. |
| `severity`    | SEV0–SEV4 ladder for the consequences of missing the target. Drives downstream weighting via the contribution edges (see below).                             |

**How work links to targets:** via `contributes_to` edges in the metadata of a task — not via parent hierarchy. A task can contribute to multiple targets simultaneously. The planner enforces this: targets are never used as direct parents.

The edge is an object, not a bare ID — see [[multi-parent]] §1.6 for the canonical schema:

```yaml
contributes_to:
  - to: <target-or-goal-id>
    stated_weight: Expected         # Renooij-Witteman verbal term, see below
    justification: "single sentence (ICD 203 style) explaining the belief"
    # Optional, for prototype-backed obligations:
    inherits_from: <prototype-id>
```

**Canonical fields**: `to`, `stated_weight`, `justification`. Aliases `weight` / `why` are accepted on read for backward compatibility but new edges should use canonical names.

**Weight is verbal, not numeric.** Raw decimals are rejected at parse. The Renooij-Witteman scale: `Impossible` (0.00) / `Improbable` (0.15) / `Uncertain` (0.25) / `Fifty-Fifty` (0.50) / `Expected` (0.75) / `Probable` (0.85) / `Certain` (1.00). Semantics are Birnbaum importance — the marginal probability that missing this task guarantees failure of the target. `Certain` = single point of failure; `Fifty-Fifty` = redundancy exists.

(Legacy `goals: []` metadata fields on existing nodes carry the same intent and should be migrated to `contributes_to` edges pointing to the appropriate `target` or `goal` node. The migration assigns a default `stated_weight: Expected` and a placeholder justification pending review.)

### `goal` nodes

Goals represent identity-level commitments — _who I am / how I define myself_. They are the top tier of the strategic reference layer, above targets. Like targets, goals are non-actionable and outside the work tree: never parents, never parented, excluded from "tasks to do" surfaces and orphan detection (parentless is correct for both).

**Goals carry no operational stakes metadata:**

| Field         | Value                                                                                  |
| ------------- | -------------------------------------------------------------------------------------- |
| `severity`    | Not applicable — identity commitments are unquantifiable; there is no cost-of-missing. |
| `consequence` | Not applicable.                                                                        |
| `due`         | Not applicable.                                                                        |

**How targets link to goals:** via `contributes_to` edges on the target node, exactly as work tasks link to targets. The `to:` field of a target's `contributes_to` edge points to a goal ID. Work tasks may also point directly to a goal when no intermediate target applies.

**Orphan detection**: Goals are excluded — a goal with no parent is correct, not an error.

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

| Edge type         | Semantics                                                              | Cycles       | Notes / example                                                                                                                                                      |
| ----------------- | ---------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `parent`          | Containment: B is part of A                                            | Nonsensical  | Self-containment undefined — never valid. Strict tree (one parent).                                                                                                  |
| `depends_on`      | Hard blocker: B cannot start until A completes                         | Pathological | A blocks B blocks A — decomposition failure, must fix                                                                                                                |
| `soft_depends_on` | Enabling: A makes B easier or better                                   | Healthy      | Writing clarifies methodology, methodology improves writing                                                                                                          |
| `contributes_to`  | Strategic contribution: B advances target/goal A (weighted, justified) | Pathological | A target/goal should not contribute to a node that contributes to it. See [[multi-parent]] §1.6 for full schema. Carries `stated_weight` (verbal) + `justification`. |
| `closes`          | Completion: this node completes the target task / PR                   | Pathological | A closes B — terminal; B is done as a result. Mutual closure undefined.                                                                                              |
| `link`            | Reference: A mentions B                                                | Irrelevant   | Cross-references carry no ordering — always fine                                                                                                                     |
| `supersedes`      | Replacement: A replaces B                                              | Pathological | Mutual replacement undefined — never valid                                                                                                                           |
| `similar_to`      | Semantic similarity (auto-discovered)                                  | Healthy      | Symmetric. Used for clustering and dedup proposals; never load-bearing for execution.                                                                                |

**Provenance fields, not edge types**: `inherits_from` (on `contributes_to` edges only) records which prototype an edge was materialised from. It's a one-time breadcrumb at edge creation, not a live reference — editing the prototype later does not retroactively rewrite existing edges.

**On-node inverse of `supersedes`**: the `superseded_by` frontmatter field on the _retired_ task is the inverse of the `supersedes` edge — it both retires the task (out of the dispatchable set) and keeps the redirect readable on the task itself. See [Supersession and retirement](#supersession-and-retirement-superseded_by).

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

> **Who may set these labels — the intent-authority rule.** This section defines what each label _means_. _Who_ may write a non-default band, and when, is governed by the SSoT at [[framework-conventions-summary#intent-authority]]: the band is **Nic's personally curated intent**, never an agent's estimate of importance. Agents leave new tasks at the default (P3) and never originate a non-default band — only Nic does, by express per-request instruction.

| Label | Name          | Meaning                                                                                                                   |
| ----- | ------------- | ------------------------------------------------------------------------------------------------------------------------- |
| P0    | Critical      | Blocking work, deadline overdue, or active incident. Drop everything. The default for "urgent" — escalate immediately.    |
| P1    | Active intent | Important to the user right now; should be in-flight this week. Has near-term consequence if it slips.                    |
| P2    | Active work   | Routine in-flight work. Scheduled and in the active working window. Promoted deliberately from P3 by the user or planner. |
| P3    | Planned       | On the roadmap; not yet active. **Default for new tasks** — promoted to P2 when the user schedules them.                  |
| P4    | Backlog       | Logged for the record. May never be done; survives only because deletion is more expensive than retention.                |

**Lower number = higher priority.** When sorting "highest priority first", sort ascending by label number (`P0` before `P1` before `P2`, etc.).

**Priority is not urgency or severity.** Urgency is a time-decay function over `due` and slack (computed by the PKB; consumed as one component of `focus_score`, not used directly for ranking). Severity is a property of incidents (impact when they occur). Priority is the user-facing label that says "where does this slot in my queue right now?" — composed of, but distinct from, both. Deadline pressure belongs in `due` (it enters ranking via the `urgency` term of `focus_score`), not in the priority band: skills do **not** infer a band from deadlines or apparent importance (see [[framework-conventions-summary#intent-authority]]).

### P0 Calibration Bar

Setting `priority=0` (P0) requires deliberate calibration and is strictly monitored. It is reserved exclusively for active incidents, blocking work that halts the entire pipeline, or immediate deadline breaches. An agent or worker MUST NOT assign or suggest P0 without providing a verified justification in the task metadata/body showing that the entire system/workflow is blocked. Uncalibrated or casual P0 assignments will be rejected by the write-boundary guard.

---

## Severity Ladder (SEV0–SEV4)

Severity is the SRE-style impact ladder for `type: target` nodes — the measurable milestones the rest of the graph protects. **`type: goal` nodes (the identity tier above targets) carry no severity** — identity commitments are unquantifiable, so there is no meaningful cost-of-missing to encode. Severity is **not** a generic importance signal for tasks. The single canonical scale; framework documents MUST link here rather than redefine these levels locally. See the multi-parent spec (brain PKB) §1.2 for the full target-node specification.

| Level | Name       | Example                                                                                          |
| ----- | ---------- | ------------------------------------------------------------------------------------------------ |
| SEV0  | Negligible | Minor annoyance; no consequence beyond self. **Default for tasks.**                              |
| SEV1  | Low        | Small reputational or time cost.                                                                 |
| SEV2  | Moderate   | Meaningful commitment; recoverable if missed.                                                    |
| SEV3  | High       | Serious consequence; hard to recover.                                                            |
| SEV4  | Terminal   | Job loss, bankruptcy, severe health, legal. Lexicographic — any SEV4-committed target dominates. |

**Severity lives on targets, not tasks.** `compute_focus_scores` adds a flat bonus of `+5 000 / +10 000 / +20 000 / +100 000` for SEV1–4 to _any_ node carrying the field. That bonus is calibrated for terminal obligations and will invert the ready queue if applied to ordinary tasks. Tasks inherit urgency from targets via `contributes_to` edges (weighted by Birnbaum importance and discounted by slack), not by carrying severity directly. See [[../../planner/SKILL.md#severity-assignment-rules]] for filing guidance.

`goal_type` (`committed` / `aspirational` / `learning`) modifies how severity propagates: only `committed` targets receive the SEV4 lexicographic override. `aspirational` and `learning` use linear scalar weighting — moonshots cannot hijack the focus queue.

### Severity Target Boundary

Severity belongs only on target nodes (`type: target`). Ordinary tasks, epics, and leaf nodes MUST default to `severity: 0` (or omit the field entirely). Setting a non-zero severity (SEV1–SEV4) on a non-target task/epic is prohibited because it artificially inflates focus scores and inverts the priority queue. Consequence severity must be declared only on the target milestones which protect the work tree. Any write attempting to assign non-zero severity to an ordinary task or non-target leaf will be rejected by the write-boundary guard.

---

## Status Values and Transitions

| Status        | Meaning                                                                         |
| ------------- | ------------------------------------------------------------------------------- |
| `inbox`       | **Default.** Captured but not yet triaged — unknown priority, unknown readiness |
| `ready`       | Decomposed to leaf tasks with all hard dependencies resolved                    |
| `queued`      | User has manually marked this task available for agent dispatch                 |
| `in_progress` | Claimed by an agent or human — actively being worked                            |
| `merge_ready` | Under review — PR open, awaiting CI, review, or iteration. Iterative state.     |
| `review`      | Mid-flight human block — requires judgment/direction before work can proceed    |
| `done`        | Complete — no further action required                                           |
| `blocked`     | Waiting on an external dependency that cannot be resolved internally            |
| `paused`      | Intentionally stopped with intent to resume — work was in-flight but deferred   |
| `someday`     | Parked idea — may never be worked; differs from `inbox` by explicit deferral    |
| `cancelled`   | Will not be done — decision made to drop                                        |

**Default is `inbox`**: Every new node starts as `inbox` regardless of how it was created.

**`ready` means decomposed**: A task graduates to `ready` once it has been decomposed into leaf tasks and all upstream `DependsOn` edges are resolved. Ready signals that the work is well-understood and unblocked — not that an agent should pick it up immediately.

**`queued` is a human gate**: The user manually promotes tasks from `ready` to `queued` to make them available for agent dispatch. This preserves human control over what agents work on next. Agents pull only from `queued`.

**The premise gate fires at `→ queued`** (see [[premise-gate]]). Crossing into the dispatchable set is the universal chokepoint every piece of work passes through before compute is spent on it, so it is where the _premise_ — is this worth doing, is the shape right? — is judged. The promoter records a **one-sentence, principal-voice premise judgment in the task body** (one open prose sentence — **never** a frontmatter field, form, or `- [ ]` checklist; rationale in [[premise-gate]]). `/pull` and the dispatch step of `/supervisor` and `/program` then **hard-refuse to dispatch** a task whose body shows no genuine premise judgment — an agent reads the body and decides, never a string/field presence-check. Absent/vacuous → bounce back to the promoter, do not dispatch.

**Propagation**: Completion of a node should trigger readiness re-evaluation of all nodes that depend on it. The system surfaces dependency chains so that cascading unblocks are visible.

### Supersession and retirement (`superseded_by`)

When a task's work is carved into sibling subtasks, moved under a successor, or otherwise replaced, the original must **leave the dispatchable set** — it must stop being a `queued`/`ready` leaf that `/pull` can select. Recording the replacement only as prose in a parent epic's Log is **not** sufficient: that redirect is invisible on the task itself, so `/pull` selects the original carrying its now-stale (fossil) body. This is the #1584 failure: an original decomposed into siblings (two already done) stayed `queued` and was dispatched against a brief describing work already shipped.

The canonical mechanism is the `superseded_by` task field:

```yaml
superseded_by: [<replacement-id>, …]   # ids of the tasks that now carry this work
```

- **It retires the task.** Stamping `superseded_by` transitions the task out of the dispatchable set (the PKB closes it — verified at runtime: `status` → `done`), so it no longer appears in `queued` or `ready` and `/pull` will not select it. No separate status edit is required; setting `status: cancelled` is the equivalent when the work was dropped rather than re-homed.
- **The redirect lives ON the task.** Because the pointer is frontmatter on the retired task, anyone (or any `/pull` descent) reading that task sees where the work went — unlike a redirect buried in an ancestor's Log.
- **It is the on-node inverse of the `supersedes` edge** (see [Edge Semantics](#edge-semantics-and-cycle-policy)). "A `supersedes` B" (edge on the replacement) ⟺ "B `superseded_by` A" (field on the original). Use `superseded_by` when the requirement is _the original must be non-dispatchable with a readable redirect_ — placing only `supersedes` on the replacements scatters the redirect across siblings and leaves the original dispatchable. (This is distinct from the knowledge-note dedup convention in [[../SKILL.md]] §dedup, where superseded source notes are deleted rather than pointer-stamped.)
- **Do not rewrite the stale body.** Supersession fixes _dispatchability_, not body content. The fossil body is left intact (git preserves it); the field is what makes the task non-dispatchable and the redirect discoverable.

Producers that carve work out of an existing task (planner `decompose`, supervisor, sweep) MUST stamp `superseded_by` on the original in the same operation. `/pull` treats a non-empty `superseded_by` as non-dispatchable and surfaces the redirect (see [[commands/pull]] Step 1).

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

| Question                                                                                                | Answer                                              |
| ------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Identity-level commitment — who I am / how I define myself? No severity/consequence/due, never parents. | **Goal**                                            |
| User-declared measurable milestone — carries severity + consequence? Not work, doesn't parent.          | **Target**                                          |
| A bundle of related work; may have sub-tasks under it; reviewable as one unit?                          | **Parent Task**                                     |
| Scope 0–3, uncertainty < 0.3, single-session deliverable?                                               | **Task**                                            |
| Discovery or spike — not directly actionable?                                                           | **Learn**                                           |
| Sequence of steps describing WHAT to do?                                                                | **Workflow**                                        |
| Instructions for HOW to do one step?                                                                    | **Skill**                                           |
| A polecat repository slug carried on a task for dispatch routing?                                       | **Project** (operational metadata, not a node type) |

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
- Promotion `→ queued` fires the **[[premise-gate]]**: the promoter records a one-sentence premise judgment in the body; dispatch hard-refuses a task that has none

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
