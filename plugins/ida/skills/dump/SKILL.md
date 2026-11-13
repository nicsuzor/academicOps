---
name: dump
description: Session exit and handover -- execute an immediate emergency handover when invoked by the user, or a calm routine wrap-up when invoked by the agent at session end (committing work, minting retroactive tasks, capturing durable facts, releasing tasks, and emitting a final report). Use when the user runs /dump, or when completing work, resetting context, or transitioning environments. Exclude for in-session updates (use reconcile).
---

# Dump -- Session Exit and Handover

Determine the invocation mode before acting:

- **How to tell the two modes apart**:
  - **User-run `/dump` (Emergency Handover)**: The user invokes `/dump` (or `/ida:dump`) as a command in their message or prompt turn (as opposed to asking an informational question about how `/dump` works), **whatever wording, context, or trailing instructions accompany the command**.
  - **Agent-run `/dump` (Routine Wrap-Up)**: The agent invokes `/dump` on its own initiative at a session end (when a task finishes via `/pull`, when resetting context, or when moving to another execution environment).

- **Mode 1: User-Run `/dump` (Emergency Handover)**:
  1. **Stop where you are currently**: Halt all in-progress task execution at the exact point reached. Start **no further work first** -- no new reviews, no new dispatches, no re-dispatches, no new test suites, and no continuation of remaining task steps, whatever accompanying wording came with the `/dump` command.
  2. **Tell running subagents to finish their immediate turn**: Immediately message every running subagent (e.g. `send_message`) instructing it to finish its immediate turn and return its current state without starting another step, and terminate any active background command tasks or scheduled timers (e.g. `manage_task: kill`).
  3. **Save current state to the PKB and hand over**: Execute Steps 1–7 below for the work as it stands right now -- commit modified files (describing partial state), update and release claimed PKB tasks as `partial` (or `done` only if all acceptance criteria were already verified before `/dump` was called), persist durable facts and project status to the PKB, and emit the final handover report.

- **Mode 2: Agent-Run `/dump` (Routine Wrap-Up)**:
  - Execute the calm, routine wrap-up across Steps 1–7 below when ending a session upon task completion, context reset, or environment transition.

## Procedure

### 1. Save and Push Work

1. Stage specific modified files (never blanket `add -A`) and commit. If work is incomplete, describe what is partial in the commit message.
2. Deliver commits only where the task's Output names. If Output says nothing is pushed or names only a PKB task or note, do not push. If Output names a branch or pull request, push commits to that remote branch (`git push`). If the PR is a draft and its code step is complete, mark it ready for review (`gh pr ready`) without waiting for approval. Ephemeral container and session scratch paths (`<appDataDir>/brain/`, `/tmp/`, unpushed working trees) vanish on exit; persist non-git evaluation datasets, specimen tables, and reports in the PKB with durable pointers.
3. For pull requests (`gh pr create`), target the diverged base branch (e.g. `--base "${BASE_BRANCH:-${POLECAT_BASE_BRANCH}}"`).
4. Record the branch name and commit SHA in the final report.

### 2. Retroactive Tasks for Unparented Project Edits and Operational Faults

If an ad-hoc or interactive session modified repository project files without an assigned task, or diagnosed and fixed/recovered from a significant operational fault without modifying repository files, create a retroactive task on the knowledge graph before exit:

1. **Minting & Parentage**: Mint a task via task creation tools with `classification: chore` or `implementation`, linking `parent` to the relevant project or standing operational epic (preventing orphan root tasks). Provide a concise, verb-led imperative title (e.g. `Recover gateway from 502 outage`).
2. **Canonical Body Format**: Format the body using the canonical 5-section concise template (`Goal`, `Deliverable`, `Scope`, `Acceptance criteria`, `Pointers`) per `synthesize-not-accrete`. Diagnostic logs and recovery checks belong in completion metadata (`status: done` release evidence); enduring architectural insights belong in durable topic notes offered to the knowledge base custodian (`pauli`).
3. **Immediate Release**: Release the task immediately as `done` with completion evidence detailing touched files and commit SHA, or operational recovery actions and verified health check.
4. **Significant Fault Threshold**: Covers service downtime/degradation (HTTP 500/502/503, inaccessible endpoints), crashed or leaking containerized services/daemons requiring manual restarts, authentication/credential failures, and latent defects diagnosed to root cause.
5. **Routine Operations Exempt**: Status checks, health pings, inspecting healthy logs, ephemeral local container restarts during normal development without an underlying fault, routing sweeps, and conversational queries require no task. Minor user-directed edits not useful 30 days later require no task.
6. **Bug Tracking Demarcation**: Retroactive tasks capture the operational recovery chore on the graph. Latent software defects or code bugs are filed on GitHub issues ("Bugs go on GitHub only").
7. **Headless Workers**: Dispatched workers on assigned tasks are strictly bound to their task boundary; unparented edits or external faults are a containment breach under `fail-fast` -- record observations for handover and release `partial` or `failed` rather than minting unrelated retroactive tasks.

### 3. Capture Durable Facts and Repair Contradictions

1. **Durable Facts (Six-Month Threshold)**: Review decisions, constraints, and verified environment invariants learned during the session. If a fact holds enduring institutional value across a six-month horizon:
   - In interactive sessions, offer the fact directly to the knowledge base custodian (`pauli`) as content.
   - In headless or isolated worker sessions, record the facts under `## Durable Facts` in the task record and handover summary for custodian collection.
2. **Knowledge Base Repair on Sight**: When encountering conflicting, incorrect, irrelevant, demonstrably false, or outdated knowledge base information during the session, report the contradiction and affected notes to the custodian (`pauli`) for on-sight correction and pruning.

