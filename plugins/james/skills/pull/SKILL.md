---
name: pull
description: Claim and execute an already-scoped queued PKB task or single-skill task to completion, record verified results, and hand over via /james:dump. Use for fast-path execution of atomic leaf tasks. Exclude for multi-stage tasks or repo-scoped epics needing workflow composition and multi-agent fan-out (use /james:supervise).
---

# /pull -- Fast-Path Task Execution

Claim and execute an already-scoped queued PKB task or single-skill task to completion, record verified evidence under `## Report`, and invoke `/james:dump` to hand over.

## Procedure

### 1. Claim Task

- Claim the assigned task ID via `pkb_claim_task` (setting `assignee` to your agent or role). If omitted, locate the target task via PKB search.
- Operate strictly within the claimed task's boundaries: mutate only the claimed task's own fields and checklist, without creating speculative child or follow-up tasks on the graph.
- **Intake Contract**: Verify deliverables as an explicit `## Acceptance` checklist on the claimed PKB task before starting work. Consult repo-local `.agents/rules/` if present in the target workspace (optional across external repositories).
- Reserve `/james:pull` for focused leaf tasks; multi-stage work, broad coordination, workflow assembly via `james:workflow-library`, or multi-agent fan-out executes via `/james:supervise`.

### 2. Execute Work

- Execute task requirements directly to produce stated deliverables, surfacing upstream failures loudly without hidden workarounds.
- **Full-context file inspection**: Read each target repository file in full before modifying it to understand surrounding conventions and helper abstractions; avoid isolated narrow line-slice reads without prior whole-file context.

### 3. Consolidate Findings

- Write the handback proof `/james:dump` records under `## Report`: a parser-valid `james:premise-check` `argdown` block answering the task's ask IDs with primary empirical observations and inline source locators.

### 4. Validate Against Criteria

- Tick acceptance items strictly against primary evidence (`file:line` citations, quoted command output, counts, or specimen runs). Any unverified item stays unticked with its limit stated.
- Release `done` via `/james:dump` only when every `<task id>/AC<n>` is answered by concrete evidence in `## Report`; if any acceptance item lacks verified evidence, release `partial` naming missing evidence or blockers in `reason`.
- If the deliverable is a PR, open it as a draft (`gh pr create --draft`), record `pr_url` and branch, and exit `done` without waiting for external CI, review, or merge unless an explicit in-session check is part of acceptance. Reserve `partial` strictly for unfinished in-scope acceptance items; never release `review`.
- If a check (e.g. QA or review) fails, release `failed` documenting failure evidence and root cause rather than minting speculative follow-up tasks.
- Deliver work where Output specifies; persist non-git reports or evaluation datasets in the PKB with durable pointers rather than leaving them only in ephemeral scratch directories.

### 5. Handover

Invoke `/james:dump` at the end of every job regardless of release status (`done`, `partial`, `failed`, `cancelled`, or `in_progress`) so `## Report` and the session handover report are recorded.
