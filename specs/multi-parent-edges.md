---
title: Multi-parent edges and target-node severity propagation
type: spec
status: draft
owner: aops
parent_epic: task-18da4781
feeds_pilot: task-0779b81b
last_updated: 2026-04-20
---

# Multi-parent edges and target-node severity propagation

Existing `downstream_weight` BFS (`mem/src/graph_store.rs:1347-1470`) propagates criticality through `blocks` / `soft_blocks` with depth decay. This spec adds two new graph elements so that **catastrophic, deadline-bound obligations** raise the priority of their contributing tasks _without_ introducing a parallel ranking axis.

Research briefs this distils from:
[[pkb-weight-744da956-target-severity]] (target nodes),
[[pkb-weight-454ec614-edge-elicitation]] (weight elicitation),
[[pkb-weight-d1a916cf-calibration-drift]] (calibration & gaming resistance).

## Design philosophy

- **One signal**: urgency integrates into the existing `downstream_weight` / `focus_score` computation. No parallel dashboards.
- **Dumb server, smart agent**: `mem` computes Brier scores, decay, LST slack, transitivity diffs. An agent decides _whether a task was necessary_, _whether consequence prose is sufficient_, and re-ranks on anomaly prompts.
- **Enforcement as surface, not gate**: anomalies, SEV4-cap breaches, and missing justifications are _surfaced_ in `/daily`, `/maintain`, `/sleep` review skills. They do not block tool use. (See VISION "What We've Learned".)
- **MVP first**: only spec the fields and behaviours the [[task-0779b81b]] pilot will actually exercise. Mark the rest as **deferred**.

## 1. Target-node semantics

A **target node** is a graph node representing a non-negotiable obligation or terminal consequence. It is not a task to be executed; it is the thing whose failure other tasks must prevent.

### 1.1 MVP frontmatter fields

```yaml
type: target
severity: 0-4            # SRE-style ladder, NOT 1-10 RPN (brief 3 §1.1)
due: <ISO-8601>          # absolute deadline; triggers LST slack calc
consequence: <prose>     # mandatory; forces deliberative articulation
goal_type: committed | aspirational | learning   # OKR frame (brief 3 §5.1)
```

### 1.2 Severity ladder (0–4)

| Level | Label        | Example                                        |
| ----- | ------------ | ---------------------------------------------- |
| 0     | Negligible   | Minor annoyance; no consequence beyond self    |
| 1     | Low          | Small reputational or time cost                |
| 2     | Moderate     | Meaningful commitment; recoverable if missed   |
| 3     | High         | Serious consequence; hard to recover           |
| **4** | **Terminal** | **Job loss, bankruptcy, severe health, legal** |

Severities 0–3 are compensatory — standard scalar math applies. **Severity 4 is lexicographic**: it gets an override multiplier (`S_lex = 10_000`) that dwarfs all standard priority weights so any SEV4-adjacent task outranks any SEV0–3 task regardless of other factors. This encodes the incommensurability of catastrophic loss (brief 3 §2.3).

### 1.3 goal_type

Only `committed` target nodes receive the lexicographic override. `aspirational` and `learning` targets use linear propagation. This prevents moonshots from hijacking the focus queue (brief 3 §5.1).

### 1.4 Consequence prose

Mandatory free-text field. Serves two functions:

1. **Cognitive speedbump**: forces the user to articulate _what failure means_ — suppresses reflexive severity inflation.
2. **Post-mortem evidence**: during calibration review, the recorded prose is compared against what actually happened.

No character cap in MVP; `/maintain` reviews it.

### 1.5 Deferred (earn-their-keep)

- Hard concurrency cap on active SEV4 nodes → surfaced by `/daily`, not enforced by hook.
- Severe-keyword gatekeeping on consequence prose → agent-side check during `/maintain`.
- Post-mortem integrity audit → manual cadence in `/maintain` until dogfooding proves we need automation.

## 2. `contributes_to` edge schema

Tasks declare contribution to one or more targets via a multi-parent-capable edge (distinct from the single `parent` / `blocks` relationships).

### 2.1 MVP frontmatter

```yaml
contributes_to:
  - to: <target-id>
    weight: Expected             # Renooij-Witteman verbal term (brief 2 §4)
    why: "contractual obligation to mark by 28 Apr"
```

### 2.2 Weight scale — Renooij-Witteman

Raw decimals are rejected at parse time. Accepted verbal terms map to fixed non-linear anchors (brief 2 §Architecture):

| Term        | Anchor |
| ----------- | ------ |
| Impossible  | 0.00   |
| Improbable  | 0.15   |
| Uncertain   | 0.25   |
| Fifty-Fifty | 0.50   |
| Expected    | 0.75   |
| Probable    | 0.85   |
| Certain     | 1.00   |

Non-linearity defeats the spacing and centring biases that corrupt linear scales.

### 2.3 Weight semantics — Birnbaum importance

`weight` is **not** "percent contribution". It is the marginal probability that **missing this task guarantees failure of the target** — the Birnbaum importance from fault-tree analysis (brief 3 §3.2). A weight of `Certain` (1.00) means the task is a single point of failure: miss it and the target fails. `Fifty-Fifty` (0.50) means redundancy exists.

The edge schema includes a `why` field (justification) following intelligence tradecraft ICD 203 (brief 2 §5). A single sentence is sufficient. Missing justifications are surfaced by `/maintain`, not blocked at write time.

### 2.4 Deferred

