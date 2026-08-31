---
name: dump
description: "Session exit and handover — commit and push your work, release any claimed PKB tasks with a status report, and emit a single final handover message. Invoke whenever a session is ending, being interrupted, or work must be handed off to the next agent."
---

# Dump — Session Exit

Every session exit must provide a formal handover.

If you have hit an error, exhausted your resources, or have been asked to terminate:

- you must abort immediately, save any progress, and return with minimal explanation and a simple resume path.
- you must still provide a handover message.
- if you have a task claimed, you must release it if you can.

## Handover process

### 1. SAVE AND PUSH YOUR WORK

You are running in an isolated, _ephemeral_ environment. Any files left on your local storage will be DESTROYED.

- You must commit and push your work if you can (`git push`).
- If you are opening a pull request (`gh pr create`), always target the base branch matching the cut line your worktree diverged from (e.g. `--base "${BASE_BRANCH:-${POLECAT_BASE_BRANCH}}"`); never hardcode `dev`, `main`, or `master`.
- If you are blocked from pushing, you must find another way to save your work in a durable location.

### 2. RELEASE YOUR TASKS

For EACH task you have worked, starting with children:

A. **Construct your report in the following format:**

```markdown
### Task: <task-id> (<precis>) — <status: done | cancelled | review | blocked | in_progress >

- **Update**: [ 1-3 sentences: what you did, what you learned, what remains ]
- **Output**: [ reference to any artifacts or work produced: e.g. `<branch>` (uncommitted: yes/no) | `url` | `pkb note id` and title | `filename` (warning: local files will be destroyed on exit)]
- **Next**: `<task-id>` [ title ] | [ Plain english instructions, with just enough detail to allow the next agent to pick up the work where you left off. ]
```

B. **Release your tasks, children first:** release the task with your session
id and your concise report via the PKB MCP tool (`pkb__release_task` or
`release_task`). If the MCP tool fails or is unavailable, HALT and say so in
your final report (`halt-on-failure`). Never fall back to direct filesystem
access in `$ACA_DATA` or the `pkb` CLI.

### 3. EMIT FINAL REPORT

Compile each of your reports into a single final message:

```markdown
## Handover: <agent> <session-id>

1. **The task** — restate the whole thing you were asked to do, and check you
   have not read the scope more narrowly than it was written.
2. **Summary** — what you found or made.
3. **Output**: <PR or artefact URL> (description)
4. **Receipts** — itemized claims with their basis tag:
   - `[observed: <file:line | command+output | URL>]` for directly observed empirical facts.
   - `[attempted-and-failed: <command> -> <error>]` for attempted actions and capability limits.
   - `[exhaustively-searched: <tool/query/scope>]` for absence claims.
   - `[not-observed]` for data not found in non-exhaustive lookups.
   - `[inferred: <premises>]` / `[assumed]` / `[reported-by-another: <source>]`.
5. **Limitations** — what is uncertain, what failed (with verbatim errors), what you did not do.
```