### 4. Release Claimed Tasks

For each claimed task (releasing child tasks first):

1. **Refetch Current Task State**: Fetch the latest task state from the PKB (`pkb_get_task`) prior to applying updates or generating the report. This ensures fresh visibility into requirements, acceptance criteria to verify and tick, and the real-time completion status of subtasks.
2. **Update Task Body and Report**: Update the task body so its `## Report` section records the outcome and the `premise-check` report argument (asked by the task's frozen ask ids).
3. **Release via `pkb_release_task`**, passing the active `session_id`:

- `done`: All acceptance criteria are fully met with verified evidence recorded in the task's Report section: quoted output, `file:line` citations, counts, specimen runs, and the report argument answering each `<task id>/AC<n>`. All child tasks and subtasks created by the session must be completed; if any subtask remains open, the parent task cannot be released as `done`. When the deliverable is a PR, push the branch, open the PR, record `pr_url` and branch, and release `done`. An empty, template, or bare-assertion report is released as `partial`.
- `partial`: The worker's own acceptance items remain unfinished (a scope seam, an external dependency, a context reset, or a missing tool) OR child tasks/subtasks created by the session remain uncompleted. If the session created subtasks that have not finished, the claimed task must be released as `partial` (never `done`), documenting what was completed, open subtasks, and what remains unfinished in `reason` and `## Report`. Never release as `partial` merely because an external dependent check (QA, merge, deploy) remains to run.
- `failed`: Terminal failure, unrecoverable blocker, or check failure (e.g. QA or review). Document failure evidence and root cause.
- `cancelled`: Task is obsolete or invalidated. Document reason.
- `in_progress`: Use only if an active successor session is immediately continuing work.
- `review`: Never set or release `review`. Reserved exclusively for manual human holds applied directly by the user.

Task report format (for `release_task` body update in `## Report` and session task summary):

````markdown
### Task: <task-id> (<title>) -- <status>

- **Update**: [1-3 sentences on work completed and remaining]
- **Output**: [Branch, commit SHA, PR link, or artifact path]
- **Rule Violations**: [None | List of violations with rule name, source, and explanation]
- **Proof**:

```argdown
<the premise-check argdown block, asked by the task's ask ids>
```
````

The status above is the task's release status. PASS, REVISE and FAIL are the checker's verdict on this argument, recorded by whoever checks it under `## Premise-Check Verdict`; a worker never writes a verdict on its own report. If the release tool is unavailable, record the failure trace and list claimed task IDs in the final report.

### 5. Consolidated Daily Note Project Updates

Determine all projects touched during the session (modified files, updated tasks, or major operational finds without code changes):

- **Triggers**: Projects touched are determined by (1) repository files modified, (2) claimed or retroactive tasks updated, or (3) major operational finds or service recoveries achieved without code changes.
- **Major Find Threshold**: Remediating a significant service outage/fault, isolating root causes of systemic issues, or significant empirical discoveries that invalidate hypotheses or uncover critical risks. Routine commands, status queries, or pure triage sweeps are exempt. Shared service/daemon recoveries attribute to the relevant platform infrastructure project.
- **Recording Format**:
  - _Interactive / Coordinator Sessions_: Write exactly one consolidated bullet per touched project into the daily note under `## Today's work`:
    `- **<project-name>**: <latest status or major find in 10-20 words> -- Next: <pointer or resumption prompt>`
    If the completed recovery has no follow-up task or resumption prompt, omit the `-- Next: ...` suffix:
    `- **<project-name>**: <latest status or major find in 10-20 words>`
  - _Headless / Isolated Worker Sessions_: Emit the consolidated project status in the handover block on the record to prevent write contention; subsequent daily sweeps absorb them.

### 6. Disciplined Next-Step Determination

Workers never sequence work or invent speculative follow-ups ("park on a downward slope"):

1. _Pre-Existing Dependent Work_: If an authorized follow-up task, child QA task, or review task already exists on the graph, provide an explicit pointer (`[[task-id]]` or URL).
2. _Interrupted Work_: If a task is released as `partial` or `in_progress` (context boundary, environment migration, user halt), provide a self-contained 2-4 sentence resumption prompt detailing current state, touched files, and exact starting instructions for a fresh agent.
3. _Fully Completed Work_: If the task is `done` and no pre-existing dependent task exists on the graph, state `None`.

### 7. Emit Final Handover Report

Compile the overall session outcome with session traceability:

```markdown
## Handover: <agent> <session-id / conversation-id>

1. **Task**: <task-id and title, or "Ad-hoc / Retroactive: <id>">
2. **Summary**: Concise synthesis of findings, modifications, and outcomes.
3. **Status & Safeguards**:
   - STATUS: <done | partial | failed | cancelled | in_progress>
   - GATE: <the acceptance criterion id tested, and observed result against it>
   - CONFIDENCE: <high | med | low> + <what single check would falsify this>
   - CONFOUND CHECK: <did a clean-room/differential control run? result? -- or "NOT RUN">
4. **Output**: <branch + commit SHA> | <PR or artifact link>
5. **Next step**: <[[task-id]] pointer | Resumption prompt | None>
6. **Durable Facts**: [None | List of durable facts offered to Pauli or recorded for collection]
7. **Argument**: The `argdown` block recorded under the task's `## Report`.
8. **Limitations**: Unresolved items, out-of-scope elements, and verbatim error outputs.
9. **Rule Violations**: [None | Disclosed violations with rule citations and reasons]
```
