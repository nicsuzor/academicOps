---
name: pull
description: Claim and execute an already-decomposed queued PKB task or single-skill task to completion without re-reifying, record verified results, and hand over via /dump. Use for fast-path worker execution of leaf tasks. Exclude for repo-scoped epic tasks needing workflow composition and multi-agent fan-out (use /supervise).
---

# /pull -- Fast-Path Task Execution

Claim and execute an already-decomposed queued PKB task or single-skill task to completion without re-reifying, record verified evidence under `## Report`, and invoke `/dump` to hand over. Dispatched leaf workers operate strictly under the worker state-only invariant.

## Procedure

### 1. Claim Task

- Claim the assigned task ID via PKB task claiming tools (`pkb_claim_task`, setting `assignee` to your agent or role). If missing, locate it via PKB search.
- Authority extends strictly to the claimed task. Plain leaf workers operate strictly state-only: mutate only the claimed task's own fields and checklist. Never reify workflows, create child tasks, or mint follow-up tasks on the graph.
- **Intake Contract**: When claiming a task, verify deliverables as a frozen `## Acceptance` checklist on the claimed PKB task before work starts. Internal lookups and fast-path execution workflows never create additional tasks on the graph.
- Coordinator sessions use `/pull` strictly for lightweight documentation, synthesis, or coordination tasks running no test suites or large codebase greps; substantive implementation, codebase sweeps, and test execution tasks must be dispatched to polecats via `/dispatch`.

### 2. Execute Work

- Execute task requirements directly to deliver stated deliverables.
- Break work into sequenced in-session steps, managing failures upstream without applying hidden workarounds.
- **Full-context file inspection**: Before modifying any repository file, the worker must read the entire target file in full to understand surrounding architecture, conventions, and helper abstractions. Keyhole line-slice reads (`read_file` with narrow line windows around advisory line hints) in isolation without prior whole-file context are strictly prohibited; line numbers are advisory starting pointers only. If a target file exceeds tool page limits, inspect the complete file via sequential discovery before editing.

### 3. Consolidate Findings

- Write the handback proof `/dump` records under `## Report`: the `premise-check` `argdown` block, asked by the task's frozen ask IDs, with the basis of every load-bearing premise.

### 4. Validate Against Criteria

- Verify deliverables against literal acceptance criteria using primary evidence and pinpoint citations. An item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated.
- Mark the task `done` via `/dump` only when its `## Report` argument answers each `<task id>/AC<n>` from concrete evidence: quoted output, `file:line` citations, counts, and the specimen run where the task asks for one. Asserting that tests ran or that work was done without concrete evidence in the report is insufficient; if any acceptance item lacks evidence in the Report, release as `partial` naming the missing evidence.
- Release as `done` or `partial` by default. A worker whose deliverable is a PR marks any draft PR ready for review as soon as its code step completes without waiting for approval, releases `done` once the PR is open, with `pr_url` and branch recorded on the record, and exits without waiting for CI, review, or merge: releasing `done` immediately unblocks dependent QA and review follow-up tasks on the graph. `partial` is reserved strictly for the worker's own unfinished acceptance items. Never release as `review` or send a complete deliverable to `partial` because of a dependent check or follow-up.
- If the worker's own deliverable is incomplete -- an external blocker, a missing tool, or a scope seam -- release as `partial` naming unfinished items or missing evidence in `reason`. Plain leaf workers never create or name follow-up tasks, and reports carry no speculative 'Next task' pointer; truth maintenance (`/reconcile`) notes partial and failed tasks and decides next actions from the parent epic.
- A worker whose check fails (e.g. QA or review) releases its task as `failed` documenting failure evidence and root cause. Never file fix tasks or follow-up tasks; the reconcile pass notes failed tasks and decides next actions from the parent epic.
- Deliver work where Output names: if Output says nothing is pushed or names only a PKB task or note, do not push. Ephemeral container and session scratch paths (`<appDataDir>/brain/`, `/tmp/`, unpushed container working trees) vanish on exit; non-git evaluation datasets, specimen tables, and reports must be persisted in the PKB with durable pointers rather than stored in ephemeral directories.
- Never release as `review`. If a worker's own deliverable is incomplete due to an external blocker, missing tool, or scope seam, release as `partial` naming unfinished items and missing evidence in `reason`. When an approval boundary or decision point is reached, file the complete artifact on the record and release as `partial` documenting what decision is needed; never release as `review`.

### 5. Handover

Invoke `/dump` at the end of every job, whatever its release status (`done`, `partial`, `failed`, `cancelled`, or `in_progress`). `/dump` is mandatory for final handover and logging results, because exiting or releasing directly omits the `## Report` argument and session handover report.
