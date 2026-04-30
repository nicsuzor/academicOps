# Worker Dispatch

Supervisor dispatches individual tasks to workers. This phase transforms
approved decomposition into execution — one task at a time.

> **`polecat` not on PATH?** Dispatch examples below use bare `polecat`. In
> non-interactive shells (Bash tool, cron, CI, headless agent), the
> `polecat`/`pc` zsh alias is not loaded. Substitute the canonical form:
> `uv run --project $AOPS $AOPS/polecat/cli.py <args>`. See
> [[../SKILL.md#dispatch]] for the global note.

---

## Worker Types and Capabilities

> **Configuration**: See [[WORKERS.md]] for current worker types, capabilities,
> cost/speed profiles, and capacity limits. Modify that file to add workers or
> change profiles without editing this skill.

Load worker registry before dispatch. Each worker has:

- **Capabilities**: What task types it can handle
- **Cost/Speed**: Resource trade-offs (1-5 scale)
- **Max Concurrent**: Capacity limit for parallel dispatch
- **Best For**: Recommended use cases

---

## Mandatory Pre-Dispatch Gates

Two gates MUST pass before any `polecat run` invocation. They are
deterministic checks, not prose conditionals — the supervisor evaluates each
explicitly and records the verdict in the task body's Activity Log.

### Gate 1: Host Check (issue #598)

Compare `hostname -s` against the polecat host registry. If the supervisor
is NOT running on a polecat host, it MUST switch to SSH+tmux remote dispatch
(see "Remote Dispatch via SSH + tmux" below). No silent local fallback.

```bash
HOST=$(hostname -s)
POLECAT_HOSTS="${POLECAT_HOSTS:-nicwin}"   # WORKERS.md once #616 lands

case " $POLECAT_HOSTS " in
  *" $HOST "*) echo "host-check: $HOST is a polecat host — local dispatch OK" ;;
  *)
    echo "host-check: $HOST NOT in [$POLECAT_HOSTS] — must use SSH+tmux"
    # supervisor halts local dispatch and switches to the remote path
    ;;
esac
```

The 2026-04 dogfood incident behind issue #598: the supervisor read
"use SSH+tmux when on a different host" as advice, dispatched
`polecat run` locally on macOS anyway, and lost 3 of 4 tasks to
`ConnectionRefusedError` because the local host could not reach PKB.

### Gate 2: PKB Readiness Probe (issue #600)

Run `polecat ping-pkb` on the host that will execute `polecat run`. The
probe exercises the same `PkbClient._initialize()` path the worker hits at
boot. If it fails, the worker will crash with `ConnectionRefusedError` and
the task will be lost. Refuse to dispatch.

```bash
# Local dispatch — probe locally
polecat ping-pkb || { echo "PKB unreachable; refusing dispatch"; exit 5; }

# Remote dispatch — probe ON the target host
ssh "$TARGET_HOST" "zsh -i -c 'polecat ping-pkb'" \
  || { echo "PKB unreachable from $TARGET_HOST; refusing dispatch"; exit 5; }
```

`polecat ping-pkb` exit codes:

| Code | Meaning                                                        |
| ---- | -------------------------------------------------------------- |
| 0    | PKB reachable, MCP handshake + low-cost call succeeded         |
| 4    | `PKB_MCP_URL` is unset — fix the env on the target host        |
| 5    | Reachable check failed — fix the URL or expose PKB to the host |

Record the gate result before firing the worker:

```
[ISO timestamp] host=nicwin: ping-pkb OK → dispatching task-abc
[ISO timestamp] host=nicwin: ping-pkb FAILED (exit 5) → halting; filing reachability subtask
```

## Pre-Dispatch Validation (MANDATORY)

Before dispatching ANY task to a worker, the supervisor must validate:

1. **PKB consistency**: The task exists, with matching content, in all three places the worker's bootstrap will consult:
   - Local disk (`ls $ACA_DATA/tasks/task-<id>*`)
   - Local CLI index (`pkb show task-<id>`)
   - Remote PKB MCP (`get_task` via MCP)

   If MCP returns `Task not found` while local disk and `pkb show` see it, work through three failure modes (NONE of them are vector reindex — reindex affects only `pkb search` / semantic queries, never CRUD):

   1. **Local push not landed.** Check `cd $ACA_DATA && git status && git log origin/main..HEAD`. If you're ahead of origin or have uncommitted changes touching the task file, push.
   2. **Remote pull cron stalled.** If the remote (the MCP host) has an unresolved sync conflict its pull cron silently halts. Requires manual resolution on the remote host — escalate to the user.
   3. **MCP server's in-memory index is stale.** The PKB MCP server is a long-running daemon with an in-memory index that does NOT auto-refresh on file changes. The file is on disk on the MCP host, the local `pkb` CLI on the same host can read it, but the MCP server doesn't know about it. Diagnostic: ask the user to confirm all hosts are at the same commit. If yes, this is the cause. Fix: user restarts the MCP container/process; no in-process refresh signal exists.

   Triage cheapest first: check (1) yourself, ask the user about (2), and only escalate (3) after the user confirms hosts are in sync. Polecat will otherwise claim the task, fail the MCP lookup, and exit leaving the task stuck in `in_progress` with no worktree.

2. **Target currency**: Are the files/modules the task will touch still current? Check for:
   - Deprecated code (superseded by another implementation, possibly in a different repo)
   - Files that no longer exist on the default branch
   - Components that have been rewritten or moved

3. **Repo correctness**: Does the task belong in this repository? Check the task body and AC for references to other repos. If the task's deliverable lives elsewhere, redirect it — don't dispatch.

4. **AC implementability**: Can the acceptance criteria be met with the current codebase? If AC references APIs, tools, or patterns that no longer exist, the task needs updating before dispatch.

**If validation fails**: Update the task with findings, set status to `blocked`, and skip it. **Always leave a loose thread**: ensure a follow-up task is filed to resolve the blocker. Do NOT dispatch tasks that will produce wasted work.

**Recovery from a stuck claim**: If a polecat claimed a task but exited before spawning a worktree (no entry in `polecat list`, no directory under `$POLECAT_HOME/worktrees/`, but task shows `status: in_progress` with `assignee: polecat`): run `polecat reset-stalled --hours 0 --force`, then re-dispatch once pre-dispatch validation passes.

**Why this matters**: Without runtime hydration (gate is off), this pre-dispatch check is the last opportunity to catch tasks aimed at deprecated code. The 2026-03-22 dogfood run lost a full worker cycle to a task targeting superseded Python files (GH #224). The 2026-04-20 dogfood run lost a claim cycle to MCP/disk divergence.

## Critic Gate for High-Blast-Radius Tasks

Some tasks carry risk of irreversible harm: OTA firmware updates, production
deployments, data migrations, file deletions at scale, uploads to external
systems. These require independent review of the task spec BEFORE dispatch —
the entity that executes must not be the same entity that decides whether
to execute.

### When the Critic Gate Applies

A task requires critic-gated dispatch if ANY of:

- Task is tagged `high-risk`, `irreversible`, `production`, or `destructive`
- Task body mentions keywords like: OTA, flash, deploy, migrate, delete (at scale), upload to external system — these are **heuristic indicators**, not an exhaustive list
- Task modifies infrastructure (CI/CD workflows, deployment configs, DNS)
- Task targets a remote/physical system where failure requires physical intervention to recover
- **Supervisor judgment** (authoritative): the action closes a recovery path, affects systems beyond version control, or has blast radius disproportionate to the task scope

Supervisor judgment is the primary trigger. Tag matching and keyword heuristics are a defense-in-depth safety net for tasks that weren't tagged during decomposition — they catch what judgment might miss, but they don't replace it.

### Gate Protocol

1. **Prepare dispatch review context**:

   ```markdown
   # Dispatch Review: <task-id>

   ## Task Spec

   [Full task body including AC]

   ## Target State

   [Current state of files/systems the task will modify — verified, not inferred]

   ## Blast Radius

   - What changes: [files, systems, devices]
   - Reversibility: [automatic | manual-remote | manual-physical | irreversible]
   - Failure impact: [what happens if the task goes wrong]
   - Recovery paths before action: [list every way to access/fix the target]
   - Recovery paths after action (if it fails): [which paths survive?]

   ## Rollback Plan

   [See below — required for all critic-gated tasks]
   ```

2. **Invoke Pauli** (mandatory for all critic-gated tasks):

   Use the `aops-core:pauli` agent with the dispatch review context. Focus:
   - Is the task spec complete enough to execute safely?
   - Are preconditions verified from evidence, not inferred?
   - Does the action close any recovery path?
   - Are edge cases handled?

   Verdict: `SAFE_TO_DISPATCH` / `NEEDS_REFINEMENT` / `DO_NOT_DISPATCH`

   **Batch review**: When an epic has multiple `high-risk` tasks that share
   context (same target system, same blast radius class), batch them into a
   single Pauli invocation. Include all task specs in one dispatch review
   context. This avoids redundant reviews while maintaining coverage.

3. **Gate decision**:

   | Pauli Verdict    | Result                                               |
   | ---------------- | ---------------------------------------------------- |
   | SAFE_TO_DISPATCH | Dispatch normally                                    |
   | NEEDS_REFINEMENT | Return to task spec refinement, do NOT dispatch      |
   | DO_NOT_DISPATCH  | Set task to `review`, escalate to human with context |

4. **Record gate result** in the task body (the task file is the only state store — see SKILL.md design principles):
   ```
   [timestamp] CRITIC GATE: Pauli: SAFE_TO_DISPATCH → dispatching
   [timestamp] CRITIC GATE: Pauli: DO_NOT_DISPATCH (closes only network ingress) → review
   ```

5. **Human override** (for `DO_NOT_DISPATCH` or `NEEDS_REFINEMENT` verdicts):

   The critic gate is a safety check, not a permanent block. If a human
   determines the task is safe despite the verdict, they can override:

   - Set the task status back to `queued` in PKB
   - Append a note: `CRITIC OVERRIDE: <rationale for why this is safe>`
   - The supervisor dispatches on the next cycle without re-invoking the gate

   The override rationale is recorded in the task body for audit. The
   supervisor does NOT override on its own — only humans can.

### Rollback Plan Requirements

Every critic-gated task MUST include a Rollback Plan in the task body before
dispatch. The supervisor adds this during DECOMPOSE or before DISPATCH.

**Required format** (appended to task body):

```markdown
## Rollback Plan

**Reversibility**: [automatic | manual-remote | manual-physical | irreversible]

### Steps to Revert

1. [Specific command or action to undo the change]
2. [Verification that revert succeeded]

### Preconditions for Safe Rollback

- [What must be true for rollback to work]
- [Time window: must revert within X minutes/hours?]

### If Rollback Fails

- [Contingency if revert steps don't work]
- [Escalation path]
```

**Dispatch rules based on reversibility**:

| Reversibility   | Dispatch allowed? | Additional requirement                          |
| --------------- | ----------------- | ----------------------------------------------- |
| automatic       | Yes               | Rollback steps must be executable by agent      |
| manual-remote   | Yes               | Human must be reachable (not overnight/weekend) |
| manual-physical | NO — refuse       | Escalate to human with full context             |
| irreversible    | NO — refuse       | Set `review`, present alternatives to human     |

**Refusal grounds** (from issue #454 — any one is sufficient to refuse):

- Rollback requires physical intervention
- Action closes the only recovery path
- Preconditions are inferred, not verified from evidence
- Success criteria are vague or untestable
- Failure detection has no out-of-band evidence path

**Rollback plan validation**: Before accepting a rollback plan, check: does
every external system modified by the task have a corresponding revert step?
If the rollback plan only addresses version control (e.g., `git revert`) but
the task modifies external systems, the plan is incomplete. Git revert undoes
the code change — it doesn't un-flash a device or un-deploy a service.

---

## Halt-on-Infeasibility Gate

Worker type, project, and repo are explicit user parameters with trust,
cost, audit, and identity semantics. They are **hard requirements**.
Adaptation in dispatch applies to _how_ a requested worker is invoked
(local CLI vs SSH+tmux vs workflow_dispatch runner) — **never** to _which_
worker is invoked. Silent substitution of worker type is forbidden.

### When the gate fires

Before dispatch, the supervisor must verify it can satisfy every explicit
dispatch parameter on the request. The gate fires whenever **any** of the
following cannot be satisfied in the current environment:

- **Worker type**: the requested worker family (Claude polecat, Gemini polecat,
  Jules, etc.) cannot be invoked through any transport this environment
  supports.
- **Project**: the requested project context cannot be loaded (`$ACA_DATA`
  missing, project alias unresolved).
- **Repo**: the target repository is not reachable (no clone, no auth, no
  SSH path to a host that has it).
- **Transport**: every transport that _could_ invoke the requested worker
  has failed environment discovery (e.g. `polecat` not on PATH AND no
  SSH+tmux host reachable AND no `workflow_dispatch` runner available).

A failure on a single transport is **not** infeasibility — try the others
first. Infeasibility means _no_ path can deliver the requested worker.

### Protocol

1. **Halt.** Do not dispatch. Do not substitute. Do not "adapt" to a different
   worker type.

2. **Produce a dispatch infeasibility report** in the epic task body, under a
   `## Dispatch Infeasibility Report` heading:

   ```markdown
   ## Dispatch Infeasibility Report

   **Timestamp**: [ISO timestamp]
   **Environment**: [host / container identifier]

   ### Requested

   - Worker type: [e.g. gemini polecat]
   - Project: [project alias]
   - Repo: [owner/repo]

   ### Missing / Failed Discovery

   - [Specific check that failed, e.g. `polecat` not on PATH]
   - [Each transport tried and why it failed: local / SSH+tmux / runner]

   ### Substitutes Available (DO NOT auto-pick)

   | Substitute                   | Cost delta | Trust delta | Audit delta | Notes |
   | ---------------------------- | ---------- | ----------- | ----------- | ----- |
   | claude polecat               | ...        | ...         | ...         | ...   |
   | claude general-purpose Agent | ...        | ...         | ...         | ...   |

   ### Decision Required

   Substitute with one of the above, fix the environment, or abort?
   ```

3. **Interactive session** — surface the report to the user and wait for an
   explicit affirmative response before dispatching anything. A bare "ok"
   or "go ahead" is sufficient; silence or ambiguity is not. Record the
   user's choice in the task body before dispatch:

   ```
   [timestamp] DISPATCH SUBSTITUTION APPROVED by user: gemini polecat → claude polecat
   ```

4. **Autonomous session** (cron, headless, no interactive user) — do **not**
   substitute. Set the epic's status to `needs_decision`, leave the report
   in the epic body, and exit. The next interactive supervisor invocation
   picks it up.

5. **Never** invoke a substitute worker without an explicit approval line in
   the task body. The presence of an infeasibility report without an approval
   line means dispatch is still blocked.

### What the gate is not

- Not a critic gate (that handles blast radius, not parameter feasibility).
- Not a pre-dispatch validation (that handles task currency, not transport).
- Not a fallback selector — fallback among **transports** for the _same_
  worker is fine and expected; fallback to a _different worker type_ is
  prohibited without user approval.

---

## Worker Selection

**Step 1: Assess Task Requirements**

Extract required capabilities from task metadata:

```markdown
## Task Analysis for Worker Selection

**Task**: <task-id>
**Tags**: [list from task.tags]
**Complexity**: <task.complexity or inferred>
**Files affected**: <count from decomposition>
**Estimated effort**: <from decomposition>

### Required Capabilities

[Map task characteristics to capabilities]

### Constraints

- Deadline pressure: [yes/no]
- Budget sensitivity: [yes/no]
- Quality criticality: [low/medium/high]
```

**Step 2: Apply Selection Rules**

> **Configuration**: Selection rules (tag routing, complexity routing, heuristic
> thresholds) are defined in [[WORKERS.md]]. Modify that file to change routing
> behavior.

Apply rules in priority order:

1. **Complexity routing**: Match task.complexity against Complexity Routing table
2. **Tag routing**: Check task.tags against High-Stakes and Bulk tag lists
3. **Heuristic thresholds**: Apply file count and effort rules
4. **Default**: Use configured default worker (typically claude for safety)

**Step 3: Check Capacity**

Before dispatch, verify worker availability against limits in [[WORKERS.md]].

1. Load Max Concurrent for selected worker type from WORKERS.md
2. Count in_progress tasks assigned to that worker type
3. If at capacity:
   - Try fallback worker if task capabilities permit
   - Otherwise queue task for later dispatch

---

## Dispatch Protocol

**Single Task Dispatch**:

```bash
# Claude worker for a specific task (by task ID)
polecat run -t <task-id> -p <project>

# Gemini worker for a specific task
polecat run -t <task-id> -p <project> --gemini

# Claude worker claiming next ready task from queue
polecat run -p <project>

# Gemini worker claiming next ready task from queue
polecat run -g -p <project>

# Jules (asynchronous, runs on Google infrastructure)
aops task <task-id> | jules new --repo <owner>/<repo>
```

**Jules Dispatch Notes**:

- Pipe task context from `aops task` into `jules new` — this gives Jules the full task body, relationships, and acceptance criteria
- Jules sessions are asynchronous — returns a session URL immediately
- Check status: `jules remote list --session`
- One session per task
- Sessions show "Completed" when coding is done but require human approval on Jules web UI before branches are pushed and PRs are created

### Coordinated Branch Dispatch

For tightly coupled subtasks (3+ tasks modifying overlapping files or
contributing to a single logical feature), the supervisor can coordinate
multiple polecats onto a shared feature branch instead of individual
`polecat/<task-id>` branches.

**When to use**: Decide during DECOMPOSE, not DISPATCH. Use when:

- 3+ subtasks modify the same files
- Tasks contribute to a single logical feature that makes more sense as one PR
- Individual PRs would create a chain of merge conflicts

**Setup** (supervisor does this before dispatching any worker):

1. Create feature branch: `git fetch origin && git checkout -b feature/<epic-id> origin/main && git push -u origin feature/<epic-id>`
2. Create draft PR: `gh pr create --draft --title "<epic title>" --body "<summary>\n\nTracks <epic-id>" --base main --head feature/<epic-id>`
3. Record in the epic's Supervisor State block: `**Feature Branch**: feature/<epic-id> (PR #NNN, draft)`

**Worker instructions** (add to each subtask body):

```markdown
## Branch Instructions

Push commits to branch `feature/<epic-id>` (already exists on remote).
Do NOT create a new branch. Pull before pushing:
git pull origin feature/<epic-id>
Do NOT file a separate PR — work contributes to draft PR #NNN.
Call `mcp__pkb__release_task` with branch="feature/<epic-id>" when done.
```

**Sequencing**: Dispatch one polecat at a time to the shared branch.
Record "branch lock: task-abc" in the epic task body. Next polecat dispatches
only after the current one releases its task.

**Completion**: When all subtasks are done, mark draft PR ready:
`gh pr ready <PR-number>`. The normal review pipeline takes over.

**Fallback**: If a polecat fails to push (conflict, etc.), fall back to
individual-branch mode for remaining tasks. Merge those branches into the
feature branch manually before marking the PR ready.

**Deadlock prevention**: If the branch-locked worker hangs (no `release_task`,
no PR activity), `polecat reset-stalled --hours 4` will reset it to `queued`,
implicitly releasing the branch lock. The supervisor dispatches the next
waiting `queued` sibling on its next ORIENT pass. If coordinated dispatch is
producing repeated conflicts or failures, abort coordinated mode: dispatch
remaining tasks on individual `polecat/<task-id>` branches and merge them into
the feature branch before marking the PR ready.

---

**Dispatch Recording** (in epic task body, BEFORE firing the worker):

Update the work items table with status `in_progress`, the worker type, and
the dispatch timestamp. The supervisor checks status on next orient phase.

```markdown
### Activity Log

[ISO timestamp] [environment]: Dispatched task-abc to claude via polecat run
```

---

## Post-Dispatch

After dispatch, update the work items table in the epic task body. The
supervisor checks status on its next invocation (orient phase) — it does
not actively poll.

**Stale task cleanup** (periodic, not real-time):

```bash
# Reset tasks stuck in_progress for >4 hours (cron or manual)
polecat reset-stalled --hours 4 --dry-run
polecat reset-stalled --hours 4
```

This is a janitorial operation. Run it periodically (e.g., via `stale-check`
cron hook) to clean up crashed workers.

**Expected worker communication**: Workers call `mcp__pkb__release_task` upon
finishing, which updates task status and appends structured notes to the task
body. The supervisor should not assume silence means success — always verify
via PKB query and GitHub PR check during MONITOR phase.

**Worker failures surface as missing PRs.** If a worker fails, no PR appears.
The task stays `in_progress` until the stale-check resets it to `queued` for
the next dispatch cycle.

**Known issue: auto-finish override loop.** When a task was already completed
by another worker (e.g., Jules fixed it), polecat auto-finish detects zero
changes and resets to queued, creating an infinite retry loop. Workaround:
mark the task `done` manually. See `aops-fdc9d0e2`.

---

## Remote Dispatch via SSH + tmux

When the supervisor is running on a different machine from the polecat host
(e.g., running `/supervisor` on a laptop while polecats execute on a remote
host), use SSH + tmux so workers survive network interruptions (lid close,
VPN drop, etc.).

### Environment Discovery

Before dispatching, verify the remote machine is ready. **All four checks
must pass** — including the PKB readiness probe ON the target host.

```bash
# 1. SSH connectivity
ssh -o ConnectTimeout=10 TARGET_HOST "echo connected"

# 2. Polecat availability (alias loaded in interactive zsh)
ssh TARGET_HOST "zsh -i -c 'polecat --help'" 2>&1

# 3. tmux availability
ssh TARGET_HOST "which tmux"

# 4. PKB reachability FROM the target host (issue #600 gate)
ssh TARGET_HOST "zsh -i -c 'polecat ping-pkb'"
```

If any check fails, report the failure and stop. Do not improvise alternatives.

The fourth check is the critical one for the 2026-04 incident behind
issue #600 — SSH + tmux + polecat all worked, but `PkbClient._initialize()` crashed
with `ConnectionRefusedError` because the PKB MCP/HTTP endpoint was not
reachable from `nicwin`'s WSL2 namespace. Probing first turns a worker
crash into a supervisor halt with a clear remediation path.

**Reachability pre-check for incident tasks**: If a task requires the worker
to SSH into a _third_ machine (e.g., `services-new` from `TARGET_HOST`), verify
that hop before dispatch:

```bash
ssh TARGET_HOST "ssh -o ConnectTimeout=5 REMOTE_TARGET 'echo reachable'" 2>&1
```

If unreachable, set the task to `blocked` with the reason and skip it. Do not
dispatch a worker that cannot reach its target.

### Dispatch

For each task, SSH into the target host and create a named tmux session:

```bash
ssh TARGET_HOST "tmux new-session -d -s 'polecat-TASKID' 'zsh -i -c \"polecat run -t TASKID -p PROJECT\"'"
```

The `zsh -i -c` wrapping ensures the polecat alias is available regardless of
tmux's default-shell setting.

**Verify sessions are running** after dispatch:

```bash
ssh TARGET_HOST "tmux has-session -t 'polecat-TASKID' && echo \"Session 'polecat-TASKID' is running\""
```

Session existence is the primary verification signal. A synchronous headless
supervisor cannot poll pane output — accept session existence as sufficient.

**Append a dispatch log** to each task body via PKB, then **read back** to
confirm the append landed (MCP append tools can silently fail):

```
[ISO timestamp] TARGET_HOST: Dispatched to polecat via SSH+tmux session 'polecat-TASKID'
```

### Ground Rules

1. **Do NOT monitor or poll.** Dispatch, verify sessions started, and report.
2. **If SSH fails**, report immediately. Retry once at most.
3. **If tmux session already exists** with that name, check if it's running a
   polecat. If yes, report and skip. Do not create a duplicate.
4. **Do NOT modify task status.** Polecat handles status transitions.
5. **Critic gate still applies.** HIGH-risk tasks must pass the gate (above)
   before SSH dispatch. The gate runs locally; dispatch is the last step.
6. **Report operational observations.** Repo drift, required rebases, stale
   mirrors, unexpected startup errors — include these in the dispatch report.

### Report Format

```markdown
## Remote Dispatch Report — TARGET_HOST

### [task-id] ([short title])

- **Critic gate**: [verdict + 1-sentence reasoning] (or N/A for normal-risk)
- **Reachability**: [verified / not applicable / FAILED]
- **tmux session**: [created / already_existed / failed]
- **Session verified**: [yes — via tmux has-session (confirmed by success message)]
- **PKB log confirmed**: [yes — read-back verified / no — append may have failed]

### Environment Observations

[Anything noteworthy: repo drift, rebase required, stale state, access issues]
```

### Example

```bash
# 0. Host check (run locally first — issue #598)
HOST=$(hostname -s); POLECAT_HOSTS="${POLECAT_HOSTS:-nicwin}"
TARGET_HOST="${POLECAT_HOSTS%% *}"   # first host in the list
case " $POLECAT_HOSTS " in *" $HOST "*) TARGET_HOST="$HOST" ;; esac

# 1. Verify SSH + polecat + tmux + PKB reachability ON nicwin
ssh -o ConnectTimeout=10 "$TARGET_HOST" "echo connected" || exit 1
ssh "$TARGET_HOST" "zsh -i -c 'polecat --help >/dev/null'" || exit 1
ssh "$TARGET_HOST" "which tmux >/dev/null" || exit 1
ssh "$TARGET_HOST" "zsh -i -c 'polecat ping-pkb'" || {
  echo "PKB unreachable from $TARGET_HOST — file a reachability subtask"
  exit 5
}

# 2. Dispatch via tmux so the worker survives network interruptions
ssh "$TARGET_HOST" "tmux new-session -d -s 'polecat-task-abc12345' \
  'zsh -i -c \"polecat run -t task-abc12345 -p brain\"'"

# 3. Verify the session is running
ssh "$TARGET_HOST" "tmux has-session -t 'polecat-task-abc12345' \
  && echo 'Session polecat-task-abc12345 is running'"
```

---

## Parallel Execution Coordination

Workers coordinate through the task system, not through the supervisor:

**Dependency Respect**:

- Workers only claim tasks with satisfied `depends_on`
- Polecat CLI `claim_next_task()` in `manager.py` enforces this via atomic file locking
- No supervisor verification needed at runtime

**Conflict Prevention**:

- Each polecat worker operates in isolated worktree
- No two workers touch same task (atomic claiming)
- Jules sessions are isolated by design (separate Google infrastructure)
- If decomposition reveals shared files:
  - Add explicit `depends_on` between subtasks before dispatch

---

## Parallel Dispatch into a Shared Repo

When dispatching multiple general-purpose subagents (not polecat workers) at
once into the same underlying repo — e.g. via the Task tool with
`isolation: worktree` — the nominal isolation is **not sufficient**. Agents
still race on the shared checkout: one `git checkout -b` while another is
mid-commit lands commits on the wrong branch. Every parallel dispatch must
follow this pattern.

### Mandatory per-agent setup

Each agent's brief MUST instruct it to create its own private worktree
**before** any work, and remove it at the end:

```bash
git fetch origin
git worktree add /tmp/wt-<task-id> -b <branch-name> origin/<base-branch>
cd /tmp/wt-<task-id>
# ... do work ...
# on exit: git worktree remove /tmp/wt-<task-id>
```

Never let two agents share a checkout. `isolation: worktree` alone is not
enough — make the private worktree explicit in the brief.

### Mandatory push pattern

`branch.autoSetupMerge=always` is common on aops machines, so
`git checkout -b feature origin/main` sets the new branch's upstream to
`origin/main`. A plain `git push -u origin <branch>` then tries to push to
`refs/heads/main` and is rejected by branch protection. Always use an
explicit refspec:

```bash
git push -u origin <branch>:<branch>
```

### No-touch lists

When dispatching N parallel agents into one repo, compute each agent's
**no-touch list** = every file or path any other agent is expected to touch,
plus any in-flight dirty changes. Include the list verbatim in the brief.
Without it, agents improvise (stash unrelated changes, edit adjacent files)
and integration becomes unrecoverable.

### Required report shape from each agent

Every parallel-dispatched agent must return a structured report as its final
deliverable. The integration step depends on this shape — free-form prose
makes bundled merges unsafe:

```markdown
- **Branch**: <branch-name>
- **Commits**: <SHA1>, <SHA2>, ...
- **Files touched**: <list>
- **Files NOT touched** (from no-touch list): confirmed
- **Deviations from brief**: <none | list>
- **Deferred verification**: <none | list of unrunnable tests with reproduce steps>
```

The supervisor uses this directly to assemble a bundle branch and to file
follow-up verification tasks (see [[supervision-loop]] MONITOR).
