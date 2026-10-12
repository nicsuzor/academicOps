---
name: q
type: command
description: Stage 1 Intake & Capture--place an ask or idea on the graph under the right parent, wire what it serves, propose values, and record strategic placement at intake. Exclude for starting workers on ready tasks (use /dispatch) or decomposing objectives (use /decompose).
allowed-tools: [Skill, AskUserQuestion, mcp__services__*]
---

# /q -- Strategic Intake & Graph Placement

Capture natural-language asks and situate them on the strategic graph: parented, connected, and valued at intake per `specs/workflows/graph-valuation.md` (R1).

## Placement and Valuation (R1)

1. **Search before creating**: Search the PKB for related targets and open work the input could serve. Reuse an existing node where one matches.
2. **Consolidate and place**: Consolidate where possible (merge duplicates, reparent related tasks). Place the node under an active parent container (or `part_of` edge under FQ1).
3. **Affordable loss check (S24)**: Evaluate affordable loss before admitting commitments. If prospective downside or commitment cost violates affordable loss, flag as a priority ask for Nic rather than admitting to the flow. Flow maths remains unpolluted by subjective risk gating.
4. **Wire what it serves**: Add one edge per thing the work serves, crossing project boundaries where they apply (U11). Outgoing edges carry the FR §5.1 contract with `set_by: agent-proposed`:
   - `label`: `serves`, `needs`, `supports`, `alternative`, or `settles`.
   - `quantum`: Proposed in §5.4 words (`all`, `most`, `a good part`, `some`, `a little`, `none`) or float `0.0..=1.0`; empty reads at default quantum 0.0 (S7). Ask: "If this were never done and everything else were, how much of the target would be lost?" (FR:346).
   - `probability`: Proposed in §5.5 words (`certain`, `probable`, `expected`, `fifty-fifty`, `uncertain`, `improbable`, `impossible`) or float `0.0..=1.0` (default 1.00). Odds live on the edge into the target and chain by multiplication (S25).
   - `effect`: `helps` (default) or `harms` (when work endangers a target, S12, U13).
   - `justification`: One sentence on what the work delivers to the target.
   - `set_by: agent-proposed`.
5. **Capital stock hubs (S27)**: Wire foundational investments that expand future optionality (reputation, relationships, tool scaffolding, capital reserves) directly to capital stock targets rather than inventing speculative multi-hop downstream chains.
6. **A bare idea stays bare**: An idea with no clear link to anything priced gets its container and no other edge (U9, I7). Never invent a link to make it count.
7. **Opportunity is one node plus its edges**: Mark opportunities as `classification: opportunity` (I9, U10). Adding it changes no other node's fields.
8. **Dates (R5)**: Record any date as `due` with `deadline_class`:
   - `fake`: Default for captured dates where no real loss lands on it.
   - `soft`: Input carries Nic's acceptance or sent mail agreeing to the date.
   - `hard`: Nic explicitly states the date is hard, or a published real-loss date proposed `hard`.
     Never derive a date from urgency.
9. **Effort**: Record `effort` duration string when the input states it or work is a known kind (read by the cliff lane).
10. **Decisions and decomposition probes (FQ8, EVPI)**: When input is a choice between options, wire each option `alternative` to the decision node `D`. Empirical probes/spikes wire `settles` to `D` ($q \in (0, 1]$).
11. **Do not write**: `intent` (FQ10), `severity` (FQ24), `stakeholder` as a weight (FQ25), target worth, `set_by: nic`, `soft_depends_on`, or `supersedes` (FR:448).

## Headless Context (Email, Mobile Capture)

When invoked headlessly (e.g. correspondence sweep or capture intake):

- Apply the same placement and valuation steps without prompting the user.
- If the container or targets cannot be identified with confidence, leave the capture note untouched for the next interactive pass (`specs/workflows/capture-intake.md`). Do not guess.

## Task Body

**Title**: Write a concise, verb-led imperative (e.g. `Implement X`).

**Description**: Synthesize the ask in a minimal task body:

- Link new messages to prior context, recompose asks into a clear logical structure, and cite message IDs as pointers.
- Do not quote user words verbatim; do not add extraneous narrative or implementation plans.
- Leave ambiguity unresolved in the task; do not guess at intent.

**Other sections**: Never restate structured metadata or task edges in prose. Interconnections live in edges, not body prose.

## Output

Return a reference to the task created or updated:

```markdown
- Captured [TASK-ID] - [TASK-TITLE] (under [PARENT-ID]: [PARENT-TITLE])
```
