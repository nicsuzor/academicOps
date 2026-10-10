---
name: pull
description: Claim a queued PKB task, execute it to completion with subagents, record verified results, and hand over.
---

# Pull

Claim and execute a queued PKB task, directing subagents to deliver against stated acceptance criteria.

## Procedure

### 1. Claim Task

- Call `pkb` tool `claim_task` (the `services` MCP server's PKB tool, invoked via its code-mode interface: `listToolFiles` → `readToolFile("servers/pkb.pyi")` → `executeToolCode` running `pkb.claim_task(id=...)`) with your assigned task ID. If missing, locate it via `pkb.search`.
- Authority extends strictly to the claimed task and its descendants. If blocked by external dependencies, complete what is possible and release remaining work.

### 2. Execute and Supervise

- Coordinate subagents in parallel to execute task requirements.
- Break work into sequenced steps, managing failures upstream without applying hidden workarounds.

### 3. Consolidate Findings

- Itemize load-bearing claims in a claim ledger, written per the `claim-ledger` skill.
- Negative and capability assertions require a failed command execution or stated search boundary.

### 4. Validate Against Criteria

- Verify deliverables against literal acceptance criteria using primary evidence and pinpoint citations. An item is ticked only with evidence of that item itself; any other item stays unticked with its limit stated.
- When acceptance criteria are met, mark the task `done` via `/dump` (workers with PKB access mark `done` after `/pull`; asserting that tests ran is sufficient for a completion claim).
- Release as `done` or `partial` by default. `review` is the exception.
- If agent work remains -- an external blocker, a missing tool, a scope seam, or a next step such as a QA run or re-run, a merge, a deploy, a retry, or a routing or dispatch call -- release as `partial` with a follow-up task carrying the remainder, and wire directed `blocks` edges from any blocker.
- Release as `review` only when the next step is a decision only Nic can make: a choice that turns on Nic's priorities, preferences or authority, such as approving a spec or picking between options only Nic can own. Name that decision in the required `reason` as a question for Nic. If the `reason` names an action an agent could take, the release is `partial`, not `review`.

### 5. Handover

Invoke `/dump` to commit changes, release tasks, and emit the final handover report.
