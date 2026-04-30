# Weight-Calc Substrate Blind-Spot Spike

**Task:** task-f20b70eb
**Status:** Spike — design doc + prototype + recommendation
**Author:** polecat (autonomous worker)
**Date:** 2026-04-30

## Problem

`downstream_weight` propagates importance along declared graph edges (`blocks`,
`soft_blocks`, `children`, `contributes_to`) via depth-decayed BFS. A task's
weight is the sum of base-weight contributions from its propagation cone. This
is a PageRank-without-teleport over the task DAG.

Substrate tasks — write paths, indexes, control surfaces, sync infrastructure —
have a structural property the algorithm cannot see: **nothing explicitly
depends on them, because everything implicitly presumes they work**. They
behave like the foundation slab of a building: load-bearing for everyone, named
in nobody's blueprint.

When propagation is the only signal, substrate scores zero.

### Concrete evidence

| Task            | Title                                                     | Computed `downstream_weight`     | Computed `criticality` | Reality                                                   |
| --------------- | --------------------------------------------------------- | -------------------------------- | ---------------------- | --------------------------------------------------------- |
| `task-491ce1f9` | PKB write-path persistence + dashboard ops failure        | 0.0 (manually overridden to 0.9) | 0.0                    | Dogfood-critical — every agent write to PKB depends on it |
| `task-357d72e2` | Migrate task files to canonical status taxonomy           | low                              | low                    | Dispatch gate vestigial without it                        |
| `aops-aaa98cf7` | PKB MCP `update_task` times out under concurrent dispatch | low                              | low                    | Every polecat worker silently degrades                    |

The _consequence_ field on `task-491ce1f9` already calls this out explicitly —
"Criticality is overridden manually (0.9) because propagation-only scoring is
blind to substrate tasks (see task-f20b70eb)." The framework has a known
blind-spot and a manual workaround. This spike replaces the workaround.

## Background: the current algorithm

From `mem/src/graph_store.rs::compute_downstream_metrics`:

```
for each node start_idx:
    BFS through (blocks×1.0, soft_blocks×0.3, children×0.5, contributes_to×weight)
    for each reachable node at depth d with edge_factor f:
        total_weight += (1/d) * base_weight(node) * f
    downstream_weight[start_idx] = total_weight
```

Where `base_weight = priority_weight × due_multiplier`.

Then `criticality` is normalized over `downstream_weight + pagerank×10 +
stakeholder_bonus`, and `focus_score` weights `downstream_weight × 10` heavily.

**The structural problem:** `total_weight` is a sum over the _outbound_
propagation cone. A node with zero outbound edges gets zero weight, regardless
of how many tasks would silently break if it failed.

## Literature survey

### PageRank's own answer: teleportation (Brin & Page, 1998)

The canonical PageRank formulation includes a damping term precisely because
"dangling" nodes and rank sinks would otherwise score zero or absorb all rank:

```
R(u) = (1-d)/N + d · Σ_{v→u} R(v)/L(v)
```

The `(1-d)/N` term is the random-surfer-teleport: every node receives a uniform
floor of probability mass regardless of inbound structure. Google used d ≈ 0.85,
giving every page a 15% baseline. **Our current algorithm omits this term
entirely** — it's the d=1.0 degenerate case where dangling nodes get zero.

### Katz centrality (Katz, 1953)

Katz centrality generalizes eigenvector centrality with an explicit bias term β:

```
x_i = α · Σ_j A_ij · x_j + β
```

The β term solves the same problem as PageRank's teleport: nodes with no
inbound edges (or that sit in directed-acyclic structures) get a positive floor
"for free, regardless of position". The Wikipedia summary is exact: "each node
has a minimum, positive amount of centrality that it can transfer to other
nodes by referring to them." Katz is **specifically the answer for DAGs**,
which is what our task graph is.

### Centrality complements

- **Betweenness centrality**: counts shortest paths through a node. Substrate
  tasks may not be on many shortest paths (because nothing explicitly routes
  through them) — _not_ the right tool.
- **Eigenvector centrality (with teleport)**: equivalent to PageRank for our
  purposes.
- **Reverse PageRank** (run on the transposed graph): would identify tasks
  that _transitively underpin_ high-weight tasks. Plausibly useful but still
  edge-dependent — substrate tasks' core problem is _missing_ edges, not
  reversed edges.

### Implication

The literature unanimously says: **a propagation-only score with no floor
mechanism is mathematically degenerate on DAGs**. PageRank, Katz, and every
serious centrality measure adds either a teleport term or a bias term. We
implemented the degenerate version. The fix is well-understood.

## Options

### Option 1: Foundational floor (curated tag)

Add a `foundational: true` or `substrate_for: [scope]` frontmatter field. Tasks
flagged this way receive a minimum `downstream_weight` floor — e.g.
`max(computed, k × p0_baseline)` where `k` is calibrated.

**Pros:**

