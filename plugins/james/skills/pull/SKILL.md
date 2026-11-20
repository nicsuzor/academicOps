---
name: pull
description: Claim and execute an already-decomposed queued PKB task or single-skill task to completion without re-reifying, record verified results, and hand over via /dump. Use for fast-path worker execution of leaf tasks. Exclude for repo-scoped epic tasks needing workflow composition and multi-agent fan-out (use /supervise).
---

# /pull -- Fast-Path Task Execution

Claim and execute an already-decomposed queued PKB task or single-skill task to completion without re-reifying, record verified evidence under `## Report`, and invoke `/dump` to hand over. Dispatched leaf workers operate strictly under the worker state-only invariant.

## Procedure

### 1. Claim Task

- Claim the assigned task ID via PKB task claiming tools (`pkb_claim_task`, setting `assignee` to your agent or role). Locating an assigned task is strictly an exact lookup by known ID or title (`pkb_get_task`); pull workers never execute exploratory or broad semantic searches for related or open work. If the assigned task cannot be fetched directly, halt or query the custodian (`pauli`).
- Authority extends strictly to the claimed task. Plain leaf workers operate strictly state-only: mutate only the claimed task's own fields and checklist. Never reify workflows, create child tasks, or mint follow-up tasks on the graph.
- **Intake Contract**: When claiming a task, verify deliverables as a frozen `## Acceptance` checklist on the claimed PKB task before work starts. Internal lookups and fast-path execution workflows never create additional tasks on the graph.
- Coordinator sessions use `/pull` strictly for lightweight documentation, synthesis, or coordination tasks running no test suites or large codebase greps; substantive implementation, codebase sweeps, and test execution tasks must be dispatched to polecats via `/dispatch`.

### 2. Execute Work

- Execute task requirements directly to deliver stated deliverables.
- Break work into sequenced in-session steps, managing failures upstream without applying hidden workarounds.
- **Full-context file inspection**: Before modifying any repository file, the worker must read the entire target file in full to understand surrounding architecture, conventions, and helper abstractions. Keyhole line-slice reads (`read_file` with narrow line windows around advisory line hints) in isolation without prior whole-file context are strictly prohibited; line numbers are advisory starting pointers only. If a target file exceeds tool page limits, inspect the complete file via sequential discovery before editing.

### 3. Consolidate Findings

- Write the handback proof `/dump` records under `## Report`: the `premise-check` `argdown` block, asked by the task's frozen ask IDs, with the basis of every load-bearing premise.
- **Recognise and route settled durable facts**: Recognise any settled durable fact uncovered during task execution (a decision, an architectural constraint, a verified finding about current system state, or an incorrect knowledge base statement -- excluding exploratory user thinking aloud until settled or directed). Offer it to the knowledge base custodian (`pauli`) as content with its source pointer without mutating knowledge notes directly, or record it under `## Durable Facts` in the task record and handover summary when operating in an isolated or headless context where the custodian is unreachable.

### 4. Validate Against Criteria

- Verify deliverables against literal acceptance criteria using primary evidence and pinpoint citations (`file:line`, quoted output, counts, PR URL, or specimen run). An item is ticked (`[x]`) only with direct evidence of that item itself; any other item stays unticked (`[ ]`) with its limit stated.
- Package deliverables and determine task release status per the composed workflow's completion step:
  - **One completion release status (`done`)**: Mark the work task **`done`** via `/dump` when all in-scope acceptance criteria are met with concrete evidence in `## Report` answering each `<task id>/AC<n>`, and the deliverable is delivered where `Output` names (for a PR task: draft PR opened via `gh pr create --draft` with `pr_url` and `branch` recorded; for a non-PR task: durable PKB artifact pointer recorded, never ephemeral scratch paths). Exit without waiting for CI, review, merge, or proof that the user installed or deployed a shipped release; releasing `done` immediately unblocks any downstream review or dependent task on the graph.
  - **Incomplete work (`partial`)**: Reserve `partial` strictly for when the worker's own acceptance items remain unfinished (external blocker, missing tool, scope seam, missing evidence in `## Report`, or a pre-work approval boundary where the complete artifact is filed on the record awaiting a decision). Never release a completed deliverable as `partial` because of a downstream check or merge, unless the claimed task's own checklist includes an unreachable post-exit criterion (such as external review, merge, or deployment) -- in that case, finish all reachable work, leave that item unticked, and release `partial` citing the unreachable criterion in `reason`.
  - **Check failure (`failed`)**: A worker whose check fails (such as an independent review or QA task) releases its task as `failed` documenting failure evidence and root cause.
  - **Prohibited status (`review`) and state-only discipline**: Never release any task as `review`. Plain leaf workers never create or name follow-up tasks, and reports carry no speculative 'Next task' pointer; `/reconcile` notes partial and failed tasks and decides next actions from the parent epic.

### 5. Handover

Invoke `/dump` at the end of every job, whatever its release status (`done`, `partial`, `failed`, `cancelled`, or `in_progress`). `/dump` is mandatory for final handover and logging results, because exiting or releasing directly omits the `## Report` argument and session handover report.
