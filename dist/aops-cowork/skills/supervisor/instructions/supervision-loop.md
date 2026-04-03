# The Supervision Loop

Active, interruptible supervision of an epic. The supervisor loops
through orient → act → checkpoint on every invocation. It might dispatch one
invocation, monitor the next, react to a failure on the third.

## The Loop

Every invocation:

1. **ORIENT** — Read the epic task file. Discover the environment. Determine
   what needs doing next.
2. **ACT** — Do the highest-priority thing: decompose, dispatch, check
   PRs, merge, react to a failure, escalate a decision.
3. **CHECKPOINT** — Write updated state to the epic task body. Commit and push
   so the next invocation (possibly on a different machine) can pick up.

That's it. The supervisor is not a pipeline — it's a loop that does one
useful thing per invocation and records what it did.

## Environment Discovery

Run on every invocation. Results are transient — the environment may change.

```bash
# What machine? What tools?
hostname; which polecat claude gemini gh docker pkb 2>/dev/null

# Can I reach things?
git ls-remote origin HEAD 2>/dev/null   # GitHub
pkb search "test" --limit 1 2>/dev/null  # PKB

# What repos are available?
ls $AOPS 2>/dev/null; ls $ACA_DATA 2>/dev/null

# What's running?
docker ps 2>/dev/null; polecat list 2>/dev/null
```

Build a capability profile from discovery:

| Capability         | Check                 | Dispatch via            |
| ------------------ | --------------------- | ----------------------- |
| Local polecat      | `which polecat`       | `polecat run -t <id>`   |
| Container dispatch | `docker ps`           | `polecat crew`          |
| GitHub API         | `gh auth status`      | `gh pr`, GitHub Actions |
| PKB access         | `pkb search` or MCP   | task state management   |
| Remote triggers    | `claude trigger list` | async remote agents     |

Adapt dispatch strategy to what's actually available.

## Task File State Format

The supervisor maintains structured state in the epic task body. This is the
**only** persistent state.

```markdown
## Supervisor State

**Phase**: orienting | decomposing | dispatching | monitoring | integrating | complete
**Last checkpoint**: [ISO timestamp]
**Environment**: [where this supervisor ran]

### Work Items

| # | ID       | Title       | Status  | Worker | PR   | Notes           |
| - | -------- | ----------- | ------- | ------ | ---- | --------------- |
| 1 | task-abc | Fix widget  | done    | claude | #234 | merged 10:45    |
| 2 | task-def | Add tests   | pr_open | gemini | #235 | CI passing      |
| 3 | task-ghi | Update docs | ready   | —      | —    | unblocked by #1 |

### Dispatch Log

[ISO timestamp] [environment]: [what the supervisor did]
```

Note: the `dispatched` status in the local work items table maps to
`in_progress` in PKB task status.

### Work Item Statuses

| Status         | Meaning                                                           |
| -------------- | ----------------------------------------------------------------- |
| ready          | Decomposed, ready to dispatch                                     |
| dispatched     | Sent to worker, waiting for PR                                    |
| pr_open        | PR filed, under review                                            |
| pr_approved    | Approved, ready to merge                                          |
| done           | Merged and verified                                               |
| blocked        | Waiting on a dependency — will be unblocked automatically         |
| needs_decision | Requires human judgment before work can proceed — do not dispatch |
| failed         | Worker failed, needs re-dispatch or replan                        |

`needs_decision` maps to PKB task status `needs_review`. Agents cannot claim
tasks in these statuses, so setting them is an enforceable gate — not an
advisory note in the body.

## Verification, Not Interrogation

The supervisor NEVER asks the human to confirm factual state. That defeats
the purpose of automation. Instead:

1. **Verify independently** — check PKB task status, check GitHub PRs, check
   build artifacts, read task bodies for progress notes. If you can't verify
   something, that's an infrastructure gap to file a task about.

2. **Verification tasks as graph gates** — at important phase boundaries,
   create discrete verification subtasks (preferably for an independent agent)
   that check claims and assumptions BEFORE the next phase starts. These are
   real tasks with `depends_on` — the downstream work literally can't proceed
   until verification completes.

The human's role is judgment (methodology, priorities, academic decisions),
not fact-checking. Verification is execution — automate it.

## Phase Actions

### ORIENT

**Step 1: Verify state.** Read the epic task file. For each work item, **independently verify** current reality:

- Check PKB task status (not just what the work items table says — query live)
- Check child task status (a parent may be done if all children are done)
- If dispatched: check for PRs (`gh pr list --search "head:polecat/{id}"`)
- If pr_open: check review/CI status
- Check git log for recent changes to task files
- Has anything been merged since last checkpoint?

Update the work items table to match verified reality. Then decide what to do next.

### DECOMPOSE

Break the goal into PR-sized subtasks. Use the protocols in
[[decomposition-and-review]]. Create subtasks in PKB, add them to the
work items table.

