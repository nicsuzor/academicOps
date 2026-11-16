---
name: q
type: command
description: Capture natural-language asks and situate them on the graph as repo-scoped tasks under governing component or initiative epics, wire value-chain links on Strategic Value Carriers, and consolidate similar work. Use for strategic intake, task capture, and situating new asks under governing epics. Exclude for starting containers on queued tasks (use /dispatch) or decomposing abstract objectives (use /decompose).
allowed-tools: [Skill, AskUserQuestion, mcp__services__*]
---

# /q -- Strategic Intake & Graph Placement

Capture natural-language asks and situate them on the strategic graph: parented, connected, and valued at intake per `specs/workflows/graph-valuation.md`. The task dispatch pipeline is used for any durable deliverable -- including agent workflows, instruction updates, specifications, and code changes. Plans, designs, and decisions are captured directly on the task graph, never as markdown plan files in target repositories. Questions and lookups that can be answered in-turn are answered directly without queueing tasks.

## Placement and Valuation

1. **Search and consolidate (mandatory across all invocations)**: Non-custodian callers delegate `/q` on Turn 1 as a single-purpose brief carrying only the verbatim ask and source identifiers -- running zero pre-delegation PKB, GitHub, or trace lookups in the parent context and never bundling `/q` with concurrent session or sweep work -- because the custodian (`pauli`) performs all intake groundwork in an isolated context. When searching for related or overlapping work, distill the input into 1-3 short (5-15 word) conceptual queries per topic facet (stripping conversational framing and negative or incidental IDs, never passing the raw verbatim prompt to `pkb_search`), and search both open and closed tasks in the PKB (`include_done: true`) as well as related targets before minting any task. Aggregating similar tasks is explicitly preferred: if an incoming ask (or its per-repo parts) can be distributed across one or more existing open epic-sized tasks and handled as the same chunk of work, fold and update those existing tasks rather than creating new tasks. Evaluate three outcomes:
   - _Consolidate or resume an open task_: If an existing open or in-progress task covers the topic or repo scope, extend and update that task instead of creating a new one.
   - _Reopen a closed task_: If a completed or closed task directly addresses the topic and requires follow-up, iteration, or expansion, reopen the closed task (setting `status: "queued"` or `"ready"`) to preserve continuity; if the deliverable or release has already shipped and the user is informed, close (`done`) the tracking and work tasks rather than holding them open to verify user-side installation or deployment.
   - _Mint a new task_: Only if no matching open or closed task can absorb the ask, create a new task situated under its governing enduring component epic or multi-session initiative epic (`parent: <epic_id>`) with zero `serves` edges on the child task. If the ask belongs to a major architectural subsystem that lacks an enduring component epic, mint and weight the enduring component epic at architectural subsystem altitude first (`status: "ready"`, wired via `serves` to `type: target` nodes) and parent the task under it; minor isolated script or utility tweaks without a dedicated subsystem epic parent under the project's general infrastructure or root epic with zero leaf `serves` edges (never spawning single-script micro-epics). Perform groundwork first (settling unknowns from the PKB first, then live GitHub and traces) and set `status: "queued"` for the concrete next agent step so ready work dispatches rather than sitting in `inbox`; reserve `"ready"`/`"inbox"` strictly for held or externally blocked items, and set `status: "review"` (`assignee: "user"`) when agent groundwork and a reasoned recommendation are complete on the record and the item genuinely waits on the user's own decision.
   - **Closed-loop delivery**: When a conversational ask requires reporting results back to the user on channel, create a closed-loop delivery task (`assignee: ida`, `needs: [<repo-task-id>]`) under the governing epic with zero `serves` edges so conversational reporting triggers automatically after container execution completes.
2. **Multi-repository scoping (execution vs. valuation)**: When an incoming ask spans two or more repositories, create related repo-specific tasks (`type: "task"`, `project` set per repo; never pass `type: "epic"`):
   - Place each repo task under the shared governing component or initiative epic (`parent: <epic_id>`) with zero leaf `serves` edges, linking sequential repo tasks via `needs`.
   - Create strictly one repo-scoped task per repository, never splitting further at intake. One-task-per-repo governs container execution isolation (`/supervise`), whereas strategic valuation (`serves`) stays exclusively on the shared component or initiative epic.
