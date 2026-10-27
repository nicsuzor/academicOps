---
name: dump
description: Session exit and handover -- commit and push work, release claimed PKB tasks, and emit a final report. Use when completing, pausing, or handing off a session.
---

# Dump -- Session Exit

Finalize session work and provide a structured handover before exit.

## Handover Process

### 1. Save and Push Work

1. Commit all modified files. If work is incomplete, describe what is partial in the commit message.
2. Deliver commits only where the task's Output names. If Output says nothing is pushed or names only local artifacts, do not push. If Output names a branch or pull request, push commits to that remote branch (`git push`).
3. For pull requests (`gh pr create`), target the diverged base branch (e.g. `--base "${BASE_BRANCH:-${POLECAT_BASE_BRANCH}}"`).
4. Record the branch name and commit SHA in the final report.

### 2. Release Claimed Tasks

For each claimed task (releasing child tasks first), update the task body (`pkb_update_body` or `pkb_update_task`) so its `## Report` section records the outcome and the `premise-check` report argument (written per the `premise-check` report-form reference, asked by the task's frozen ask ids). Before calling `pkb_release_task`, export and file the report's `argdown` claims to the OpenTelemetry / Phoenix span collector as claims to be verified:

```bash
uv run --project <plugin-dir> python3 <plugin-dir>/skills/dump/scripts/file_claims.py --claim <task_id> --argdown-file <path-to-argdown-or-report>
```

Then call `pkb_release_task` via the `services` MCP server's code-mode interface (`portal_codemode_execute` running `async () => await codemode.pkb_release_task({ id: "<task_id>", status: "<status>" })`; in agy via `call_mcp_tool` with `ServerName: "services"`, in Claude Code via `mcp__services__portal_codemode_execute`) with the appropriate terminal status:

- `done`: All acceptance criteria are fully met with verified evidence recorded in the task's Report section: quoted output, `file:line` citations, counts, the specimen run where requested, and the report argument answering each `<task id>/AC<n>` from that evidence. A worker whose deliverable is a PR releases `review` instead (below). An empty, template, or bare-assertion report is released as `partial`.
- `partial`: The worker's own acceptance items remain unfinished -- a scope seam, an external dependency, or a missing tool. Never release as `partial` because a dependent follow-up (QA, merge, deploy) remains to run. A follow-up task carries the remainder; record it under Next and wire a `needs` edge to any blocker (FR:334).
- `review`: Either the worker's PR is open and awaits merge by the repository (record `pr_url`; do not wait for CI, review or merge; `/reconcile` writes `done` on the merge), or the worker needs help to finish the task. Help is transient, never a waiting state: a worker hands back on the record, documenting what help is needed in `reason`, and never addresses or escalates to the user. Any reconcile pass reading a `review` task transitions it immediately.
- `failed`: The task cannot be completed and has reached a terminal failure. Document failure evidence and root cause.
- `cancelled`: Task is obsolete or invalidated. Document reason.
- `in_progress`: Use only if an active successor session is immediately continuing work.

Task report format (for the `release_task` body update in `## Report` and the session task summary):

````markdown
### Task: <task-id> (<title>) -- <status>

- **Update**: [1-3 sentences on work completed and remaining]
- **Output**: [Branch, commit SHA, PR link, or artifact path]
- **Next**: [Clear instructions for successor agent]
- **Proof**:

```argdown
<the premise-check argdown block, asked by the task's ask ids>
```
````

The status above is the task's release status. PASS, REVISE and FAIL are the checker's verdict on this argument, recorded by whoever checks it under `## Premise-Check Verdict`; a worker never writes a verdict on its own report.

If the release tool is unavailable, record the failure trace and list claimed task IDs in the final report.

### 3. Emit Final Handover Report

Compile the overall session outcome, retaining only non-duplicated handover metadata and pointers (fields already present in the argdown block or task record -- such as redundant status/safeguards and repeating the argument block verbatim -- are omitted):

```markdown
## Handover: <agent> <session-id>

1. **Task**: Task id and title.
2. **Output**: <branch + commit SHA> | <PR or artifact link>
3. **Pointers**: Task `## Report` / filed claim ID, verification reference, or artifact paths.
4. **Limitations**: Unresolved items, out-of-scope elements, and verbatim error outputs.
5. **Next**: Clear instructions for successor agent.
```

### 4. Trailing Session Summary

Even though the general rule is "most important line first", print a concise session summary as the **final trailing line** of the session output, because the handover block often scrolls off the user's screen in long terminal sessions:

```markdown
Summary: <1-line concise summary of outcome, modifications, and release status>
```
