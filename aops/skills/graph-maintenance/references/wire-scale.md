# Wire — Interactive Procedure, Schema, and Scoring Mechanics

## Core process

1. **List targets.** `mcp__pkb__list_tasks(type="target")`.
2. **Select target.** Present the list; `AskUserQuestion` for which to process this session.
3. **Find candidates**, per target:
   - Tasks in the same project as the target.
   - Tasks named in the target's body under "Active children to wire" or similar.
   - Semantic neighbours: `get_semantic_neighbors(target_id)`.
   - Recent `ready`/`queued`/`in_progress` tasks: `list_tasks(status=[...], limit=20)`.
   - Filter out tasks that already carry a `contributes_to` edge to this target.
4. **Iterate & elicit.** For each candidate, present its summary (id, title, project, status)
   against the target and ask: "Does this task contribute to achieving [Target]?" On confirmation,
   prompt for weight (Renooij-Witteman scale) and a single-sentence justification, then write the
   edge via `update_task`.
5. **Report.** Summarise edges added.

## Canonical edge schema

```yaml
contributes_to:
  - to: <target-id>
    stated_weight: <term>
    justification: "<one-sentence justification>"
```

## Effect on scores — what the edge actually does

A `contributes_to` edge is **directional and reverse-scoring**. `compute_downstream_metrics`
(`mem` repo, `graph_store.rs`) reads it as a _reverse_ edge for `downstream_weight`: the edge
raises the **target's** `downstream_weight` — and thus the target's `focus_score` — and **never
the source task's own**.

**Common mistake this prevents:** you cannot raise a _task's_ own `focus_score` by adding
`contributes_to` edges from it. If a task's score is floored (`downstream_weight` 1.0,
`focus_score` at the floor), wiring more outgoing edges will not move it — they move the targets
it points at.

**How a task inherits stakes (the sanctioned channel):** put `severity` on the **target** node
(`type: target`), then wire the task to it with `contributes_to` — never on the task itself. See
the Severity Ladder + Severity Target Boundary in
[[../../../../aops/skills/remember/references/TAXONOMY.md#severity-ladder-sev0sev4]].

## Critical rules

- **Justification is mandatory**: every edge MUST have a justification.
- **Verbal terms only**: never write raw decimals to `stated_weight`.
- **Search before asking**: always verify an edge doesn't already exist, to avoid duplicates.
- **One sentence only**: keep justifications concise.
- **Focus on ready tasks**: prioritise wiring tasks that are `ready` or `in_progress`.
- **Edges score the target, not the source**: to give a _task_ more weight, add `severity` to the
  _target_ it points at — never to the task.
