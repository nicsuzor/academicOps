---
name: dump
description: Session exit and handover -- execute an immediate emergency handover when invoked by the user, or a calm routine wrap-up when invoked by the agent at session end (committing work, minting retroactive tasks, capturing durable facts, releasing tasks, and emitting a final report). Use when the user runs /dump, or when completing work, resetting context, or transitioning environments. Exclude for in-session updates (use /reconcile).
---

# /dump -- Session Exit and Handover

Determine invocation mode before acting:

- **User-run `/dump` (Emergency Handover)**: Triggered when the user invokes `/dump` (or `/crew:dump`) as a command, regardless of accompanying text. Stop all task execution immediately (no new reviews, dispatches, tests, or remaining steps); instruct active subagents to finish their immediate turn and return current state; cancel active timers and background tasks; then execute Steps 1-7 on work as it stands (releasing `partial`, or `done` only if all criteria were already verified).
- **Agent-run `/dump` (Routine Wrap-Up)**: Execute Steps 1-7 at session end (`/pull` completion, context reset, or environment transition).

## Procedure

### 1. Save and Push Work

Stage specific modified files (never `add -A`) and commit, noting partial state when incomplete. Push commits and open draft PRs (`gh pr create --draft` targeting the diverged base branch) only where `## Output` specifies. Persist non-git evaluation datasets and reports in the PKB (ephemeral scratch paths vanish on exit). Record branch and commit SHA.

### 2. Retroactive Tasks (Interactive Sessions Only)

When an interactive session edits repository files without an assigned task or recovers from a significant operational fault (outage, crashed daemon, credential failure, root-caused defect -- exempting routine health checks, status pings, and minor edits; file code bugs on GitHub issues), mint a retroactive task (`classification: chore|implementation`, parented to its project or operational epic, 5-section body: `Goal`, `Deliverable`, `Scope`, `Acceptance criteria`, `Pointers`) and release it `done` with SHA or health-check evidence. Isolated workers on assigned tasks never mint retroactive tasks: record containment breaches and release `partial` or `failed`.

### 3. Capture Durable Facts & Repair Contradictions

Offer settled durable facts (decisions, constraints, verified current-state findings, or KB corrections on a 6-month horizon; exclude exploratory thinking aloud) directly to the custodian (`pauli`) with source pointers, or record them under `## Durable Facts` on the task record and include them as sourced premises inside `### Handover Disposition` when isolated.

### 4. Release Claimed Tasks (Children First)

1. Refetch current task state (`pkb_get_task`), update `## Report` (leading with original ask/criteria and release outcome, with each deciding observation and its source), and call `pkb_release_task`:
   - `done`: Single completion status when all in-scope criteria have primary evidence in `## Report` and deliverables are delivered (draft PR opened with `pr_url`/`branch`, or PKB artifact recorded -- without waiting for CI, review, merge, or proof of user installation/deployment). Workers release `done` when in-session deliverables finish and any out-of-session work is queued as follow-up tasks.
   - `partial`: Worker's own criteria or in-session subtasks remain unfinished (blocker, scope seam, missing tool, pre-work approval boundary), or task includes an unreachable post-exit criterion (finish reachable work, leave that item unticked, cite in `reason`).
   - `failed`: Unrecoverable blocker or check failure.
   - `cancelled`: Obsolete or invalidated.
   - `in_progress`: Immediate active successor session continuing.
   - Never set or release `review` (human hold only).

```markdown
**Original Ask (`<task-id>/AC1`):** <Original acceptance criterion in full>

**Main Conclusion:** Task `<task-id>` (<title>) released as `<status>` on `<branch>` (`<commit-sha>`, `<pr-url or artifact>`), subject to <limitations or none>.

### Deliverables

1. <Deliverable: branch, commit SHA, PR URL, or persisted artifact>.
2. <Deciding command output, count, or test receipt>.
3. Rule compliance: <none observed, or explicit rule violation disclosure with rule citation>.
4. Limitations: <limitations or none>.

### Handover

1. Durable facts for custodian (`pauli`): <settled facts with primary pointers, or none>.
2. Next step: <pre-existing task-id pointer | 2-4 sentence resumption prompt | none>.
3. Daily-note project line (isolated workers only): `<project>: <10-20 word status/find> [-- Next: <pointer or prompt>]`.
```

Omit item 3 under `### Handover` when the daily note is updated directly.

### 5. Consolidated Daily Note Updates

For touched projects (modified repo files, updated tasks, or major operational/empirical finds): interactive and coordinator sessions write one consolidated bullet per project under `## Today's work`: `- **<project>**: <10-20 word status/find> -- Next: <pointer or prompt>` (omit `-- Next:` when complete). Isolated workers carry that line as an item under `### Handover` to avoid write contention.

### 6. Next-Step Determination

Never invent speculative follow-ups: list pre-existing dependent task pointers, coordinator-queued out-of-session follow-up IDs, a self-contained 2-4 sentence resumption prompt if `partial`/`in_progress`, or `None` if `done`.

### 7. Emit Final Handover Report

- **Agent-to-agent handovers (workers, subagents, container coordinators)**: Report task ID and release status (`done | partial | failed | cancelled | in_progress`), original ask and acceptance criteria with sourced primary evidence (branch, commit SHA, PR/artifact link, test/control receipts), limitations, durable facts, next step (`task-id` link | resumption prompt | none), isolated-worker daily-note line, and disclosed rule violations.
- **User-facing handover directly to the user**: Present a concise Markdown handover covering task, status, outputs, verified evidence, next step, durable facts, limitations, and any disclosed rule violations.
