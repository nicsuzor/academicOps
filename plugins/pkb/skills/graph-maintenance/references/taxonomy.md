# PKB Taxonomy

The vocabulary every PKB skill writes in. Where another skill needs a node type,
an edge, a weight, a status, or the priority rules, it uses these — it does not
restate them.

## Node types

| Type     | What it is                                                                                                 | In the work tree? |
| -------- | ---------------------------------------------------------------------------------------------------------- | ----------------- |
| `goal`   | An identity commitment — who I am, what I define myself by. Roughly ten of them. Unquantifiable.           | No                |
| `target` | A measurable milestone — done or not done. Carries the stakes: `severity` + `consequence`, optional `due`. | No                |
| `epic`   | A bundle of work that parents other work.                                                                  | Yes               |
| `task`   | A deliverable one owner finishes in one focused session.                                                   | Yes               |
| `learn`  | A spike or noted finding. Not directly actionable; resolves by decomposing into follow-ups.                | Yes               |

`epic` and `task` are the same object; the label tracks whether it parents
children, not a fixed depth. Decomposition stops when residual uncertainty is
low enough to act, not at a depth.

`goal` and `target` sit beside the work tree, never in it: never a parent, never
parented, never in a to-do surface, excluded from orphan detection. Work reaches
them by `contributes_to`, which is metadata, not structure.

`classification` (`bug`, `feature`, `spike`, `research`, `chore`, …) is a
descriptive subtype. It does not enter `focus_score`. Set it from the task's
shape; never override a value the user set.

`project` is not a hierarchy level. It is a repository slug carried as
`project: <slug>` frontmatter, read at dispatch to choose the worker's
worktree. Children inherit the parent's value. A task with no routable `project`
cannot be dispatched. **The slug is baked into the task id at creation and
cannot be renamed afterwards** — `update_task` changes the field, not the id.
File it right the first time; if the right slug is not obvious, walk the ancestor
chain, and if that yields nothing, ask.

## Edges

| Edge              | Means                                           | Cycles       |
| ----------------- | ----------------------------------------------- | ------------ |
| `parent`          | B is part of A. One parent, strict tree.        | Never valid  |
| `depends_on`      | B cannot start until A completes.               | Pathological |
| `soft_depends_on` | A makes B easier or better.                     | Healthy      |
| `contributes_to`  | B advances target/goal A. Weighted.             | Pathological |
| `closes`          | This node completes that target or PR.          | Pathological |
| `link`            | A mentions B. Body `[[wikilinks]]`.             | Irrelevant   |
| `supersedes`      | A replaces B.                                   | Pathological |
| `similar_to`      | Auto-discovered similarity. Never load-bearing. | Healthy      |

A hard dependency cycle is a decomposition failure — merge the nodes or pick a
direction. Soft cycles are normal: writing clarifies methodology, methodology
improves writing.

## `contributes_to` — the valuation edge

```yaml
contributes_to:
  - to: <target-or-goal-id>
    stated_weight: Expected # verbal term only; raw decimals are rejected at parse
    justification: "one sentence on why this contributes"
```

| Term        | Weight | Means                                                      |
| ----------- | ------ | ---------------------------------------------------------- |
| Certain     | 1.00   | Single point of failure — if this fails, the target fails. |
| Probable    | 0.85   | Strong contribution; very likely needed.                   |
| Expected    | 0.75   | Standard path.                                             |
| Fifty-Fifty | 0.50   | Redundancy exists; half the importance.                    |
| Uncertain   | 0.25   | Weak; might be relevant.                                   |
| Improbable  | 0.15   | Very weak.                                                 |
| Impossible  | 0.00   | No contribution.                                           |

Semantics are Birnbaum importance: the marginal probability that missing this
work guarantees the target fails.

**The edge is reverse-scoring.** It raises the _target's_ `downstream_weight`
and `focus_score` — never the source task's own. You cannot lift a task's score
by wiring more outgoing edges; they lift the things it points at. To give a task
more weight, put `severity` on the target it serves and wire the edge. This is
the most common mistake made with this edge.

Justification is mandatory. Search before wiring — the edge may already exist.

## Priority — the user's intent, never an estimate

