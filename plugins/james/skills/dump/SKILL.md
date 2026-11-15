---
name: dump
description: Session exit and handover -- execute an immediate emergency handover when invoked by the user, or a calm routine wrap-up at session end (committing work, minting retroactive tasks when needed, capturing durable facts, releasing tasks, and emitting a final report). Use when the user runs /dump, or when completing work via /james:pull or /james:supervise, resetting context, or transitioning environments.
---

# Dump -- Session Exit and Handover

Determine the invocation mode before acting:

- **User-run `/dump` (Emergency Handover)**: Invoked when the user runs `/dump` (or `/james:dump`) as a command in their prompt turn (not an informational question about `/dump`), whatever wording, context, or trailing instructions accompany it.
- **Agent-run `/dump` (Routine Wrap-Up)**: Invoked on the agent's own initiative at session end (task completion via `/james:pull` or `/james:supervise`, context reset, or environment transition).

## Mode 1: User-Run `/dump` (Emergency Handover)

1. **Stop immediately**: Halt all in-progress task execution at the exact point reached. Start no further work -- no new reviews, dispatches, test suites, or remaining task steps.
2. **Wind down active work**: Message any active subagents (`send_message`) to finish their immediate turn and return current state without starting new steps, and cancel active background tasks or timers (`manage_task: kill`).
3. **Save current state and hand over**: Execute Steps 1-7 below for the work as it stands right now -- commit modified files (describing partial state), record durable facts under `## Durable Facts` (passing directly to `pauli` only if already active, or persisting via `pkb` MCP without spawning a new subagent), release claimed tasks as `partial` (or `done` only if all acceptance criteria were already verified before `/dump` was called), and emit the final handover report.

## Mode 2: Agent-Run `/dump` (Routine Wrap-Up)

Execute the routine wrap-up across Steps 1-7 below.

## Procedure

### 1. Save and Push Work

1. Stage specific modified files (never blanket `add -A`) and commit, scrubbing private identifiers, PKB IDs, session trailers, personal names, and private hostnames for public repositories (`data-boundaries`). Describe incomplete state explicitly if partial.
2. Deliver commits only where the task's Output names (`git push` when targeting a remote branch or pull request; do not push if Output names only local state or a PKB node). Open pull requests as draft (`gh pr create --draft`) targeting the repository's integration branch (or `$AOPS_BASE_BRANCH` / `$BASE_BRANCH` when set), and mark ready (`gh pr ready`) once required in-session checks and review verdicts are posted. Persist non-git reports and datasets in the PKB rather than ephemeral scratch paths.
3. Record the branch name and commit SHA in the final report.

### 2. Retroactive Tasks for Unparented Project Edits and Operational Faults

If an ad-hoc or interactive session modified repository files without an assigned task, or diagnosed and recovered from a significant operational fault, create a retroactive task via `pkb` MCP before exit:

1. **Minting & Parentage**: Create a task (`classification: chore` or `implementation`) with a concise verb-led imperative title and `parent` set to the relevant project or standing operational epic.
2. **Canonical Body Format**: Use the concise 5-section structure (`Goal`, `Deliverable`, `Scope`, `Acceptance criteria`, `Pointers`) per `synthesize-not-accrete`. Keep diagnostic logs in release evidence and durable architectural insights in PKB knowledge notes.
3. **Immediate Release**: Release immediately as `done` with completion evidence (touched files and commit SHA, or verified recovery check).
4. **Thresholds & Scope**: Covers service outages/degradations, crashed daemons requiring restarts, credential failures, and diagnosed latent defects; exempts routine status checks, healthy restarts during normal development, and minor user-directed edits. Latent software defects belong in GitHub issues ("Bugs go on GitHub only").
5. **Scoped Leaf Workers**: Workers on assigned leaf tasks stay strictly within their claimed task boundary; record out-of-scope faults for handover and release `partial` or `failed` rather than minting unrelated retroactive tasks.

### 3. Capture Durable Facts and Repair Contradictions

