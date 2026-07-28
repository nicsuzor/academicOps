# Graph Placement — search, place, wire, densify

Detail for [SKILL.md](../SKILL.md) steps 1–3. Mechanics only; the judgment calls (which parent,
which weight) stay with the agent running the skill.

## Search before create

- `mcp__services__pkb__search()` / `mcp__services__pkb__pkb_context()` — semantic search over the PKB for anything that
  already covers this ask.
- `mcp__services__pkb__task_search()` — narrower, task-scoped search when you already suspect the right area.
- `mcp__services__pkb__get_semantic_neighbors(id)` — once you have a candidate parent or a near-duplicate,
  check its neighbourhood before deciding.

If something already covers this ask: update it (`mcp__services__pkb__update_task` / `mcp__services__pkb__append`), do
not create a sibling. If it partially covers it, extend rather than duplicate.

## Placement ladder

| Signal                            | Level     | Where                                               |
| --------------------------------- | --------- | --------------------------------------------------- |
| Desired future state, multi-month | Goal      | `${ACA_DATA}/goals/`                                |
| Bounded effort toward a goal      | Project   | `${ACA_DATA}/projects/`                             |
| Session/PR-sized verifiable unit  | Task/epic | via PKB, parent = the project or goal it serves     |
| High uncertainty, need info first | Spike     | task with `classification: spike`, parent unchanged |

Use `mcp__services__pkb__create_task()` with the resolved parent. If the right parent is genuinely ambiguous
between two live candidates — not just unclear from a quick look — that is a SURFACE case (see
SKILL.md step 6), not a coin flip.

## `contributes_to` — the valuation edge

Directional, **reverse-scoring**: it raises the _target's_ `downstream_weight`/`focus_score`, never
the source task's own. Wire it from the new task to the real `type: target` node it serves —
never a vague goal — with a Renooij-Witteman verbal weight and a one-sentence justification.

| Term        | Weight | Meaning                                                    |
| ----------- | ------ | ---------------------------------------------------------- |
| Certain     | 1.00   | Single point of failure — if this fails, the target fails. |
| Probable    | 0.85   | Strong contribution; very likely needed.                   |
| Expected    | 0.75   | Expected contribution; standard path.                      |
| Fifty-Fifty | 0.50   | Redundancy exists; half the importance.                    |
| Uncertain   | 0.25   | Weak contribution; might be relevant.                      |
| Improbable  | 0.15   | Very weak contribution.                                    |
| Impossible  | 0.00   | No contribution.                                           |

```yaml
contributes_to:
  - to: <target-id>
    stated_weight: <term>       # verbal term only, never a raw decimal
    justification: "<one sentence>"
```

Write the verbal term, not the decimal. Justification is mandatory. Search before wiring — check
the target doesn't already have this edge.

## Densify — the other relations

Wiring one `contributes_to` edge is not densifying; the graph should pick up several relations per
new task where they genuinely exist:

- **`depends_on`** (hard) — task cannot proceed without this. Ask: "what happens if the dependency
  never completes?" Impossible/wrong output → hard. Still valid but less informed → `soft_depends_on`.
- **`soft_depends_on`** (soft) — benefits from context, doesn't block. Use for sibling work,
  strategic validation, environmental factors that don't gate correctness.
- **`supersedes`** — this task replaces prior work; mark the replaced node `status: cancelled` with
  the edge pointing at its replacement, don't silently orphan it.
- **Related wikilinks** — genuinely related nodes (prior attempts, adjacent decisions, siblings)
  named in body prose as `[[id]]`. Not a formal typed edge — just don't leave a new task an island
  when the bundle's `## Context`/`## Dependencies` sections already named neighbours.

`mcp__services__pkb__get_dependency_tree(id)` and `mcp__services__pkb__get_network_metrics(id)` are useful for checking
what a candidate parent/target already connects to before you add more.
