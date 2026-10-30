---
name: pull
description: Claim a queued PKB task, execute it to completion with subagents, record verified results, and hand over via /dump.
---

# Pull

Claim and execute a queued PKB task, directing subagents to deliver against stated acceptance criteria, then invoke `/dump` to log results and hand over.

## Procedure

### 1. Claim Task

- Claim your assigned task ID via PKB task claiming tools (`pkb_claim_task`, setting `assignee` to your agent or role). If missing, locate it via PKB search.
- Authority extends strictly to the claimed task and its descendants. If blocked by external dependencies, complete what is possible and release remaining work.
- **Intake Contract:** On receiving a direction or work brief, the receiving agent must record its own summary stating deliverables as a frozen `## Acceptance` checklist on a PKB task before work starts.

### 2. Execute and Supervise

- Coordinate subagents in parallel to execute task requirements.
- Break work into sequenced steps, managing failures upstream without applying hidden workarounds.
- **Full-context file inspection**: Before modifying any repository file, the worker must read the entire target file in full to understand surrounding architecture, conventions, and helper abstractions. Keyhole line-slice reads (`read_file` with narrow line windows around advisory line hints) in isolation without prior whole-file context are strictly prohibited; line numbers are advisory starting pointers only. If a target file exceeds tool page limits, inspect the complete file via sequential discovery before editing.

### 3. Consolidate Findings

- Write the handback proof `/dump` records under `## Report`: the `premise-check` `argdown` block, asked by the task's frozen ask ids, with the basis of every load-bearing premise.

### 4. Validate Against Criteria

- Verify deliverables against literal acceptance criteria using primary evidence and pinpoint citations. An item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated.
- Mark the task `done` via `/dump` only when its `## Report` argument answers each `<task id>/AC<n>` from concrete evidence: quoted output, `file:line` citations, counts, and the specimen run where the task asks for one. Asserting that tests ran or that work was done without concrete evidence in the report is insufficient; if any acceptance item lacks evidence in the Report, release as `partial` naming the missing evidence.
- Release as `done` or `partial` by default. A worker whose deliverable is a PR releases `done` once the PR is open, with `pr_url` and branch recorded on the record, and exits without waiting for CI, review or merge: releasing `done` immediately unblocks dependent QA and review follow-up tasks on the graph. `partial` is reserved strictly for the worker's own unfinished acceptance items. Never release as `review` or send a complete deliverable to `partial` because of a dependent check or follow-up.
- If the worker's own deliverable is incomplete -- an external blocker, a missing tool, or a scope seam -- release as `partial` naming unfinished items or missing evidence in `reason`. Workers never create or name follow-up tasks, and reports carry no 'Next task' pointer; the reconcile pass notes partial and failed tasks and decides next actions from the parent epic.
- A worker whose check fails (e.g. QA or review) releases its task as `failed` documenting failure evidence and root cause. Never file fix tasks or follow-up tasks; the reconcile pass notes failed tasks and decides next actions from the parent epic.
- Deliver work where Output names: if Output says nothing is pushed or names only a PKB task or note, do not push. Ephemeral container and session scratch paths (`<appDataDir>/brain/`, `/tmp/`, unpushed container working trees) vanish on exit; non-git evaluation datasets, specimen tables, and reports must be persisted in the PKB with durable pointers rather than stored in ephemeral directories.
- Never release as `review`. If a worker's own deliverable is incomplete due to an external blocker, missing tool, or scope seam, release as `partial` naming unfinished items and missing evidence in `reason`. When an approval boundary or decision point is reached, file the complete artifact on the record and release as `partial` documenting what decision is needed; never release as `review`.

### 5. Handover

Invoke `/dump` at the end of every job, whatever its release status (`done`, `partial`, `failed`, `cancelled`, or `in_progress`). `/dump` is mandatory for the final handover and for logging results at the end of every job, because exiting or releasing directly omits the `## Report` argument and session handover report.
