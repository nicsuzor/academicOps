---
name: q
type: command
description: Stage 1 Intake & Capture--place an ask or idea on the graph under the right parent, wire what it serves, propose values, and record strategic placement at intake. Exclude for starting workers on ready tasks (use /dispatch) or decomposing objectives (use /decompose).
allowed-tools: [Skill, AskUserQuestion, mcp__services__*]
---

# /q -- Strategic Intake & Graph Placement

Capture natural-language asks and situate them on the strategic graph: parented, connected, and valued at intake per `specs/workflows/graph-valuation.md`. Questions and lookups are answered directly by the session that receives them; the task dispatch pipeline is used only for real code changes. Answer questions and lookups directly without capturing or queueing them as tasks.

## Placement and Valuation

1. **Search before creating**: Search the PKB for related targets and open work the input could serve. Reuse an existing node where one matches.
2. **Consolidate and place**: Consolidate where possible (merge duplicates, reparent related tasks). Place the node under an active parent container (or `part_of` edge).
3. **Affordable loss check**: Evaluate affordable loss before admitting commitments. If prospective downside or commitment cost violates affordable loss, flag as a priority ask for the user rather than admitting to the flow. Flow maths remains unpolluted by subjective risk gating.
4. **Wire what it serves**: Add one edge per thing the work serves, crossing project boundaries where they apply. Outgoing edges carry the edge contract with `set_by: agent-proposed`:
   - `label`: `serves`, `needs`, `supports`, `alternative`, or `settles`.
   - `quantum`: Proposed in words (`all`, `most`, `a good part`, `some`, `a little`, `none`) or float `0.0..=1.0`; empty reads at default quantum 0.0. Ask: "If this were never done and everything else were, how much of the target would be lost?".
   - `probability`: Proposed in words (`certain`, `probable`, `expected`, `fifty-fifty`, `uncertain`, `improbable`, `impossible`) or float `0.0..=1.0` (default 1.00). Odds live on the edge into the target and chain by multiplication.
   - `effect`: `helps` (default) or `harms` (when work endangers a target).
   - `justification`: One sentence on what the work delivers to the target.
   - `set_by: agent-proposed`.
5. **Capital stock hubs**: Wire foundational investments that expand future optionality (reputation, relationships, tool scaffolding, capital reserves) directly to capital stock targets rather than inventing speculative multi-hop downstream chains.
6. **A bare idea stays bare**: An idea with no clear link to anything priced gets its container and no other edge. Never invent a link to make it count.
7. **Opportunity is one node plus its edges**: Mark opportunities as `classification: opportunity`. Adding it changes no other node's fields.
8. **Dates**: Record any date as `due` with `deadline_class`:
   - `fake`: Default for captured dates where no real loss lands on it.
   - `soft`: Input carries the user's acceptance or sent mail agreeing to the date.
   - `hard`: The user explicitly states the date is hard, or a published real-loss date proposed `hard`.
     Never derive a date from urgency.
9. **Effort**: Record `effort` duration string when the input states it or work is a known kind (read by the cliff lane).
10. **Decisions and decomposition probes**: When input is a choice between options, wire each option `alternative` to the decision node `D`. Empirical probes/spikes wire `settles` to `D` ($q \in (0, 1]$).
11. **Do not write**: `intent`, `severity`, `stakeholder` as a weight, target worth, `set_by: user`, `soft_depends_on`, or `supersedes`.

## Headless Context (Email, Mobile Capture)

When invoked headlessly (e.g. correspondence sweep or `notes/mobile-captures/` intake):

1. **Read for homophones**: Treat voice-dictated captures as phonetic transcripts; resolve homophones in context before judging meaning or ambiguity.
2. **Classify and route each capture**:
   - **Task** (or **Expand** probe): If an existing task already carries the ask (Step 1), fold the capture into that task (`update_body`) and `delete` the capture after the write succeeds. Otherwise, convert the capture into a task in place via `convert_document(id=<capture-id>, type="task", status="ready"|"inbox")` so the same file and ID move out of `notes/mobile-captures/` into `tasks/` with task frontmatter, then set the verb-led imperative `title`, `parent`, `project`, `classification` (`probe` for Expand), `links`, and task body via `update_task` and `update_body`. Do not create a replacement task or edit PKB files on disk to simulate conversion.
   - **Note** (or **Expand** into an existing note): Synthesize into the target note (`update_body`) or create a canonical note (`create(type="knowledge", ...)`), then `delete` the capture only after the destination write succeeds.
   - **Discard**: Delete the capture via `delete`.
3. **Defer when uncertain**: Apply placement and valuation without prompting the user. If the classification, parent container, or target cannot be identified with confidence, or if `convert_document` fails, leave the capture note untouched in `notes/mobile-captures/` for the next interactive pass (`specs/workflows/capture-intake.md`). Do not guess.

## Task Body

**Title**: Write a concise, verb-led imperative (e.g. `Implement X`).

**Description**: Synthesize the ask in a minimal task body:

- Restate the user's terse, fragmented words into clear, complete tasks and notes, judged by fidelity to meaning and distinctions, not by wording.
- Keep the user's exact words only in the referent the premise check reads (`## Ask` and equivalents); do not treat keeping exact words in PKB outputs as a goal.
- Fault a restatement only for lost, added, or distorted meaning.
- Link new messages to prior context, recompose asks into a clear logical structure, and cite message IDs as pointers.
- Leave ambiguity unresolved in the task; do not guess at intent.

**Other sections**: Never restate structured metadata or task edges in prose. Interconnections live in edges, not body prose.

## Output

Return a reference to the task created or updated:

```markdown
- Captured [TASK-ID] - [TASK-TITLE] (under [PARENT-ID]: [PARENT-TITLE])
```
