---
name: tick
type: skill
description: Periodic sweep to nudge in-flight, high-focus epics forward between execution steps.
---

# /tick -- Epic Progression

Advance in-flight epics that have stalled. Focus on resolving blockers on a small batch of high-priority epics.

## Protocol

1. **List active epics**: Retrieve in-flight epics ordered by `focus_score` descending.
2. **Reconcile status**: Run `/aops:reconcile` in batch mode before judging work stuck.
3. **Check liveness**: Skip epics with currently executing tasks.
4. **Unblock selected epics**: Select 2-3 genuinely stuck epics per pass:
   - Resolve transient issues (CI runs, draft PRs) autonomously per the epic's task instructions.
   - **Dispatch leaves, never parents.** Walk the parent's children in `depends_on` order and dispatch the first whose dependencies are satisfied. A task with children is a parent: hold it, step it, and read the aggregate of its children rather than dispatching it. `blocked` is derived, so a child whose dependency has not landed is not a candidate.
   - Delegate deep inspection of diffs or transcripts to sub-agents to conserve context.
   - When human decisions are required, assign the decision node to the user and prompt with a brief summary and recommendation via `AskUserQuestion`.
5. **Assess every returned leaf, and do not believe exit 0.** A container exits zero whether or not it delivered, and `/reconcile` does not reset stale claims -- nothing else catches a clean exit that pushed nothing. For each leaf that came back:
   - Confirm the branch exists and the task carries evidence (`completion_evidence`, `pr_url`, or an observable artifact named in its acceptance criteria). A self-report is not evidence.
   - Choose the status: `merge_ready` (pushed, PR open), `partial` (clean seam, remainder named), `review` (a genuine question only the user can answer -- last resort), or back to `queued` (nothing landed, or the work does not meet its criteria). Never `done` -- that is `/reconcile`'s alone, on an observed merge.
   - Then advance to the next child per step 4.
6. **Systemic halt**: If an epic fails bumping repeatedly across passes, report the systemic blockage once and halt.
