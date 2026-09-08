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
   - Dispatch epics rather than individual child tasks once decomposition is complete.
   - Delegate deep inspection of diffs or transcripts to sub-agents to conserve context.
   - When human decisions are required, assign the decision node to the user and prompt with a brief summary and recommendation via `AskUserQuestion`.
5. **Systemic halt**: If an epic fails bumping repeatedly across passes, report the systemic blockage once and halt.
