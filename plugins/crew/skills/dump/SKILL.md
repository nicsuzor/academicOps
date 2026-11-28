---
name: dump
description: Session exit and handover -- execute an immediate emergency handover when invoked by the user, or a calm routine wrap-up when invoked by the agent at session end (committing work, minting retroactive tasks, capturing durable facts, releasing tasks, and emitting a final report). Use when the user runs /dump, or when completing work, resetting context, or transitioning environments. Exclude for routine in-session progress updates.
---

# /dump -- Session Exit and Handover

Determine invocation mode before acting:

- **User-run `/dump` (Emergency Handover)**: Triggered when the user invokes `/dump` (or `/crew:dump`) as a command, regardless of accompanying text. Stop all task execution immediately (no new reviews, dispatches, tests, or remaining steps); instruct active subagents to finish their immediate turn and return current state; cancel active timers and background tasks; then execute Steps 1-7 on work as it stands (releasing `partial`, or `done` only if all criteria were already verified).
- **Agent-run `/dump` (Routine Wrap-Up)**: Execute Steps 1-7 at session end (`/pull` completion, context reset, or environment transition).

## Procedure

### 1. Save and Push Work

Stage specific modified files (never `add -A`) and commit, noting partial state when incomplete. Push commits, open draft PRs, or persist non-git outputs only at the shared location specified by the composed workflow or `## Output` (ephemeral scratch paths vanish on exit). Record branch and commit SHA.

### 2. Retroactive Tasks (Interactive Sessions Only)

When an interactive session edits repository files without an assigned task or recovers from a significant operational fault (outage, crashed daemon, credential failure, root-caused defect -- exempting routine health checks, status pings, and minor edits), mint a retroactive task (`classification: chore|implementation`, parented to its project or operational parent, 5-section body: `Goal`, `Deliverable`, `Scope`, `Acceptance criteria`, `Pointers`) and release it `done` with SHA or health-check evidence (routing code bugs as directed by the composed workflow). Isolated workers on assigned tasks never mint retroactive tasks: record containment breaches and release `partial` or `failed`.

### 3. Capture Durable Facts & Repair Contradictions

Offer settled durable facts (decisions, constraints, verified current-state findings, or KB corrections on a 6-month horizon; exclude exploratory thinking aloud) to the knowledge-base curation role with source pointers, or record them under `## Durable Facts` on the task record and inside `### Handover Disposition` when isolated.

### 4. Release Claimed Tasks (Children First)

1. Refetch current task state (`pkb_get_task`), update `## Report` with the original ask/criteria, release outcome, and deciding primary evidence inline, and call `pkb_release_task`:
   - `done`: Single completion status when all in-scope criteria have primary evidence in `## Report` and deliverables are delivered where the composed workflow or `## Output` specifies (without waiting for CI, review, merge, or proof of user installation/deployment). Workers release `done` when in-session deliverables finish and any out-of-session work is queued as follow-up tasks.
   - `partial`: Worker's own criteria or in-session subtasks remain unfinished (blocker, scope seam, missing tool, pre-work approval boundary), or task includes an unreachable post-exit criterion (finish reachable work, leave that item unticked, cite in `reason`).
   - `failed`: Unrecoverable blocker or check failure.
   - `cancelled`: Obsolete or invalidated.
   - `in_progress`: Immediate active successor session continuing.
   - Never set or release `review` (human hold only).

```markdown
- **Original Ask (`<task-id>/AC1`)**: <Original acceptance criterion in full>
- **Outcome**: Task `<task-id>` (<title>) released as `<status>` on `<branch>` (`<commit-sha>`, `<pr-url or artifact>`), subject to `<limitations or none>`.
- **Deliverable Verification**: Primary evidence per acceptance criterion quoting deciding command outputs, counts, test receipts, or artifact links inline, plus rule compliance check (`none observed` or explicit violation disclosure with rule citation).
- **Handover Disposition**:
  - Durable facts: <settled facts with primary pointers, or none>
  - Next step: <pre-existing task-id pointer | 2-4 sentence resumption prompt | none>
  - Summary update (only if specified by the composed workflow): <concise status/finding for the workflow-specified summary target>
```

### 5. Workflow-Directed Summary Updates

Update external summaries or daily notes only if and where the composed workflow specifies. When a workflow directs a summary update, follow its format and target; isolated workers carry the summary entry inside `### Handover Disposition` rather than mutating shared notes concurrently.

### 6. Next-Step Determination

Never invent speculative follow-ups: list pre-existing dependent task pointers, coordinator-queued out-of-session follow-up IDs, a self-contained 2-4 sentence resumption prompt if `partial`/`in_progress`, or `None` if `done`.

### 7. Emit Final Handover Report

- **Agent-to-agent handovers (workers, subagents, container coordinators)**: Report task ID and release status (`done | partial | failed | cancelled | in_progress`), original ask and acceptance criteria with sourced primary evidence (branch, commit SHA, PR/artifact link, test/control receipts), limitations, durable facts, next step (`task-id` link | resumption prompt | none), any workflow-directed summary entry, and disclosed rule violations.
- **User-facing handover directly to the user**: Present a concise Markdown handover covering task, status, outputs, verified evidence, next step, durable facts, limitations, and any disclosed rule violations.