Incremental decomposition is normal — add subtasks mid-flight when a worker
discovers something is bigger than expected.

### DISPATCH

1. Select ready work items
2. Run pre-dispatch validation (see [[worker-dispatch]]):
   - Target files still exist?
   - Task belongs in the right repo?
   - AC is implementable against current codebase?
3. Record dispatch in the task file BEFORE firing the worker
4. Fire the worker: `polecat run -t <id> -p <project>`
5. Update status to `dispatched`

### MONITOR

For each dispatched/pr_open item:

- Check PKB for status changes
- Check GitHub for PRs (`gh pr list`, `gh pr view`)
- Update the work items table

No active polling loops. Check once per invocation.

### REACT

| Problem                           | Response                                           |
| --------------------------------- | -------------------------------------------------- |
| Worker failed (no PR, task reset) | Re-dispatch, possibly different worker             |
| PR has merge conflicts            | Close PR, re-dispatch on fresh base                |
| PR got CHANGES_REQUESTED          | Read review comments, decide: fix or re-dispatch   |
| Task bigger than expected         | Decompose further, add work items                  |
| Dependency discovered             | Add depends_on, mark dependent as blocked          |
| Academic integrity concern        | Set task status to `needs_review`, do not dispatch |

### INTEGRATE

1. Verify PR is clean (CI green, approved, no conflicts)
2. Merge: `gh pr merge <N> --squash --delete-branch`
3. Sync mirrors if available: `polecat sync`
4. Update work item: status → done
5. Check if this unblocks other work items → move to ready

### COMPLETE

All work items done:

1. Update parent task status
2. Run knowledge capture ([[knowledge-capture]])
3. File follow-up tasks for out-of-scope discoveries
4. Final checkpoint with summary

## Holding Work for Human Judgment

When a task requires human judgment before work can proceed (academic integrity
concern, methodology question, scope ambiguity), set the **PKB task status** to
`needs_review` and the work items table status to `needs_decision`.

This is an enforced gate. Agents cannot claim tasks in `needs_review` status,
so the work is held without relying on anyone checking a body note.

```bash
# Hold a task for human decision
pkb update <task-id> --status needs_review --note "Reason: <why human input needed>"
```

Update the work items table status to `needs_decision`. The supervisor will
skip these items during DISPATCH until the human resolves them by changing
the status back to `active` (ready to dispatch).

## State Recovery

All supervisor state lives in the epic task file body. If the file is lost
or corrupted, recover from the nearest available source:

1. **Git log**: `git log --all -- <path-to-epic-task>` — prior versions of the
   task file are in git history.
2. **PKB search**: `pkb search "<epic title>"` — prior snapshots of the task
   may be indexed.
3. **Open PRs**: `gh pr list --search "head:polecat/"` — dispatched work items
   leave PRs as evidence.
4. **Child task status**: Query PKB for tasks with `parent: <epic-id>` to
   reconstruct the work items table.

Reconstruct the `## Supervisor State` block from these sources and checkpoint
before resuming.

## Concurrency

### Multiple Supervisors

**One epic = one supervisor session.** Running two supervisors on the same
epic concurrently is unsafe. Markdown table updates have no transaction
isolation — two supervisors can both read a task as `ready`, both dispatch it,
and the last-write-wins checkpoint will silently corrupt the work items table.

If you suspect another supervisor is active, check the dispatch log timestamp
and git log before acting. Use a session lock file (`epic-<id>.lock`) as a
coordination signal if concurrent sessions are likely.

When sessions do overlap, git is the backstop:

- Pull before acting. Push after checkpointing.
- If push fails → pull, re-orient, adjust.
- Idempotent actions mean the worst case is wasted work, not corruption.

### Worker Coordination

Workers coordinate through atomic task claiming (polecat CLI), not through
the supervisor. The supervisor doesn't prevent double-claiming — that's the
worker's job.

## Invocation Patterns

```bash
# Manual (current session)
# Just invoke /supervisor with the epic task ID

# Periodic (in-session loop)
/loop 30m /supervisor task-XXXXXXXX

# Scheduled task (survives session restarts)
# Use create_scheduled_task MCP tool

# Cron (via repo-sync or GitHub Actions)
pkb get task-XXXXXXXX | claude -p "You are the supervisor. Orient and act."
```

## Anti-Patterns

- **Tight polling loops**: Don't `watch` or `sleep` between checks. Check once,
  checkpoint, exit. Come back later.
- **Environment-specific state**: Don't write paths, PIDs, or container IDs into
  the task file. They won't be valid next invocation.
- **Silent failures**: If something breaks, write it into the task file. The next
  supervisor instance needs to know.
- **Delegating judgment**: If a work item involves academic output, methodology,
  or citations — set task status to `needs_review`. Never auto-merge.