3. **Affordable loss check**: Evaluate affordable loss before admitting commitments. If prospective downside or commitment cost violates affordable loss, flag as a priority ask for the user rather than admitting to the flow. Flow maths remains unpolluted by subjective risk gating.
4. **Wire value-chain links under the Three-Purpose Taxonomy (ADR-0002)**: Add edges strictly per purpose, enforcing the Component-Weighting & Leaf-Inheritance Rule (Single Injection Invariant):
   - **Weight Flow (`serves`)**:
     - `serves`: Points **strictly to a priced `type: target` node** (`to: <target_id>`), never task-to-epic. Authored **exclusively** on **Strategic Value Carriers**: (1) enduring component/subsystem epics (`status: "ready"`), (2) multi-session initiative epics, or (3) standalone major deliverables (freestanding commitments to external stakeholders belonging to no component or initiative epic).
     - **Zero leaf `serves` edges & holistic epic pricing**: Small fixes, bugfixes, feature slices, refactors, config tweaks, QA/review tasks, and repo-scoped tasks under a component or initiative epic carry **zero `serves` edges** and inherit worth via `parent` (or `needs`). At most one node along any `parent` chain wires `serves` to a given target. Epics are always priced at their full holistic component/initiative weight, never as a remainder after child tasks.
     - **Weight fields**: `quantum` (words `all`..`none` or float 0.0..=1.0), `probability` (words `certain`..`impossible` or float 0.0..=1.0, default 1.00), `effect: helps` | `harms`, `justification`, `set_by: agent-proposed`.
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
10. **Decisions and empirical probes**: An agent given a task or high-value prompt does the groundwork first (settling unknowns from the PKB first, then live GitHub and traces) and makes architectural or route decisions itself rather than leaving actionable work in `inbox`. A task that has options to choose between with no commitment to doing anything immediately beyond choosing keeps the choices and instructions inside the single task body. Competing options remain in the task body or ADR until chosen; when chosen, only the selected option is reified into an actionable task under `parent: <task_id>` at `status: "queued"`. Only when agent groundwork and option evaluation are complete (with a reasoned recommendation written in the body) and the choice genuinely waits on the user's own decision or host action is the task set to `status: "review"` (`assignee: "user"`) so it surfaces in the daily note's `## With you`. Empirical probes are active tasks (`classification: probe`) wired to the scoping task via standard `needs: [<probe_task_id>]`. Stored `alternative` and `settles` edges are prohibited.
11. **Do not write**: `intent`, `severity`, `stakeholder` as a weight, target worth, `set_by: user`, `supports`, `soft_depends_on`, `supersedes`, stored `alternative` or `settles` edges, duplicate frontmatter edges for body citations, task-to-epic `serves` edges, or leaf `serves` edges on child tasks under component or initiative epics.

## Headless Context (Email, Mobile Capture)

When invoked headlessly (e.g. correspondence sweep or `notes/mobile-captures/` intake):

1. **Read for homophones**: Treat voice-dictated captures as phonetic transcripts; resolve homophones in context before judging meaning or ambiguity.
2. **Classify and route each capture**:
   - **Task** (or **Expand** probe): If an existing task already carries the ask (verified in Step 1 via distilled conceptual query search through the custodian), fold the capture into that task (`update_body`) and `delete` the capture after the write succeeds. Otherwise, convert the capture into a task in place via `convert_document(id=<capture-id>, type="task", status="ready"|"inbox")` so the same file and ID move out of `notes/mobile-captures/` into `tasks/` with task frontmatter, then set the verb-led imperative `title`, `parent`, `project`, `classification` (`probe` for Expand), `links`, and task body via `update_task` and `update_body`. Do not create a replacement task or edit PKB files on disk to simulate conversion.
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
