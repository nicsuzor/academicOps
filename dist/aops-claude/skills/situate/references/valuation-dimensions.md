# Valuation Dimensions — recording the initial estimate

Detail for [SKILL.md](../SKILL.md) step 4. This does **not** re-derive the scoring math — the
canonical model lives in `mem`'s `multi-parent` spec (`focus_score`, `compute_downstream_metrics`
in `graph_store.rs`). Situate records an estimate on each standing dimension; it doesn't own or
reimplement the formula.

## The six standing dimensions

From [[00-pipeline]] Principle 3, estimated at situate-time and revisable:

| Dimension               | What it is                                                  | Where it lives                                                                                                                                  |
| ----------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Value of information    | How much uncertainty this resolves                          | `classification: spike`/`research` signals a genuine probe; `voi_value` is graph-computed (see caveat below)                                    |
| Consequences of failure | What breaks if this is wrong or skipped                     | `consequence` prose — **on the target it contributes to**, not the task itself                                                                  |
| Downstream unblocking   | What this frees up                                          | `mcp__pkb__get_dependency_tree(id, direction='downstream')` to check, `depends_on` edges from other nodes to record it                          |
| Contribution to targets | How much this moves a real target                           | the `contributes_to` edge weight + justification (see graph-placement.md)                                                                       |
| Uncertainty discount    | How much to discount the estimate given how little is known | `uncertainty` field — a classifier on the node, scoring input only via downstream propagation, not a direct multiplier on this node's own score |
| Estimated effort        | Rough sizing                                                | `effort` field                                                                                                                                  |

Populate what the bundle's `Intent`/`Context` make clear; don't fabricate precision the ask doesn't
support. `classification` (`spike`/`research`/omit for execution) may be set from the task's shape
but never overrides a user-set value.

## `voi_value` — known distortion, discount accordingly

`voi_value` (live component of `focus_score`, capped at 5000) currently over-rewards deliverables
wired to busy targets rather than genuine uncertainty-resolving work. Trust it for spike/probe
leaves; discount it for deliverables until recalibrated. Don't let a high computed `voi_value`
substitute for your own judgment on whether this task actually resolves uncertainty — record your
estimate honestly even where it disagrees with the computed number.

## Priority — Nic's intent only, never estimated

`priority` is not one of the six dimensions and situate never sets it beyond the uncurated default
(P3), regardless of how the other five dimensions come out. Only an express directive from Nic this
turn justifies a non-default band. Same-day/near-term intent language ("today", "this week") is
such a directive and gets written as `priority: 1` — never fabricated into a `due` date; `due` is
exclusively for real external deadlines, and manufacturing one to carry urgency signal poisons
deadline trust for every genuine deadline on the graph. `priority: 0` requires deliberate
calibration (active incidents, pipeline-blocking work, documented overdue-critical) — not a default
for "this seems important."

## Severity — target-only, never on the task

Tasks and epics default to `severity: 0` or omit it entirely; agent-assigned non-zero `severity` on
a task is prohibited (write-boundary guard blocks it). `severity` 1–4 lives on `type: target` nodes
only, paired with `consequence` prose. If a new task should inherit stakes, that's a reason to check
the target's `severity` and `contributes_to` weight — not to put `severity` on the task.

Canonical SSoT for both: `[[framework-conventions-summary#intent-authority]]`.