| Band | Name          | Means                                                               |
| ---- | ------------- | ------------------------------------------------------------------- |
| P0   | Critical      | Active incident, pipeline blocked, or a deadline already breached.  |
| P1   | Active intent | Wanted now; in flight this week; near-term consequence if it slips. |
| P2   | Active work   | Routine in-flight work, inside the active window.                   |
| P3   | Planned       | On the roadmap, not yet active. **Default for new tasks.**          |
| P4   | Backlog       | Logged for the record; may never be done.                           |

Lower number wins. **Agents never originate a non-default band.** Leave new work
at P3 and write another band only on an express instruction in the current turn.
To express importance, reach for `contributes_to` weight and target `severity` —
never `priority`.

P0 additionally requires a written, verified justification in the body showing
that the whole pipeline is blocked. Uncalibrated P0 is rejected at the write
boundary.

**`due` is for real external deadlines only** — a portal closes, a meeting
happens, a window ends. Never invent one to make urgency show up in the score;
one fabricated deadline poisons trust in every real one. "I want this today" is
P1, not a `due` date.

## Severity — targets only

| Level | Name       | Example                                                             |
| ----- | ---------- | ------------------------------------------------------------------- |
| SEV0  | Negligible | No consequence beyond self. **Default.**                            |
| SEV1  | Low        | Small reputational or time cost.                                    |
| SEV2  | Moderate   | Meaningful commitment; recoverable.                                 |
| SEV3  | High       | Serious, hard to recover.                                           |
| SEV4  | Terminal   | Job loss, bankruptcy, severe health, legal. Lexicographic override. |

`severity` lives on `type: target` nodes, paired with `consequence` prose.
Non-zero severity on a task, epic, or goal is prohibited and rejected at the
write boundary: the score bonus is calibrated for terminal obligations and
inverts the ready queue when applied to ordinary work. Tasks inherit stakes
through `contributes_to`, not by carrying severity.

`goal_type` (`committed` / `aspirational` / `learning`) gates propagation: only
`committed` targets get the SEV4 override, so moonshots cannot hijack the queue.

## Status

| Status        | Means                                                                    |
| ------------- | ------------------------------------------------------------------------ |
| `inbox`       | **Default for everything new.** Captured, not triaged.                   |
| `ready`       | Decomposed to leaves with every hard dependency resolved.                |
| `queued`      | The user has released it for agent dispatch. Agents pull only from here. |
| `in_progress` | Claimed and being worked.                                                |
| `merge_ready` | Parked **on a PR**. May be auto-closed when the PR merges.               |
| `review`      | Parked **on a human decision**. Never auto-closed — always re-surfaced.  |
| `partial`     | A finished component shipped; the rest decomposed into follow-ups.       |
| `blocked`     | Waiting on an external dependency.                                       |
| `paused`      | Stopped deliberately, intended to resume.                                |
| `someday`     | Parked idea; explicit deferral.                                          |
| `done`        | Complete.                                                                |
| `cancelled`   | Will not be done.                                                        |

**`merge_ready` and `review` are not the same parked state.** A `merge_ready`
task resolves against its PR. A `review` task resolves against a person, usually
has no PR at all, and a sweep that reconciles it against PRs will find nothing,
change nothing, and let it rot silently. Surface every `review` task, every
sweep. A merged PR on a `review` task is evidence the decision can be made, not
authority to close it.

A `merge_ready` task with no resolvable PR is anomalous — surface it, do not
close it.

`queued` is the human gate. Agents do not promote work into it.

## Retiring superseded work

When work is carved up, moved, or replaced, the original must leave the
dispatchable set — otherwise the next pull selects it and dispatches a worker
against a brief describing work already shipped.

- Set the original `status: cancelled` (or `done` if its own acceptance was
  genuinely met before the carve-up). Terminal status is what makes it
  unselectable; no extra field is needed.
- Put a `supersedes` edge on each replacement, so the redirect is discoverable
  from the live side.
- Do not rewrite the stale body. Supersession fixes dispatchability, not content;
  git holds the fossil.

Whatever creates the replacements cancels the original in the same operation.

## Default parent

Every task has a parent. Resolve the most contextually appropriate one. During
an emergency handover or an ad-hoc capture with no obvious home, use
`adhoc-sessions` rather than failing or omitting the field.

## Actionable vs ready

**Actionable** is everything not terminal (`done`, `cancelled`, `someday`) —
the whole working set, and what dashboards count. **Ready** is the narrow
subset: fully decomposed leaves with zero unmet dependencies. Claimed and parked
work is actionable but not ready.