1. **Durable Facts (Six-Month Horizon)**: Review verified decisions, constraints, and environment invariants learned during the session:
   - When `pauli` is active or in coordinator sessions, update durable PKB topic notes via `pkb` MCP tools or delegate curation to `pauli`.
   - In isolated worker sessions, record durable facts under `## Durable Facts` in the task record and handover summary.
2. **Knowledge Base Repair on Sight**: When encountering outdated, conflicting, or demonstrably false PKB content, update or prune it via `pkb` MCP tools or report the affected node IDs to `pauli` for immediate correction.

### 4. Release Claimed Tasks

For each claimed task (releasing child tasks first):

1. **Refetch Current Task State**: Read the latest task state (`pkb_get_task`) before updating or verifying acceptance criteria.
2. **Update Body, Report & File Claims**: Record completion evidence and the `james:premise-check` `argdown` block under `## Report`, answering each ask ID. When filing argdown claims to OTel/Phoenix, run `scripts/file_claims.py` inside this skill directory (`uv run --project <plugin-dir> python scripts/file_claims.py --claim <task-id> --argdown-file <path> --session <session-id>`).
3. **Release via `pkb_release_task`**, passing the active `session_id`:
   - `done`: All in-scope acceptance criteria are met with primary evidence in `## Report` (`file:line`, quoted output, counts, or specimen runs) answering every `<task id>/AC<n>`. In `/james:supervise`, all in-session deliverables and PRs are complete and any explicitly deferred work is queued on out-of-session follow-up tasks (recorded under `Next step`). In `/james:pull`, all acceptance items are satisfied directly.
   - `partial`: Acceptance items or in-session subtasks remain unfinished (scope seam, missing tool, context reset, or external dependency), documenting what remains in `reason` and `## Report`. Never release `partial` merely because external CI, review, or merge remains.
   - `failed`: Terminal failure, unrecoverable blocker, or failed check, with root cause and evidence.
   - `cancelled`: Task is obsolete or invalidated, stating the reason.
   - `in_progress`: Only when an active successor session continues immediately.
   - `review`: Never release `review`; reserved for manual human holds.

Task report format:

````markdown
### Task: <task-id> (<title>) -- <status>

- **Update**: [1-3 sentences on work completed and remaining]
- **Output**: [Branch, commit SHA, PR link, or artifact path]
- **Rule Violations**: [None | List of violations with rule name, source, and explanation]
- **Proof**:

```argdown
<the james:premise-check argdown block, asked by the task's ask ids>
```
````

Verdicts (`PASS`, `REVISE`, `FAIL`) are recorded solely by the checker under `## Premise-Check Verdict` via `james:premise-check` (`verdict.py --judged-file <path>`); a worker never writes a verdict on its own report.

### 5. PKB Project and Task Status Updates

For each project touched (modified repository files, updated tasks, or major operational recoveries):

- **Interactive / Coordinator Sessions**: Update the relevant PKB task and project or topic records via the configured PKB MCP tools with a concise status summary (`<latest status or major find>` and `Next: <pointer or resumption prompt>` when follow-up work remains).
- **Headless / Delegated Sessions**: Record the concise project status summary directly in the task's `## Report` and session handover output to avoid concurrent write contention.

### 6. Disciplined Next-Step Determination

Never invent speculative follow-ups:

1. _Pre-Existing or Coordinator Follow-Ups_: Name authorized follow-up task IDs (`<task-id>` or URL) already wired on the graph.
2. _Interrupted Work (`partial` / `in_progress`)_: Provide a self-contained 2-4 sentence resumption prompt with current state, touched files, and exact starting instructions.
3. _Completed Work_: State `None` when `done` with no follow-up task on the graph.

### 7. Emit Final Handover Report

````markdown
## Handover: <agent> <session-id / conversation-id>

- **Summary**: <task-id / status, concise synthesis of modifications, outcomes, durable facts, and next step>
- **Artifacts / PR**: <branch + commit SHA, PR URL, or artifact path>
- **Rule Violations**: <None | Disclosed violations with rule citations and reasons>

```argdown
<the james:premise-check argdown block recorded under the task's ## Report>
```
````
