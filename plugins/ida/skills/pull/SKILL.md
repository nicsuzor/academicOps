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

- Verify deliverables against literal acceptance criteria using primary evidence and pinpoint citations.
- When acceptance criteria are met, mark the task `done` via `/dump` (workers with PKB access mark `done` after `/pull`; asserting that tests ran is sufficient for a completion claim).
- If the next step is a decision only Nic can make, release as `review`, naming that decision in the required `reason`.
- If agent work remains -- an external blocker, a missing tool, or a scope seam -- release as `partial` with a follow-up task carrying the remainder, and wire directed `blocks` edges from any blocker.

### 5. Handover

Invoke `/dump` to commit changes, release tasks, and emit the final handover report.
