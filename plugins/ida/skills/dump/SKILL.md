---
name: dump
description: Session exit and handover -- commit and push work, release claimed PKB tasks, and emit a final report. Use when completing, pausing, or handing off a session. Exclude for in-session updates (use reconcile).
---

# Dump -- Session Exit

Finalize session work and provide a structured handover before exit.

## Handover Process

### 1. Save and Push Work

1. Commit all modified files. If work is incomplete, describe what is partial in the commit message.
2. Deliver commits only where the task's Output names. If Output says nothing is pushed or names only a PKB task or note, do not push. If Output names a branch or pull request, push commits to that remote branch (`git push`). Ephemeral container and session scratch paths (`<appDataDir>/brain/`, `/tmp/`, unpushed container working trees) vanish on exit; non-git evaluation datasets, specimen tables, and reports must be persisted in the PKB with durable pointers rather than stored in ephemeral directories.
3. For pull requests (`gh pr create`), target the diverged base branch (e.g. `--base "${BASE_BRANCH:-${POLECAT_BASE_BRANCH}}"`). If the pull request requires user or reviewer approval, create it in draft state (`--draft`) to suppress review notifications until proportionate review receipts are posted to the thread.
4. Record the branch name and commit SHA in the final report.

### 2. Release Claimed Tasks

For each claimed task (releasing child tasks first), update the task body so its `## Report` section records the outcome and the `premise-check` report argument (written per the `premise-check` report-form reference, asked by the task's frozen ask ids), then release the task via `pkb_release_task` with the appropriate terminal status:

- `done`: All acceptance criteria are fully met with verified evidence recorded in the task's Report section: quoted output, `file:line` citations, counts, the specimen run where requested, and the report argument answering each `<task id>/AC<n>` from that evidence. When the deliverable is a PR, the worker pushes the branch, opens the PR, records `pr_url` and branch, and releases `done`. An empty, template, or bare-assertion report is released as `partial`.
- `partial`: The worker's own acceptance items remain unfinished -- a scope seam, an external dependency, or a missing tool. Never release as `partial` because a dependent check (QA, merge, deploy) remains to run. Workers document what was completed and what remains unfinished in `reason` and `## Report`; workers never create or name follow-up tasks, and reports carry no 'Next task' pointer (the reconcile pass and parent epic handle next actions).
- `review`: Reserved exclusively for manual human holds applied directly by the user. Workers and automated sessions never set or release `review`. If work requires an escalated decision or has incomplete items, release `partial` with documented reason.
- `failed`: The task cannot be completed, has reached a terminal failure, or a check failed (e.g. QA or review). Document failure evidence and root cause. Never file fix tasks or follow-up tasks; the reconcile pass notes failed tasks and decides next actions from the parent epic.
- `cancelled`: Task is obsolete or invalidated. Document reason.
- `in_progress`: Use only if an active successor session is immediately continuing work.

Task report format (for the `release_task` body update in `## Report` and the session task summary):

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

The status above is the task's release status. PASS, REVISE and FAIL are the checker's verdict on this argument, recorded by whoever checks it under `## Premise-Check Verdict`; a worker never writes a verdict on its own report.

If the release tool is unavailable, record the failure trace and list claimed task IDs in the final report.

### 3. Emit Final Handover Report

Compile the overall session outcome:

```markdown
## Handover: <agent> <session-id / conversation-id>

1. **Task**: Task id and title.
2. **Summary**: Concise synthesis of findings and modifications.
3. **Status & Safeguards**:
   - STATUS: <release status: done | partial | failed | cancelled | in_progress>
   - GATE: <the acceptance criterion id tested, and observed result against it>
   - CONFIDENCE: <high | med | low> + <what single check would falsify this>
   - CONFOUND CHECK: <did a clean-room/differential control run? result? -- or "NOT RUN">
4. **Output**: <branch + commit SHA> | <PR or artifact link>
5. **Argument**: The `argdown` block recorded under the task's `## Report`.
6. **Limitations**: Unresolved items, out-of-scope elements, and verbatim error outputs.
7. **Rule Violations**: [None | Disclosed violations with rule citations and reasons]
```
