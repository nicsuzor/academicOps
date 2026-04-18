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

Every node in the PKB is the same fundamental data structure. There is no structural difference between a "project" and a "task" at the data level — both are graph nodes with the same fields and computed properties.

**Labels** (`type: project`, `type: epic`, etc.) are **views on computed property ranges**, not structural types assigned to fixed tree depths. A node is called an "epic" because its scope and uncertainty fall in the epic range — not because it happens to live at depth 3.

This matters because work decomposition is self-similar: decomposing a project looks exactly like decomposing a task. The stopping condition is residual uncertainty, which is a property of the node, not a function of its depth.

---

## The Compression Model

The task graph has intrinsic complexity — the full specification of all work, dependencies, and context. The hierarchy's job is to **compress** this into something that fits through the bottleneck of human working memory.

A flat todo list is a fixed-rate code: it treats every item as having the same complexity. The hierarchy is a **variable-rate code** that allocates more structure to high-complexity work and less to simple work.

Each level resolves a different kind of uncertainty:

| Level   | Uncertainty resolved         | Remaining uncertainty          |
| ------- | ---------------------------- | ------------------------------ |
| Goal    | What success looks like      | Which bodies of work to pursue |
| Project | Which coherent body of work  | How to decompose the work      |
| Epic    | What to do and in what order | How to execute each step       |
| Task    | What to execute              | Nothing — ready to act         |

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

- `downstream_weight`: count of nodes that depend (transitively) on this one completing
- `pagerank`: structural influence in the dependency graph
- `stakeholder_exposure`: explicit priority/stakeholder signals

**What it tells you**: Which nodes to work on first when time is scarce. High criticality = unblocks many downstream nodes. Low criticality = isolated or terminal work.

### depth and leaf

- **depth**: Distance from root (parent chain walk). Advisory — does not determine label.
- **leaf**: Boolean. True when the node has no children AND uncertainty is low. A structural indicator of decomposition completeness — not sufficient for execution readiness (which also requires resolved DependsOn edges).

---

## Labels as Property Ranges

These ranges map conventional labels to computed property values. They are **guidelines for navigation, not enforcement gates**. Tooling uses these to present a sensible default view; the properties drive actual scheduling.

| Label       | Scope | Uncertainty | Typical behaviour                                     |
| ----------- | ----- | ----------- | ----------------------------------------------------- |
| **goal**    | > 50  | > 0.7       | Target distribution — defines what success looks like |
| **project** | > 15  | varies      | Partition of goal space — a coherent body of work     |
| **epic**    | 3–20  | < 0.5       | Sufficient statistic for execution — what to do       |
| **task**    | 0–3   | < 0.3       | Near-zero entropy — ready to act                      |

A node with scope 25 but clear acceptance criteria and resolved dependencies might be a well-decomposed epic, not a project. The label is a human-facing shorthand; the properties are authoritative.

**Why not fixed depth?** Forcing work into exactly 4 levels causes two failure modes:

- Simple work gets **over-decomposed** — phantom epics created just to satisfy the hierarchy
- Complex work gets **under-decomposed** — months of work crammed into one "epic"

Variable-rate decomposition stops when uncertainty is low enough to act — regardless of depth.

---

## Primary Node Types

The five primary node types in the PKB:

| Type        | Description                                                                                                                          |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **goal**    | A multi-month/year desired outcome — the root of the hierarchy                                                                       |
| **project** | A discrete thing we work on — a noun with defined scope and boundaries                                                               |
| **epic**    | A bundle of related work that together achieves an aim — a verb                                                                      |
| **task**    | A discrete deliverable, completable in a single focused session                                                                      |
| **learn**   | Observational tracking — a spike, discovery, or noted finding. Not directly actionable; resolves by decomposing into follow-up tasks |

The `classification` field carries additional semantic subtypes (bug, feature, spike, chore, etc.) without multiplying top-level types.

---

## Edge Semantics and Cycle Policy

The graph is **directed but not required to be acyclic**. Cycles are a feature for some edge types and a pathology for others.

| Edge type       | Semantics                                      | Cycles       | Example                                                     |
| --------------- | ---------------------------------------------- | ------------ | ----------------------------------------------------------- |
| `Parent`        | Containment: B is part of A                    | Nonsensical  | Self-containment is undefined — never valid                 |
| `DependsOn`     | Hard blocker: B cannot start until A completes | Pathological | A blocks B blocks A — decomposition failure, must fix       |
| `SoftDependsOn` | Enabling: A makes B easier or better           | Healthy      | Writing clarifies methodology, methodology improves writing |
| `Link`          | Reference: A mentions B                        | Irrelevant   | Cross-references carry no ordering — always fine            |
| `Supersedes`    | Replacement: A replaces B                      | Pathological | Mutual replacement is undefined — never valid               |

### Cycle detection policy

**Hard cycles** (DependsOn + Parent edges): Detected via Tarjan's SCC. Any strongly connected component with more than one node, or any single-node SCC that has a self-edge, is a decomposition failure requiring human review. These are surfaced as errors.

**Soft cycles** (SoftDependsOn edges): Counted and reported but not flagged as errors. Mutual reinforcement is a normal property of academic work — writing clarifies thinking, thinking improves writing.

### Dependencies as mutual information

When two tasks have high mutual information — knowing A's state tells you about B's state — they belong in the same container (epic). When tasks are independent, they can live in different containers.

