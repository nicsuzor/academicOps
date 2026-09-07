---
name: pull
description: Claim a queued PKB task, execute it to completion with subagents, record verified results, and hand over.
---

# Pull

Claim and execute a queued PKB task, directing subagents to deliver against stated acceptance criteria.

## Procedure

### 1. Claim Task

- Call `pkb__claim_task` with your assigned task ID. If missing, locate it via `pkb__task_search`.
- Authority extends strictly to the claimed task and its descendants. If blocked by external dependencies, complete what is possible and release remaining work.

### 2. Hydrate Context

Invoke `pauli` with the `hydrate` skill to retrieve current strategic context, project rules, and background documentation.

### 3. Execute and Supervise

- Coordinate subagents in parallel to execute task requirements.
- Break work into sequenced steps, managing failures upstream without applying hidden workarounds.

### 4. Consolidate Findings

- Synthesize results once execution finishes; avoid intermediate status noise.
- Itemize load-bearing claims, tagging each with its explicit basis (`[observed]`, `[attempted-and-failed]`, `[exhaustively-searched]`, `[inferred]`, `[assumed]`).
- Negative and capability assertions require a failed command execution or stated search boundary.

### 5. Validate Against Criteria

- Verify deliverables against literal acceptance criteria using primary evidence and pinpoint citations.
- If incomplete due to external blockers, release as `review` (with required `reason`) or `partial`. Wire directed `blocks` edges instead of setting `status: blocked`.

### 6. Handover

Invoke `/dump` to commit changes, release tasks, and emit the final handover report.