- `base_rate` field (outside-view anchor) — cannot bootstrap without historical data.
- `brier_history` array — requires the calibration ritual to be running.
- `anomaly_flag` — requires stated-vs-revealed divergence detector.
- `last_interacted` / `current_weight` (decayed runtime value) — requires decay engine.
- Background AHP transitivity audit — agent-invoked in `/maintain` for now.

## 3. Urgency propagation formula

### 3.1 Formula

```
urgency_contribution(task → target) = S_lex(target.severity)
                                     × W_edge(contributes_to.weight)
                                     × f(Slack(target))
```

Where:

- `S_lex(s)` — step function:
  - `s == 4 && goal_type == "committed"` → `10_000`
  - else → scalar from priority→weight table (reuse existing priority mapping: P0=5, P1=3, P2=2, P3=1, default=0.5; adopt target.severity→P-level isomorphism: SEV0=P3, SEV1=P2, SEV2=P1, SEV3=P0).

- `W_edge` — the numeric anchor from the Renooij-Witteman term (§2.2).

- `Slack = due - now - e'` where `e'` is the estimated execution time (sum of descendant task scope × uncertainty). Least Slack Time, not Earliest Deadline First — LST uses execution estimates to prevent starvation of large critical tasks (brief 3 §4.2).

- `f(Slack)` — piecewise-exponential (brief 3 §4.4):
  - `Slack > safe_horizon` → `ε` (negligible; don't clutter focus weeks out)
  - `0 < Slack ≤ safe_horizon` → `e^(k × (safe_horizon - Slack))`
  - `Slack ≤ 0` → `1.0` (unlock full `S_lex`)

`safe_horizon` and `k` are runtime parameters, default to `safe_horizon = 7 days`, `k` tuned so warning phase covers ≈1 order of magnitude.

### 3.2 Integration

Extend the existing `compute_downstream_metrics` BFS (`mem/src/graph_store.rs:1347-1470`):

```rust
// Pseudocode — when visiting a node with contributes_to edges:
for edge in node.contributes_to {
    if let Some(target) = nodes.get(&edge.to) {
        let s_lex = lexicographic_weight(target.severity, target.goal_type);
        let w_edge = renooij_witteman_anchor(edge.weight);
        let slack = lst_slack(target.due, now, estimated_execution_time(node));
        let f = piecewise_exponential(slack, safe_horizon, k);
        total_weight += s_lex * w_edge * f;
    }
}
```

This composes additively with the existing blocks/soft_blocks BFS contribution. **One scalar, one ranking.**

### 3.3 Invariants

- When no targets are present in a subgraph, the formula reduces to `0` — backwards compatible.
- A task with `contributes_to` but no declared Severity 4 target never triggers the lexicographic override.
- Completed targets are excluded from the BFS (mirrors `COMPLETED_STATUSES` handling).

## 4. Calibration ritual (deferred)

Full Brier-scoring infrastructure is **not MVP**. What we build later (once the pilot justifies it):

- **Monthly cadence** in `/maintain`: for each edge whose target reached terminal state, the agent prompts the user for a binary "was this task materially necessary?" and computes `(W_edge - outcome)²`. Rolling 90-day aggregate surfaces in the dashboard.
- **Stated-vs-revealed divergence**: `mem` query that flags `contributes_to` edges with high `W_edge` but zero interaction on the source task in N days. Surfaced in `/daily`. Resolution: agent presents a micro A/B re-rank to the user.
- **Transitivity audit**: AHP-style consistency check — if `A contributes_to B = Probable` and `B contributes_to C = Probable` but `A contributes_to C = Improbable`, flag the triad. Server computes, agent surfaces.
- **Post-mortem**: if a SEV4 target resolved with large remaining slack OR deadline passed without the stated consequence, auto-file a task for calibration review.

These are the levers for keeping the graph honest against epistemic entropy. Deferring until the pilot + at least one real SEV4 cycle prove we need them (see VISION: "Components earn their keep").

## 5. Pilot alignment — [[task-0779b81b]]

The pilot currently specifies `severity: 1` for "maintain QUT employment" — under this spec that should be `severity: 4, goal_type: committed`. The pilot also uses `contributes_to: [{to, weight: 1.0, why}]` — under this spec `weight` must be a verbal term (likely `Certain` for contractual obligations).

The pilot will exercise:

- Target node creation (§1.1 MVP fields)
- Multiple tasks linking via `contributes_to` (§2.1)
- Observation of whether the target's presence changes daily focus surfacing

It will **not** exercise: Brier scoring, decay, anomaly detection, transitivity audits. Those are §4 deferred.

## 6. Open questions

1. **Parser first, or frontmatter-only pilot first?** Current plan: pilot runs with inert YAML (parser ignores `contributes_to`) to validate the ergonomics before Rust work. If the pilot reveals the model is right, file the parser + BFS-integration task under this epic.
2. **Severity → priority isomorphism**. We reuse the existing P0–P4 scale for SEV0–3 to preserve "one signal". Is that the right mapping, or should we keep severity as a separate field and blend at display time? MVP keeps them linked; revisit if the pilot exposes friction.
3. **`e'` (estimated execution time) source**. Today's frontmatter has `scope` and `uncertainty` as informal fields. LST needs a concrete number. MVP: sum of `scope` minutes across descendants, fall back to a coarse bucket (XS/S/M/L/XL → 30m/2h/1d/3d/1w) if unset.
4. **Concurrency cap enforcement**. Surfaced in `/daily` — but by whom? Proposal: `/daily` queries `mem` for count of active SEV4 targets; if > 2, includes a warning line in the briefing. No blocking.