The tree hierarchy is a **spanning tree** of the underlying dependency graph. It captures containment but drops cross-cutting dependency edges. Tooling must surface full dependency chains ("blocked by X, which is blocked by Y"), not just immediate blockers.

---

## Status Values and Transitions

| Status        | Meaning                                                                         |
| ------------- | ------------------------------------------------------------------------------- |
| `inbox`       | **Default.** Captured but not yet triaged — unknown priority, unknown readiness |
| `ready`       | Decomposed to leaf tasks with all hard dependencies resolved                    |
| `queued`      | User has manually marked this task available for agent dispatch                 |
| `in_progress` | Claimed by an agent or human — actively being worked                            |
| `merge_ready` | Work complete and committed, waiting for review/merge                           |
| `done`        | Complete — no further action required                                           |
| `blocked`     | Waiting on an external dependency that cannot be resolved internally            |
| `cancelled`   | Will not be done — decision made to drop                                        |

**Default is `inbox`**: Every new node starts as `inbox` regardless of how it was created.

**`ready` means decomposed**: A task graduates to `ready` once it has been decomposed into leaf tasks and all upstream `DependsOn` edges are resolved. Ready signals that the work is well-understood and unblocked — not that an agent should pick it up immediately.

**`queued` is a human gate**: The user manually promotes tasks from `ready` to `queued` to make them available for agent dispatch. This preserves human control over what agents work on next. Agents pull only from `queued`.

**Propagation**: Completion of a node should trigger readiness re-evaluation of all nodes that depend on it. The system surfaces dependency chains so that cascading unblocks are visible.

**Canonical authority**: This is the canonical status set. Discrepancies in other framework documents (e.g. implementation specs using additional statuses like `active`, `waiting`, or `review`) should be resolved by updating those documents to align with this list or explicitly scoping their additional statuses to their subsystem.

---

## The Orchestration Layer

Separate from the task hierarchy, the orchestration layer describes how work is executed:

```
WORKFLOW (composable step arrangement for achieving an epic)
  └─ STEP (one unit of work within a workflow)
      └─ SKILL (fungible instructions for HOW to execute a step)
          └─ PROCEDURE (skill-internal instructions, not fungible)
```

Workflows define WHAT to do and in WHAT order. Skills define HOW to do a single step. Skills are fungible — you can swap one for another that does the same thing. Procedures are skill-internal details that only make sense within that skill.

### Workflow

A **composable arrangement of steps** that describes how to achieve an epic. Answers "WHAT do we do and in WHAT order?" — not "HOW do we do each step."

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

A node is an "epic" because its scope and uncertainty fall in the epic range, not because it lives at depth 3. Labels are navigation aids; properties drive scheduling and tooling.

### 2. Decompose until uncertainty is low enough to act

The stopping condition for decomposition is residual uncertainty, not depth. Stop when a node has clear acceptance criteria, resolved dependencies, and a body specific enough to execute in one session.

### 3. Hard dependency cycles are decomposition failures

If A blocks B and B blocks A, the decomposition is wrong. Restructure — either merge them, or identify a dependency direction. Soft dependency cycles (mutual reinforcement) are healthy and expected.

### 4. Ready means all blockers resolved

A task is only ready when its uncertainty is low AND all DependsOn edges point to completed nodes. "Leaf" is not sufficient.

### 5. The hierarchy provides context

Each level answers "why?" in terms of its parent. A task's purpose is explained by its epic. An epic's purpose is explained by its project. A project's purpose is explained by its goal. If you can't trace this chain, something is misplaced.

### 6. Workflows orchestrate; skills execute; skills are fungible

Workflows define WHAT steps to take and in WHAT order. Skills define HOW to execute a step. A skill NEVER contains a workflow — it may contain procedures (skill-internal HOW-TO), but not orchestration. This separation is what makes the Bazaar model work.

---

## Quick Reference

### Is this a...?

| Question                                                    | Answer       |
| ----------------------------------------------------------- | ------------ |
| Scope > 50, uncertainty > 0.7?                              | **Goal**     |
| Scope > 15, coherent body of work toward a goal?            | **Project**  |
| Scope 3–20, uncertainty < 0.5, can be reviewed as one unit? | **Epic**     |
| Scope 0–3, uncertainty < 0.3, single-session deliverable?   | **Task**     |
| Discovery or spike — not directly actionable?               | **Learn**    |
| Sequence of steps describing WHAT to do?                    | **Workflow** |
| Instructions for HOW to do one step?                        | **Skill**    |

### Status lifecycle

```
inbox → ready → queued → in_progress → merge_ready → done
                                     ↘ blocked
```

- `inbox` is the default for all new nodes
- `ready` is set automatically when decomposition is complete and dependencies are resolved
- `queued` is set **manually by the user** — the human gate before agent dispatch
- Agents pull only from `queued`

### Edge type guide

| Relationship                     | Use             |
| -------------------------------- | --------------- |
| B is part of A (containment)     | `Parent`        |
| B cannot start until A completes | `DependsOn`     |
| A makes B easier/better          | `SoftDependsOn` |
| A mentions or references B       | `Link`          |
| A replaces B                     | `Supersedes`    |

---

## Document Authority

This document supersedes any conflicting definitions in other framework files. If another document defines these terms differently, that document should be updated to reference this one.

**Referenced by**: `aops-core/SKILLS.md`, all `SKILL.md` files, `specs/workflow-system-spec.md`, `aops-core/skills/planner/WORKFLOWS.md`

**Supersedes**: Fixed-depth waterfall definitions (Goal→Project→Epic→Task as structural types at fixed depths).
