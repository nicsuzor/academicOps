---
name: q
type: command
description: Stage 1 Intake & Capture--place an ask or idea on the graph under the right parent, wire contributes_to/depends_on, densify with wikilinks, and record strategic valuation at intake.
allowed-tools: [Skill, AskUserQuestion, mcp__services__*]
---

# /q -- Strategic Intake & Graph Placement

Capture natural-language asks and situate them on the strategic graph: parented, connected, and evaluated at intake.

## Placement

1. Search the PKB for related tasks. Identify how this ask fits with existing, past, or planned work.
2. Consolidate the graph where possible: use your judgment to merge duplicates, reparent related tasks, split and recombine tasks to create a coherent structure.
3. Assign a parent task: the ask must be placed under a valid, active parent.
4. **Densify graph edges**:
   - `contributes_to`: Wire an edge if this task meaningfully contribtes to a 'target' or another task that is not an ancestor or descendant. Use your best judgment to set the quantum and certainty of the contribution. Provide a one-sentence justification for the edge. Avoid redundant sibling edges under the same parent.
   - `depends_on`, `soft_depends_on`, `supersedes`: Link dependencies. Use 'depends_on' edges to sequence work that must be done in order. Use 'soft_depends_on' edges to indicate that one task informs or supports another but is not a blocking pre-requisite. Use 'supersedes' edges to indicate that one task replaces or obsoletes another. Avoid redundant sibling edges under the same parent.

## Metadata

5. **Value at intake**: Record your best assessment of marginal benefit, synergies, value of information, and effort where established.
6. **Intent**: Set `intent` only when the user's own words name a band or its unambiguous equivalent (`critical`/`P0` → 0, `high` → 1, `active`/`do it now` → 2, `planned` → 3, `backlog`/`someday` → 4). If the ask comes directly from the user in their own words, you may set the intent to 'planned' (3) by default. Otherwise leave it unset. Never infer a band from tone, from urgency in the triggering incident, or from the parent's value.

## Task body

**Title**: Write a concise, verb-led imperative (e.g. `Implement X`). Do not include unecessary detail -- a short slug is best.

**Description**: Capture the ask in a task body without additional detail:

- You may rephrase or expand the prompt you were given to better capture the essence of the ask.
- Do not add implementation steps, execution methods, acceptance criteria, or any additional processes or requirements.
- Leave all ambiguity unresolved in the task. Do not guess at intent where it is unclear; do not infer extra details or constraints.

**Other sections**: Never restate structured metadata or task edges in the body.

- Interconnections live in edges; significance in metadata; neither belong in prose.
- Do not add unecessary sections to the task body.
- Do not add 'references', 'related', or 'see also' sections.

## Output

Return a reference to the task you created or updated, in the short form:

```markdown
- Captured [TASK-ID] - [TASK-TITLE] (under [PARENT-ID]: [PARENT-TITLE])
```