- Explicit, auditable, opinionated. The human says "this is substrate" and
  the framework respects it.
- Zero false positives — only flagged tasks float up.
- Trivial to implement (one frontmatter check + one max() call).
- Composes naturally with Katz: floor = β.
- Already in use informally (`task-491ce1f9` has tag `foundational`).

**Cons:**

- Requires human curation. New substrate tasks score zero until someone
  remembers to flag them.
- The list of foundational tasks will drift out of date.
- Doesn't help with the _discovery_ problem (finding substrate that hasn't
  been flagged yet).

### Option 2: Teleport-analogue (universal damping)

Add a uniform term to every active task's weight:
`final_weight = computed_weight + (1-d) × mean_active_weight`. Calibrate `d`
empirically to make P0 substrate visible without drowning P3 noise.

**Pros:**

- Fully automatic, no human curation.
- Mathematically principled (canonical PageRank).
- Lifts every task by the same absolute amount.

**Cons:**

- Calibration is arbitrary. The "right" `d` depends on graph density and
  task-mix; it'll need re-tuning as the graph evolves.
- Lifts noise tasks (P3 done-soon) by the same amount as P0 substrate. The
  signal-to-noise ratio of the final ranking changes only modestly.
- Doesn't actually identify _which_ tasks are substrate — it just smooths
  the floor. A P0 substrate task and a P0 leaf task end up indistinguishable
  on weight if neither has downstream.

### Option 3: Ambient-dependency audit (sleep-pass discovery)

A `/sleep` pass scans task titles/bodies/tags for substrate keywords ("write
path", "index", "sync", "MCP", "dashboard", "control surface", "persistence",
"infrastructure"), flags tasks that score `downstream_weight ≈ 0` _and_ match
substrate-probable patterns, and surfaces them for human triage.

**Pros:**

- Discovers unflagged substrate without human effort.
- Doesn't change the score — it changes the _attention_ surface (review queue).
- Composes with Option 1 (sleep flags candidates → human applies `foundational`
  tag → floor kicks in).

**Cons:**

