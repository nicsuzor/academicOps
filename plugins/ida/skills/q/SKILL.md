---
name: q
type: command
description: Stage 1 Intake & Capture--place an ask or idea on the graph under the right parent, wire what it serves, propose values, and record strategic placement at intake. Exclude for starting workers on ready tasks (use /dispatch) or decomposing objectives (use /decompose).
allowed-tools: [Skill, AskUserQuestion, mcp__services__*]
---

# /q -- Strategic Intake & Graph Placement

Capture natural-language asks and situate them on the strategic graph: parented, connected, and valued at intake per `specs/workflows/graph-valuation.md`. The task dispatch pipeline is used for any durable deliverable -- including agent workflows, instruction updates, specifications, and code changes. Plans, designs, and decisions are captured directly on the task graph, never as markdown plan files in target repositories. Questions and lookups that can be answered in-turn are answered directly without queueing tasks.

## Placement and Valuation

1. **Search before creating**: Search the PKB for related targets and open work the input could serve. Reuse an existing node where one matches.
2. **Consolidate and place**: Consolidate where possible (merge duplicates, reparent related tasks). Place the node under an active parent container (or `part_of` edge).
3. **Affordable loss check**: Evaluate affordable loss before admitting commitments. If prospective downside or commitment cost violates affordable loss, flag as a priority ask for the user rather than admitting to the flow. Flow maths remains unpolluted by subjective risk gating.
4. **Wire what it serves under the Three-Purpose Taxonomy (ADR-0002)**: Add edges strictly per purpose, pushing weight links as far up the parent hierarchy as accurate:
   - **Weight Flow (`serves`, `supports`)**:
     - `serves`: Wire from top-level deliverable tasks to priced `target` nodes. Subtasks inherit value via parent induction and must not duplicate `serves` edges.
     - `supports`: Wire only when executing the task directly reduces effort/risk or increases the completion probability of an upstream task/target. Tracking/coordination tasks do NOT support tracked tasks; tracking tasks serve user understanding targets.
     - **Weight fields**: `quantum` (words `all`..`none` or float $0.0..=1.0$), `probability` (words `certain`..`impossible` or float $0.0..=1.0$, default 1.00), `effect: helps` | `harms`, `justification`, `set_by: agent-proposed`.
   - **Work Sequencing (`needs`)**:
     - Wire from dependent to prerequisite task ($B \to A$).
     - Boolean execution gate; carries **neither** quantum nor probability.
   - **Structural Clustering (Body wikilinks)**:
     - Contextual references and cited artifacts live exclusively as markdown `[[wikilinks]]` in the body (`## Context`, `## Pointers`). Direct body references already act as clustering/interconnection edges in graph physics; duplicate formal frontmatter edges are strictly prohibited.
5. **Capital stock hubs**: Wire foundational investments that expand future optionality (reputation, relationships, tool scaffolding, capital reserves) directly to capital stock targets rather than inventing speculative multi-hop downstream chains.
6. **A bare idea stays bare**: An idea with no clear link to anything priced gets its container and no other edge. Never invent a link to make it count.
7. **Opportunity is one node plus its edges**: Mark opportunities as `classification: opportunity`. Adding it changes no other node's fields.
8. **Dates**: Record any date as `due` with `deadline_class`:
   - `fake`: Default for captured dates where no real loss lands on it.
   - `soft`: Input carries the user's acceptance or sent mail agreeing to the date.
   - `hard`: The user explicitly states the date is hard, or a published real-loss date proposed `hard`.
     Never derive a date from urgency.
9. **Effort**: Record `effort` duration string when the input states it or work is a known kind (read by the cliff lane).
10. **Decisions and empirical probes**: A task that has options to choose between with no commitment to doing anything immediately beyond choosing keeps the choices and instructions inside the single task body. Competing options remain in the task body or ADR until chosen; when chosen, only the selected option is reified into an actionable task under `parent: <task_id>`. Empirical probes are active tasks (`classification: probe`) wired to the scoping task via standard `needs: [<probe_task_id>]`. Stored `alternative` and `settles` edges are prohibited.
11. **Do not write**: `intent`, `severity`, `stakeholder` as a weight, target worth, `set_by: user`, `soft_depends_on`, `supersedes`, stored `alternative` or `settles` edges, duplicate frontmatter edges for body citations, `supports` edges from tracking tasks to tracked tasks, or redundant child-to-ancestor `serves` edges.

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

**Other sections**: Never duplicate structured frontmatter edges in prose or vice versa. Contextual citations, background references, and related artifacts are recorded exclusively as markdown `[[wikilinks]]` in the body (under `## Context` or `## Pointers`), which naturally provide structural clustering for graph physics and search without duplicating formal frontmatter weight edges.

## Output

Return a reference to the task created or updated:

```markdown
- Captured [TASK-ID] - [TASK-TITLE] (under [PARENT-ID]: [PARENT-TITLE])
```
