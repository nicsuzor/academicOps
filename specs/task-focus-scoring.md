---
title: Task Focus Scoring
type: spec
status: active
tier: ux
depends_on: []
tags: [spec, ux, scoring, dashboard, intentions]
---

# Task Focus Scoring

How tasks are classified as "hot" (visible in default views) or "cold" (searchable but hidden), and how the ready queue is ranked.

## Problem

A task system serving an ADHD brain will always have more tasks than capacity. This is a permanent condition, not a backlog to be cleared. The system must surface what matters for what the user **intends to accomplish**, not present an undifferentiated queue.

1. Start from declared intentions — what the user is trying to get done right now
2. Surface the right tasks at the right time within intention scope
3. Keep everything else searchable without cluttering focus views
4. Rank by strategic value, not by insertion order

When the user declares intentions (see [[intentions.md]]), the intention subgraph becomes the primary scope. Tasks outside intentions still exist and can surface when urgent, but they're secondary. When no intentions are active, `intention_alignment` is 0.0 for all tasks and the remaining signals determine ranking.

## Design principles

1. **Scoring, not sorting.** Tasks get a continuous focus score. Views apply a threshold. No binary hot/cold tag to maintain.
2. **Transparent.** The score is visible and the formula is documented. Users can understand why a task is surfaced.
3. **Automatic.** Scores recompute on query. No manual tagging, no "move to cold" action needed.
4. **Reversible.** Nothing is deleted or archived by the scoring system. A task's score can rise if conditions change (e.g., a dependency chain activates it).
5. **ADHD-aware.** The system manages overflow by design. "Too many tasks" is the normal state, not an error.

## Focus score

Each task's focus score is computed from weighted signals:

```
focus_score = (
    w_intention   * intention_alignment  +
    w_downstream  * downstream_signal    +
    w_priority    * priority_signal      +
    w_project     * project_activity     +
    w_recency     * recency_signal       +
    w_blocking    * blocking_urgency     +
    w_user        * user_boost
)
```

### Signal definitions

| Signal                | Range     | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| --------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `intention_alignment` | 0.0 - 1.0 | Whether this task is within an active intention's subgraph (see [[intentions.md]]). 1.0 if the task is a descendant of any active intention root, or in its dependency frontier. 0.2 if the task shares the same `project` as an intention root but is outside the subgraph. 0.0 otherwise. When no intentions are active, this signal is 0.0 for all tasks and the other signals dominate naturally.                                                                                                                 |
| `downstream_signal`   | 0.0 - 1.0 | Normalized downstream dependency count: `min(1.0, log(1 + direct_dependents) / log(1 + k))` where `k` is a capping constant (default: 10, configurable). Counts direct dependents only (not transitive closure) to keep computation cheap and the signal interpretable. A task blocking 10+ others = 1.0.                                                                                                                                                                                                             |
| `priority_signal`     | 0.0 - 1.0 | Derived from the `priority` field: `(4 - priority) / 4`. Priority 0 (critical) = 1.0, priority 4 = 0.0.                                                                                                                                                                                                                                                                                                                                                                                                               |
| `project_activity`    | 0.0 - 1.0 | How active is this task's project? Measured as `modified_in_window / max(project_task_count, 3)` where window is last 14 days. Using `max(, 3)` as a minimum denominator avoids discontinuity at the small-project boundary. For tasks with `project: null`, `project_activity` = 0.0. Note: this signal is intentionally self-reinforcing — active projects attract more work, which keeps them active. Other signals (priority, blocking, user_boost) ensure cold-project tasks can still surface when they matter. |
| `recency_signal`      | 0.0 - 1.0 | Decay function on `modified` timestamp. 1.0 if modified today, decaying exponentially with `exp(-days / 30)` (≈0.05 at 90 days). Implementations should clamp to 0.0 at or after 90 days.                                                                                                                                                                                                                                                                                                                             |
| `blocking_urgency`    | 0.0 - 1.0 | 1.0 if this task is explicitly blocking a task with `status: in_progress`. 0.5 if blocking a task with `status: active`. 0.0 otherwise.                                                                                                                                                                                                                                                                                                                                                                               |
| `user_boost`          | 0.0 - 1.0 | Explicit user signal. Set via `focus: boost` in frontmatter or daily note mentions. Decays after 7 days if not refreshed.                                                                                                                                                                                                                                                                                                                                                                                             |

### Default weights

These are **starting values only** — there are no theoretically correct ratios. The right weights depend on the task graph shape, project cadence, and how the system is used in practice. Expect to recalibrate after observing score distributions.

| Weight         | Value | Initial rationale                                            |
| -------------- | ----- | ------------------------------------------------------------ |
| `w_intention`  | 0.30  | Declared intention is the strongest signal — what you intend |
| `w_downstream` | 0.20  | Unblocking value within the intention scope                  |
| `w_priority`   | 0.15  | User-assigned priority                                       |
| `w_project`    | 0.10  | Active projects pull related tasks into focus                |
| `w_recency`    | 0.10  | Recently-touched tasks are more likely to be relevant        |
| `w_blocking`   | 0.10  | Urgency from blocking in-progress work                       |
| `w_user`       | 0.05  | Explicit user focus boost                                    |

Weights are configurable via `$AOPS_CONFIG/focus-weights.yaml`. They MUST sum to 1.0.

### Why not FIFO or LIFO

