---
name: pull
description: Claim a queued PKB task, execute it to completion with subagents, record verified results, and hand over via /dump.
---

# Pull

Claim and execute a queued PKB task, directing subagents to deliver against stated acceptance criteria, then invoke `/dump` to log results and hand over.

## Procedure

### 1. Claim Task

- Call `pkb_claim_task` via the `services` MCP server's code-mode execution tool (`portal_codemode_execute` running `async () => await codemode.pkb_claim_task({ id: "<task_id>", assignee: "<agent-or-role>" })`; in agy call `call_mcp_tool` with `ServerName: "services"`, `ToolName: "portal_codemode_execute"`, and in Claude Code call `mcp__services__portal_codemode_execute`) with your assigned task ID. If missing, locate it via `codemode.pkb_search({ query: "..." })`. If schema discovery is needed, `portal_codemode_search` exposes `async () => await codemode.tools()`.
- Authority extends strictly to the claimed task and its descendants. If blocked by external dependencies, complete what is possible and release remaining work.
- **Intake Contract:** On receiving a direction or work brief, the receiving agent must record its own summary stating deliverables as a frozen `## Acceptance` checklist on a PKB task before work starts.

### 2. Execute and Supervise

- Coordinate subagents in parallel to execute task requirements.
- Break work into sequenced steps, managing failures upstream without applying hidden workarounds.

### 3. Consolidate Findings

- Write the handback proof `/dump` records under `## Report`: the `premise-check` `argdown` block, asked by the task's frozen ask ids, with the basis of every load-bearing premise.

### 4. Validate Against Criteria

- Verify deliverables against literal acceptance criteria using primary evidence and pinpoint citations. An item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated.
- Mark the task `done` via `/dump` only when its `## Report` argument answers each `<task id>/AC<n>` from concrete evidence: quoted output, `file:line` citations, counts, and the specimen run where the task asks for one. Asserting that tests ran or that work was done without concrete evidence in the report is insufficient; if any acceptance item lacks evidence in the Report, release as `partial` naming the missing evidence.
- Release as `done` or `partial` by default. A worker whose deliverable is a PR releases `review` once the PR is open, with `pr_url` on the record, and exits without waiting for CI, review or merge: the repository merges it, and `/reconcile` writes `done` on the merge, which unblocks dependent work. `partial` is only for the worker's own unfinished acceptance items. Never send a complete deliverable to `partial` because of a dependent check or follow-up.
- If the worker's own deliverable is incomplete -- an external blocker, a missing tool, or a scope seam -- release as `partial` naming unfinished items or missing evidence in `reason`. Workers never create or name follow-up tasks, and reports carry no 'Next task' pointer; the reconcile pass notes partial and failed tasks and decides next actions from the parent epic.
- A worker whose check fails (e.g. QA or review) releases its task as `failed` documenting failure evidence and root cause. Never file fix tasks or follow-up tasks; the reconcile pass notes failed tasks and decides next actions from the parent epic.
- Deliver work where Output names: if Output says nothing is pushed or names only a PKB task or note, do not push. Ephemeral container and session scratch paths (`<appDataDir>/brain/`, `/tmp/`, unpushed container working trees) vanish on exit; non-git evaluation datasets, specimen tables, and reports must be persisted in the PKB with durable pointers rather than stored in ephemeral directories.
- Apart from an open PR awaiting merge, `review` means a worker needs help to finish the task. It is transient, never a waiting state for decisions. Release as `review` only when the worker cannot finish without help from a higher level, recording what help is needed on the record in `reason`. A worker hands back on the record and never addresses or escalates to the user. Any reconcile pass reading a `review` task transitions it immediately.

### 5. Handover

Invoke `/dump` at the end of every job, whatever its release status (`done`, `partial`, `review`, `failed`, `cancelled`, or `in_progress`). `/dump` is mandatory for the final handover and for logging results at the end of every job, because exiting or releasing directly omits the `## Report` argument and session handover report.
