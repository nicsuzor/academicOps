---
name: q
type: command
description: Capture natural-language asks and situate them on the task graph as repo-scoped tasks under governing component or initiative parents, wire value-chain links on Strategic Value Carriers, and consolidate similar work. Use for strategic intake, task capture, and situating new asks. Exclude for starting workers on queued tasks (use /dispatch) or decomposing abstract objectives (use /decompose).
allowed-tools: [Skill, mcp__services__*]
---

# /q -- Strategic Intake & Graph Placement

Situate natural-language asks on the task graph: parented, connected, and valued at intake. Use the task pipeline for any durable deliverable (workflows, instructions, specifications, code); capture plans, designs, and decisions on the graph rather than as plan files in repositories. Answer in-turn questions and lookups directly without queueing tasks.

## 1. Search, Hydrate, and Consolidate

1. **Custodian intake**: The PKB custodian (`pauli`) executes `/q` intake and related-work lookup via `/hydrate`. Non-custodian callers delegate `/q` on Turn 1 with only the verbatim ask and source identifiers, running zero pre-delegation lookups or bundled sweep work.
2. **Search via hydrate**: Search open and closed tasks (`include_done: true`) plus related targets via `/hydrate` before minting any task.
3. **Evaluate outcome**:
   - _Consolidate or resume_: Extend an open or in-progress task covering the topic or repository scope rather than creating a duplicate.
   - _Reopen or close_: Reopen a closed task needing follow-up (`queued` or `ready`). If the deliverable already shipped and the user is informed, mark tracking and work tasks `done` rather than holding them open to verify user installation or deployment.
   - _Mint a new task_: Create a task (`type: "task"`, never `type: "epic"`) parented under its governing enduring component parent (`status: "ready"`, weighted via `serves` to `type: target`) or multi-session initiative (`parent: <parent_id>`) with zero `serves` edges on the child. If an architectural subsystem lacks a component parent, create and weight it first; parent minor isolated tweaks under the project's general infrastructure parent with zero leaf `serves` edges. Do groundwork first (PKB, then live repository host and traces), set `status: "queued"` for ready agent work, reserve `ready`/`inbox` for held or blocked items, and set `status: "review"` (`assignee: "user"`) only after groundwork and a reasoned recommendation are recorded and progress genuinely waits on the user's decision.
4. **Closed-loop delivery**: When a conversational ask needs results reported back on channel, add a dependent delivery task (`assignee: ida`, `needs: [<repo-task-id>]`, zero `serves` edges). Executor responsibility ends once shipped and reported.

## 2. Multi-Repository Scoping

When an ask spans multiple repositories, create strictly one repo-scoped task (`type: "task"`, `project` set per repo) under the shared governing parent (`parent: <parent_id>`) with zero leaf `serves` edges, sequencing repos via `needs`. One task per repository governs isolated container execution (`/supervise`), while strategic valuation (`serves`) stays exclusively on the shared parent.

## 3. Value-Chain Links & Metadata

- **Affordable loss**: Flag commitments whose prospective downside violates affordable loss as a priority ask for the user rather than admitting them.
- **Three-Purpose Taxonomy**:
  - `serves`: Points strictly to priced `type: target` nodes (never task-to-task), authored exclusively on Strategic Value Carriers (enduring component parents, multi-session initiatives, or freestanding major external deliverables) at full holistic weight (`quantum`, `probability`, `effect: helps|harms`, `justification`, `set_by: agent-proposed`). Child tasks carry zero `serves` edges and inherit worth via `parent` or `needs`.
  - `needs`: Boolean execution dependency from dependent to prerequisite (no `quantum` or `probability`).
  - Body wikilinks: Record contextual citations and pointers exclusively as markdown wikilinks under `## Context` or `## Pointers` (never duplicate them as formal frontmatter edges).
- **Hubs, ideas, opportunities**: Link foundational capability investments directly to capital stock targets; leave bare ideas without invented links; tag unagreed offers as `classification: opportunity`.
- **Dates & effort**: Record dates as `due` with `deadline_class` (`fake` default, `soft` if accepted, `hard` if explicitly hard or published real-loss; never from urgency). Record `effort` when stated or known.
- **Groundwork & decisions**: Settle unknowns before filing. Keep competing options inside one scoping task or ADR until chosen, then reify only the chosen route under `parent: <task_id>` at `status: "queued"`. Model empirical unknowns as `classification: probe` tasks wired via `needs: [<probe_task_id>]`. Never write `intent`, `severity`, `stakeholder`, target worth, `set_by: user`, `supports`, `soft_depends_on`, `supersedes`, stored `alternative`/`settles` edges, or leaf `serves` edges.

## 4. Headless Intake (Email, Mobile Capture)

1. **Prepare sources**: Read full message/thread bodies, non-banner attachments, and reachable links (note unreachable access boundaries plainly; resolve voice homophones). Never mint user tasks to read, open, or check a source.
2. **Classify obligation**:
   - `noise` (automated notices, newsletters, CC copies): `delete`; create zero tasks.
   - `reference` / FYI: Update an existing blocking task or topic note (`update_body`); create zero user tasks.
   - `opportunity` / unagreed offer: Prepare one decision record (`status: "review"`, `assignee: "user"`, `classification: "opportunity"`, `deadline_class: "fake"` unless accepted) with summary, bold options inside the single body (`[Recommended]` rationale, draft reply, decline option).
   - `action` / accepted commitment: Queue agent groundwork (`queued`) or prepared draft.
3. **Route captures**: Fold duplicates into existing tasks (`update_body` then `delete`), convert in place via `convert_document(id=<capture-id>, type="task", status="ready"|"inbox")` then `update_task`/`update_body`, synthesize into a canonical note (`update_body` or `create(type="knowledge")`) before deleting, or `delete` discards. Leave uncertain captures untouched for interactive review.

## 5. Task Body & Output

- **Title**: Concise verb-led imperative (e.g., `Implement X`).
- **Body**: Restate terse asks faithfully by meaning and distinctions; preserve exact user words with message IDs only in `## Ask` as the immutable referent; leave unresolved ambiguity open. Bound `Goal`, `Acceptance`, and deliverables strictly to outcomes the assigned worker delivers and checks before releasing `done`, excluding external post-exit acts (independent review, CI, PR merge, host deployment, user approval) unless that stage is the task's authorized scope.
- **Output**: `- Captured [TASK-ID] - [TASK-TITLE] (under [PARENT-ID]: [PARENT-TITLE])`
