---
name: pull
description: Claim a queued PKB task, execute it to completion with subagents, record verified results, and hand over via /dump.
---

# Pull

Claim and execute a queued PKB task, directing subagents to deliver against stated acceptance criteria, then invoke `/dump` to log results and hand over.

## Procedure

### 1. Claim Task

- Call `pkb` tool `claim_task` (the `services` MCP server's PKB tool, invoked via its code-mode interface: `listToolFiles` → `readToolFile("servers/pkb.pyi")` → `executeToolCode` running `pkb.claim_task(id=...)`) with your assigned task ID. If missing, locate it via `pkb.search`.
- Authority extends strictly to the claimed task and its descendants. If blocked by external dependencies, complete what is possible and release remaining work.

### 2. Execute and Supervise

- Coordinate subagents in parallel to execute task requirements.
- Break work into sequenced steps, managing failures upstream without applying hidden workarounds.

### 3. Consolidate Findings

- Itemize load-bearing claims in a report argument, written per the `premise-check` skill.

### 4. Validate Against Criteria

- Verify deliverables against literal acceptance criteria using primary evidence and pinpoint citations. An item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated.
- Mark the task `done` via `/dump` only when its `## Report` section records concrete evidence demonstrating delivery against each acceptance item: quoted output, `file:line` citations, counts, and the specimen run where the task asks for one. Asserting that tests ran or that work was done without concrete evidence in the report is insufficient; if any acceptance item lacks evidence in the Report, release as `partial` naming the missing evidence.
- Release as `done` or `partial` by default. A worker whose deliverable is a PR releases `review` once the PR is open, with `pr_url` on the record, and exits without waiting for CI, review or merge: the repository merges it, and `/reconcile` writes `done` on the merge, which unblocks the follow-ups. `partial` is only for the worker's own unfinished acceptance items. Never send a complete deliverable to `partial` because of a dependent follow-up.
- If the worker's own deliverable is incomplete -- an external blocker, a missing tool, or a scope seam -- release as `partial` with a follow-up task carrying the remainder, and wire a `needs` edge from the follow-up task to any blocker (FR:334).
- Apart from an open PR awaiting merge, `review` means a worker needs help to finish the task. It is transient, never a waiting state for decisions. Release as `review` only when the worker cannot finish without help from a higher level, recording what help is needed on the record in `reason`. A worker hands back on the record and never addresses or escalates to the user. Any reconcile pass reading a `review` task transitions it immediately.

### 5. Handover

Invoke `/dump` at the end of every job, whatever its release status (`done`, `partial`, `review`, `failed`, `cancelled`, or `in_progress`). `/dump` is mandatory for the final handover and for logging results at the end of every job, because exiting or releasing directly omits the task-body proof and session handover report.
