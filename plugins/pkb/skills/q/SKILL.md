---
name: q
type: command
description: Stage 1 Intake & Capture--place an ask or idea on the graph under the right parent, wire contributes_to/depends_on, densify with wikilinks, and record strategic valuation at intake.
allowed-tools: [Skill, AskUserQuestion, mcp__services__pkb__create_task, mcp__services__pkb__update_task, mcp__services__pkb__update_body, mcp__services__pkb__search, mcp__services__pkb__task_search, mcp__services__pkb__batch_reparent]
---

# /q -- Strategic Intake & Graph Placement

Capture natural-language asks and situate them on the strategic graph: parented, connected, and evaluated at intake. Intake leaves work at `status: inbox`; do not decompose, design probes, or release for dispatch.

## Workflow

1. **Classify level**: Goal (identity state), Target (milestone/stakes), Epic (multi-unit body), Task (single session), or Spike (`classification: spike` for uncertainty).
2. **Title**: Write a concise, verb-led imperative (e.g. `Implement X`). Never include personal names.
3. **Parent**: Assign a valid, active parent (epic, target, or active task). Never leave tasks unparented or in catch-alls.
4. **Search and adopt**: Search existing tasks before creating. If a matching task exists, update it or reparent with `pkb__batch_reparent(ids=[...], new_parent="<parent_id>", dry_run=False)`. Mint human-readable IDs (`id: "aops_<slug>"`).
5. **Densify graph edges**:
   - `contributes_to`: Point to target or goal with `stated_weight` (`critical`, `high`, `medium`, `low`) and a one-sentence justification ([[kb_pauli_prioritisation_doctrine]]).
   - `depends_on`, `soft_depends_on`, `supersedes`: Link dependencies. Omit redundant sibling edges under the same parent.
   - Task structure lives in edges, never in prose.
6. **Value at intake**: Record marginal benefit, synergies, value of information, and effort where established. Never write `focus_score`.

## Output

```markdown
- Captured [TASK-ID] - [TASK-TITLE] (under [PARENT-ID])
```

## Must Not

- Create standalone "decision" tasks or file questions as tasks (model alternatives as mutually exclusive option nodes and unknowns as spikes).
- Include personal names in titles or filenames.
- Write `intent` (or legacy `priority`), or set `severity` on non-target nodes.
- Promote or release work for dispatch (leave at `inbox`).
