---
name: dump
description: Session exit and handover -- execute an immediate emergency handover when invoked by the user, or a calm routine wrap-up when invoked by the agent at session end (committing work, minting retroactive tasks, capturing durable facts, releasing tasks, and emitting a final report). Use when the user runs /dump, or when completing work, resetting context, or transitioning environments. Exclude for in-session updates (use /reconcile).
---

# /dump -- Session Exit and Handover

Determine invocation mode before acting:

- **User-run `/dump` (Emergency Handover)**: Triggered when the user invokes `/dump` (or `/ida:dump`) as a command, regardless of accompanying text. Stop all task execution immediately (no new reviews, dispatches, tests, or remaining steps); instruct active subagents to finish their immediate turn and return current state; cancel active timers and background tasks; then execute Steps 1-7 on work as it stands (releasing `partial`, or `done` only if all criteria were already verified).
- **Agent-run `/dump` (Routine Wrap-Up)**: Execute Steps 1-7 at session end (`/pull` completion, context reset, or environment transition).

## Procedure

### 1. Save and Push Work

Stage specific modified files (never `add -A`) and commit, noting partial state when incomplete. Push commits and open draft PRs (`gh pr create --draft` targeting the diverged base branch) only where `## Output` specifies; mark `gh pr ready` only after the independent check passes and its verdict is posted. Persist non-git evaluation datasets and reports in the PKB (ephemeral scratch paths vanish on exit). Record branch and commit SHA.

### 2. Retroactive Tasks (Interactive Sessions Only)

When an interactive session edits repository files without an assigned task or recovers from a significant operational fault (outage, crashed daemon, credential failure, root-caused defect -- exempting routine health checks, status pings, and minor edits; file code bugs on GitHub issues), mint a retroactive task (`classification: chore|implementation`, parented to its project or operational epic, 5-section body: `Goal`, `Deliverable`, `Scope`, `Acceptance criteria`, `Pointers`) and release it `done` with SHA or health-check evidence. Isolated workers on assigned tasks never mint retroactive tasks: record containment breaches and release `partial` or `failed`.

### 3. Capture Durable Facts & Repair Contradictions

Offer settled durable facts (decisions, constraints, verified current-state findings, or KB corrections on a 6-month horizon; exclude exploratory thinking aloud) directly to the custodian (`pauli`) with source pointers, or record them under `## Durable Facts` when isolated.

### 4. Release Claimed Tasks (Children First)

1. Refetch current task state (`pkb_get_task`), update `## Report` with outcome and the `premise-check` `argdown` block (using frozen ask IDs), and call `pkb_release_task` with `session_id`:
   - `done`: Single completion status when all in-scope criteria have primary evidence in `## Report` and deliverables are delivered (draft PR opened with `pr_url`/`branch`, or PKB artifact recorded -- without waiting for CI, review, merge, or proof of user installation/deployment). Coordinators (`/supervise`) release `done` when in-session deliverables finish and out-of-session work is queued as follow-up tasks; leaf workers (`/pull`) satisfy all criteria directly.
   - `partial`: Worker's own criteria or in-session subtasks remain unfinished (blocker, scope seam, missing tool, pre-work approval boundary), or task includes an unreachable post-exit criterion (finish reachable work, leave that item unticked, cite in `reason`).
   - `failed`: Unrecoverable blocker or check failure.
   - `cancelled`: Obsolete or invalidated.
   - `in_progress`: Immediate active successor session continuing.
   - Never set or release `review` (human hold only). Workers never write `## Premise-Check Verdict`.

````markdown
### Task: <task-id> (<title>) -- <status>

- **Update**: [1-3 sentences on completed and remaining work]
- **Output**: [Branch, commit SHA, PR link, or artifact path]
- **Rule Violations**: [None | Rule name, source, explanation]
- **Proof**:

```argdown
<premise-check argdown block, asked by task ask IDs>
```
````

### 5. Consolidated Daily Note Updates

For touched projects (modified repo files, updated tasks, or major operational/empirical finds): interactive and coordinator sessions write one consolidated bullet per project under `## Today's work`: `- **<project>**: <10-20 word status/find> -- Next: <pointer or prompt>` (omit `-- Next:` when complete). Isolated workers emit these bullets in handover output to avoid write contention.

### 6. Next-Step Determination

Never invent speculative follow-ups: list pre-existing dependent task pointers, coordinator-queued out-of-session follow-up IDs, a self-contained 2-4 sentence resumption prompt if `partial`/`in_progress`, or `None` if `done`.

### 7. Emit Final Handover Report

```markdown
## Handover: <agent> <session-id>

1. **Task**: <task-id and title, or "Ad-hoc / Retroactive: <id>">
2. **Summary**: <findings, modifications, outcomes>
3. **Status & Safeguards**:
   - STATUS: <done | partial | failed | cancelled | in_progress>
   - CRITERION: <acceptance criterion ID tested and observed result>
   - CONFIDENCE: <high | med | low> + <single falsifying check>
   - CONFOUND CHECK: <clean-room/differential control result | NOT RUN>
4. **Output**: <branch + commit SHA | PR or artifact link>
5. **Next step**: <task-id link | Resumption prompt | None>
6. **Durable Facts**: <None | list for custodian>
7. **Argument**: <argdown block from ## Report>
8. **Limitations**: <unresolved items, out-of-scope elements, verbatim errors>
9. **Rule Violations**: <None | violations with citations>
```