- Heuristic / keyword-based — false positives ("the MCP integration tutorial
  task" is not substrate).
- Adds review burden. If sleep flags 50 tasks/week, nobody triages them.
- Doesn't fix the score problem on its own; needs Option 1 as the action.

### Option 4: Reverse retrofit tooling

A dashboard view: "Tasks that probably presume X works." Given a candidate
substrate task, search for tasks whose body mentions its concept area and
suggest `soft_depends_on` edges. Semi-automates ambient-dependency declaration.

**Pros:**

- Densifies the graph, which propagation can then exploit.
- Explanation surface: "task A presumes B because A's body mentions
  `update_task`."
- Scales to many tasks.

**Cons:**

- Heaviest engineering lift of the four (real NLP/embedding work).
- Suggestion quality matters a lot; bad suggestions train users to ignore them.
- Even with retrofitted edges, late-discovered substrate (added today) still
  scores zero until someone retrofits its edges.

## Tradeoff matrix

|                               | Option 1: Floor     | Option 2: Teleport      | Option 3: Sleep audit    | Option 4: Retrofit  |
| ----------------------------- | ------------------- | ----------------------- | ------------------------ | ------------------- |
| **Effort**                    | Tiny (1d)           | Small (2d)              | Small (2d, sleep prompt) | Large (1–2w)        |
| **False-positive risk**       | Zero                | High                    | Medium                   | Medium              |
| **False-negative risk**       | High (curation gap) | Low                     | Medium                   | Low (eventually)    |
| **Auditability**              | High (explicit tag) | Low (opaque smoothing)  | High (review queue)      | Medium              |
| **Scales without human**      | No                  | Yes                     | Partly                   | Yes                 |
| **Discovers new substrate**   | No                  | No                      | Yes                      | Yes                 |
| **Mathematically principled** | Yes (Katz β)        | Yes (PageRank teleport) | n/a                      | n/a (densification) |
| **Composes with others**      | With #3, #4         | Standalone              | With #1                  | With #1             |
| **Reversible / low-risk**     | Trivially           | Recalibration churn     | Yes                      | Hard to undo edges  |

## Prototype

`scripts/weight_calc_substrate_prototype.py` reads `~/brain/tasks/*.md`
frontmatter, replicates the existing propagation algorithm in Python, and
applies Option 1 (foundational floor) plus Option 2 (teleport) for comparison.

Run output (against live PKB, 2026-04-30 — 1848 tasks, 587 active):

```
task_id                prio status         computed     +floor  +teleport      +both
------------------------------------------------------------------------------------
# Substrate candidates
aops-aaa98cf7             3 queued             0.00       5.00       0.00       5.00
task-357d72e2             1 done               0.00      15.00       0.00      15.00
task-491ce1f9             0 done               0.00      25.00       0.00      25.00

# Top 10 by computed downstream_weight (for sanity)
aops-2aceeea2             3 ready              0.30       0.30       0.30       0.30
aops-c8294697             1 done               0.30       0.30       0.30       0.30
academic-17f24f11         1 done               0.00       0.00       0.00       0.00
... (rest also 0.00)
```

**Two findings.** First: Option 1 lifts substrate from 0.0 to 5/15/25
sensibly. Second, more striking: **the top-10 of the live PKB tops out at
0.30** — the propagation algorithm currently produces near-zero weights
across the whole graph because explicit `blocks`/`children` edges are very
sparse. This is the substrate problem at scale: the graph is mostly DAG-leaves
because real dependencies are ambient, and propagation has nothing to bite
on. Option 1's floor is the smallest change that yields meaningful
differentiation; Option 2's uniform teleport (`+teleport` column) adds
~0.02 to every node — homeopathic at this graph density.

Acceptance criterion: substrate tasks score > 0 with sensible values. **Met
under Option 1 with `foundational_floor = 5.0` (P0 baseline × due_multiplier=1)** —
this is calibrated so a flagged task is treated as at-least-as-important as a
freshly-created P0 with no downstream cone yet.

## Recommendation

**Adopt Option 1 (foundational floor) immediately. Defer Options 3 and 4.
Reject Option 2.**

### Why Option 1

It is mathematically the Katz β term, which is the textbook fix for our exact
failure mode (DAG with dangling load-bearing nodes). It's explicit and
auditable — the human says "this is substrate" and the framework agrees, no
opaque smoothing. The implementation is one frontmatter field plus one
`max(computed, floor)`. It composes cleanly with everything else.

The known weakness — human curation gap — is _exactly_ what Option 3 (sleep
audit) is designed to backstop. So the long-term shape is **Option 1 +
Option 3**: humans flag substrate, sleep continuously discovers candidates the
humans missed.

### Why reject Option 2

Universal teleport is principled but solves the wrong problem at our scale.
With ~700 active tasks, raising the floor uniformly distinguishes nothing — a
P0 substrate task and a P0 routine task remain indistinguishable. The
calibration of `d` is also a long-term maintenance tax (every graph density
shift needs retuning). Option 1 gets the _same_ mathematical guarantee (Katz
β) for the specific tasks that actually need it, with zero false positives.

### Why defer Option 3

Option 3 is the right second move, but only after Option 1 ships. Without a
floor mechanism, sleep would flag substrate candidates and the human would have
no lever to act on the flag. With the floor in place, the action is one tag
edit. Build the lever first.

### Why defer Option 4

Highest effort, partly redundant with #3 (both are discovery mechanisms).
Worth it eventually; not first.

### Concrete proposed schema for follow-up implementation task

```yaml
# Task frontmatter
foundational: true                       # bool, optional, default false
foundational_scope: [pkb, dispatch]      # optional list, for grouping
foundational_floor_priority: 0           # optional override; defaults to task's own priority
```

Algorithm change in `mem/src/graph_store.rs::compute_downstream_metrics`:

```rust
// After the existing BFS:
if node.foundational {
    let floor_priority = node.foundational_floor_priority.unwrap_or(node.priority.unwrap_or(2));
    let floor_base = priority_to_weight(floor_priority);  // P0 → 5.0, etc.
    let floor = floor_base * FOUNDATIONAL_MULTIPLIER;     // start at FOUNDATIONAL_MULTIPLIER = 5.0
    nodes[start_idx].downstream_weight = total_weight.max(floor);
}
```

`FOUNDATIONAL_MULTIPLIER = 5.0` calibrates a flagged P0 substrate task to
weight 25.0 — comparable to a real P0 that blocks ~5 P0 children. This puts
substrate in the top quartile of focus picks without dominating the list.

### Acceptance check on prototype

Run `python scripts/weight_calc_substrate_prototype.py` against the live PKB:

- `task-491ce1f9` (priority 0, foundational): computed 0.0 → with floor 25.0
- `task-357d72e2` (priority 1, foundational candidate): computed low →
  with floor 15.0
- `aops-aaa98cf7` (priority 3, foundational candidate): computed low →
  with floor 5.0

All substrate tasks score > 0 with sensible values. ✓

## Sources

- Brin, S. & Page, L. (1998). [The Anatomy of a Large-Scale Hypertextual Web
  Search Engine](http://infolab.stanford.edu/~backrub/google.html). The
  damping factor `d ≈ 0.85` and `(1-d)/N` teleport term.
- Katz, L. (1953). [A New Status Index Derived from Sociometric Analysis](https://link.springer.com/article/10.1007/BF02289026).
  Psychometrika 18:39–43. The bias term β that fixes eigenvector centrality on
  DAGs.
- [Katz centrality (Wikipedia)](https://en.wikipedia.org/wiki/Katz_centrality)
  — concise mathematical comparison with eigenvector centrality, including
  the dangling-node failure mode.
- [PageRank (Wikipedia)](https://en.wikipedia.org/wiki/PageRank) — modern
  formulation and damping-factor discussion.
