---
id: wire-edges
name: wire-edges-workflow
category: planning
bases: [base-task-tracking]
description: Interactive flow for densifying contributes_to edges on target nodes
permalink: workflows/wire-edges
tags: [workflow, planning, edges, targets, densify]
version: 1.0.0
---

# Wire Edges Workflow

**Purpose**: Guides the user through linking active tasks to high-level target nodes using structured contribution edges.

**When to invoke**: User says "wire edges", "link to target", "add contributes_to", or specifically mentions "Renooij-Witteman".

## Core Process

1. **List Targets**: Query the PKB for all nodes with `type: target`.
   - Tool: `mcp__pkb__list_tasks(type="target")`

2. **Select Target**: Present the list of targets to the user and ask them to select one or more targets to process in this session.
   - Tool: `AskUserQuestion`

3. **Find Candidates**: For each selected target, identify candidate tasks that might contribute to it.
   - **Search strategy**:
     - Tasks in the same project as the target.
     - Tasks mentioned in the target's body under "Active children to wire" or similar.
     - Semantic neighbors: `mcp__pkb__get_semantic_neighbors(target_id)`.
     - Recent tasks with status: ready, queued, or in_progress: mcp__pkb__list_tasks(status=["ready", "queued", "in_progress"], limit=20)
   - Filter out tasks that already have a `contributes_to` edge pointing to the target.

4. **Iterate & Elicit**: For each candidate task, present its summary (ID, Title, Project, Status) and the target summary.
   - **Ask**: "Does this task contribute to achieving [Target]?"
   - If user confirms:
     - **Select Weight**: Prompt for weight using the Renooij-Witteman scale.
       - _Options_: Certain, Probable, Expected, Fifty-Fifty, Uncertain, Improbable, Impossible.
     - **Capture Justification**: Prompt for a single-sentence justification (e.g., "Direct contribution to X").
     - Write Edge: Use the mcp__pkb__update_task tool to add the edge to the task's frontmatter.

5. **Report**: After processing candidates, provide a summary report of edges added.

## Renooij-Witteman Scale Reference

| Term            | Weight | Meaning (Birnbaum Importance)                         |
| --------------- | ------ | ----------------------------------------------------- |
| **Certain**     | 1.00   | Single point of failure; if this fails, target fails. |
| **Probable**    | 0.85   | Strong contribution; very likely needed.              |
| **Expected**    | 0.75   | Expected contribution; standard path.                 |
| **Fifty-Fifty** | 0.50   | Redundancy exists; half the importance.               |
| **Uncertain**   | 0.25   | Weak contribution; might be relevant.                 |
| **Improbable**  | 0.15   | Very weak contribution.                               |
| **Impossible**  | 0.00   | No contribution.                                      |

## Canonical Edge Schema

```yaml
contributes_to:
  - to: <target-id>
    stated_weight: <term>
    justification: "<one-sentence justification>"
```

## Effect on Scores — what the edge actually does

A `contributes_to` edge is **directional and reverse-scoring**. `compute_downstream_metrics` (in the `mem` repo, `graph_store.rs`) reads it as a _reverse_ edge for `downstream_weight`: the edge raises the **target's** `downstream_weight` — and thus the target's `focus_score` — and **never the source task's own**.

**Common mistake this prevents:** you cannot raise a _task's_ own `focus_score` by adding `contributes_to` edges from it. If a task's score is floored (`downstream_weight` 1.0, `focus_score` at the floor), wiring more outgoing edges will not move it — they move the targets it points at.

**How a task inherits stakes (the sanctioned channel):** put `severity` on the **target** node (`type: target`), then wire the task to it with `contributes_to`. The task then inherits urgency _down_ the edge — Birnbaum-weighted by `stated_weight`, discounted by slack. **Never set `severity` on the task itself:** the flat SEVn focus bonus is calibrated for terminal target obligations and will invert the ready queue; the write-boundary guard rejects it. See [[../../remember/references/TAXONOMY.md#severity-ladder-sev0sev4]] (Severity Ladder + Severity Target Boundary).

## Critical Rules

- **Justification is mandatory**: Every edge MUST have a justification.
- **Verbal terms only**: Never write raw decimals to the `stated_weight` field.
- **Search before asking**: Always verify if an edge already exists to avoid duplicates.
- **One sentence only**: Keep justifications concise.
- **Focus on ready tasks**: Prioritize wiring tasks that are `ready` or `in_progress`.
- **Edges score the target, not the source**: a `contributes_to` edge never raises the source task's own `focus_score`. To give a _task_ more weight, add `severity` to the _target_ it points at — never to the task. See "Effect on Scores" above.