- **FIFO** (oldest first) punishes the user for capturing ideas early. Old tasks rot at the top.
- **LIFO** (newest first) means older important work never surfaces. Recency bias.
- **Focus scoring** is multi-dimensional. A 6-month-old task that blocks three other tasks and is in an active project scores higher than yesterday's low-priority note-to-self.

## Hot/cold threshold

The focus score determines visibility in default views:

| Score range | Classification | Behaviour                                                                                                |
| ----------- | -------------- | -------------------------------------------------------------------------------------------------------- |
| >= 0.3      | **Hot**        | Shown in `list_tasks(status="active")` by default                                                        |
| < 0.3       | **Cold**       | Hidden from default view. Shown with `list_tasks(temperature="all")` or `list_tasks(temperature="cold")` |

The threshold (0.3) is configurable via `$AOPS_CONFIG/focus-weights.yaml`.

### What makes a task go cold

A task naturally goes cold when:

- Its project has no recent activity (low `project_activity`)
- It hasn't been touched in weeks (decaying `recency_signal`)
- It has no downstream dependencies (zero `downstream_signal`)
- Its priority is low (3-4)
- No user boost active

This is automatic. No manual archival, no triage, no "declare bankruptcy."

### What brings a task back hot

A cold task warms up automatically when:

- The user declares an intention that includes it in the subgraph (`intention_alignment` → 1.0)
- The user boosts it (`focus: boost`)
- Its project becomes active again (someone works on a sibling task)
- It starts blocking in-progress work
- Its priority is raised
- It's mentioned in a daily note

## API changes

### `list_tasks` additions

```python
list_tasks(
    status="active",       # existing (active = ready to work on)
    temperature="hot",     # NEW: "hot" (default), "cold", "all"
    sort_by="focus_score", # NEW: "focus_score" (default for ready), "priority", "created", "modified"
    limit=30,              # existing, default changes from 50 to 30 for "hot"
)
```

When `temperature` is not specified:

- `status="active"` defaults to `temperature="hot"`
- All other statuses default to `temperature="all"`

### Task metadata additions

Each task gains computed (not stored) fields:

```yaml
# Returned in list_tasks and get_task responses
_focus_score: 0.72
_temperature: hot    # derived from score vs threshold
_score_breakdown:    # optional, for debugging
  intention: 0.30
  downstream: 0.14
  priority: 0.15
  project_activity: 0.05
  recency: 0.03
  blocking: 0.05
  user_boost: 0.00
```

These are computed at query time, not stored in the task file.

## Configuration

```yaml
# $AOPS_CONFIG/focus-weights.yaml
focus:
  weights:
    intention: 0.30
    downstream: 0.20
    priority: 0.15
    project_activity: 0.10
    recency: 0.10
    blocking: 0.10
    user_boost: 0.05
  threshold: 0.3
  recency_time_constant_days: 30
  project_activity_window_days: 14
  user_boost_decay_days: 7
  downstream_capping_constant: 10
```

## Implementation notes

- Focus scores are computed at query time, not stored. This avoids stale scores and index maintenance.
- For large task sets (>1000), consider caching scores with a TTL matching the shortest decay window.
- The `_score_breakdown` field is optional and only returned when requested (e.g., `list_tasks(debug=true)`).
- The PKB server already computes weighted scores. This spec extends that existing capability with additional signals and a hot/cold threshold.

### Reconciliation with "Dumb Server, Smart Agent" (P#78)

This spec extends the server's computation scope. The focus score is deterministic — a fixed formula over existing fields (priority, modified date, graph topology) with externally configured weights. It contains no semantic analysis, no NLP, and no judgment calls.

The key distinction: the **formula and weights** are configured externally (agent/user domain), while the **computation** is server-side (same category as graph metrics like downstream dependency counts). The threshold is a configured number, not an inference.

This is explicitly acknowledged as an extension of the server's role from pure data access to include deterministic aggregation. The `mcp-decomposition-tools.md` and `pkb-server-spec.md` specs should be updated to reflect this when implementation proceeds.

## Giving effect

- `aops-tools/tasks_server.py` (external tools package) -- Implementation of focus scoring in list_tasks
- `$AOPS_CONFIG/focus-weights.yaml` (external config, not tracked in this repo) -- Weight and threshold configuration
- `$ACA_DATA/intentions.yaml` -- Active intention state, read at query time for `intention_alignment` signal
- [[intentions.md]] -- Intention concept spec (declares the `intention_alignment` signal)
- [[aops-core/WORKFLOWS.md]] -- No changes needed (routing is unaffected)

## Open questions

1. **Should the daily note auto-boost tasks?** If a task is mentioned in today's daily note, should that count as a user boost signal? (Proposed: yes, with 7-day decay.)
2. **Should completed tasks in a project count toward project_activity?** (Proposed: yes -- completing tasks shows the project is alive.)
3. **Should orphan tasks get a penalty?** Tasks with no parent have missing graph context. (Proposed: no explicit penalty -- they naturally score low on downstream_signal.)
4. **Weight tuning.** The default weights are a starting point — there are no theoretically correct ratios. Plan to observe score distributions in practice and adjust. The `_score_breakdown` field exists specifically to support this calibration. The introduction of `intention_alignment` as the dominant signal (0.30) is a major change — monitor whether it over-suppresses urgent non-intention work.
