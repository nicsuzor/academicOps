# Worker Dispatch

The pre-dispatch gates and dispatch mechanics that **pauli** runs during preflight. The main supervisor agent does not invoke these inline — pauli reads this file and produces a structured `dispatch` / `halt` verdict.

> **`polecat` not on PATH?** Examples below use bare `polecat`. In non-interactive shells (Bash tool, cron, CI, headless agent), the alias is not loaded. Substitute: `uv run --project $AOPS $AOPS/polecat/cli.py <args>`.
>
> **Worker registry**: see [[WORKERS.md]] for worker types, capabilities, cost/speed profiles, capacity limits, and selection rules. Pauli reads it fresh on each preflight.

## Mandatory Pre-Dispatch Gates

Three gates MUST pass before any `polecat run` invocation. Deterministic checks, not prose conditionals — pauli evaluates each explicitly and records the verdict.

### Gate 1: Host Check (issue #598)

Compare `hostname -s` against the polecat host registry. If pauli is NOT running on a polecat host, dispatch MUST switch to SSH+tmux remote dispatch (see "Remote Dispatch via SSH + tmux" below). No silent local fallback.

```bash
HOST=$(hostname -s)
POLECAT_HOSTS="${POLECAT_HOSTS:-nicwin}"

case " $POLECAT_HOSTS " in
  *" $HOST "*) echo "host-check: $HOST is a polecat host — local dispatch OK" ;;
  *)           echo "host-check: $HOST NOT in [$POLECAT_HOSTS] — must use SSH+tmux" ;;
esac
```

The 2026-04 dogfood incident behind issue #598: the supervisor read "use SSH+tmux when on a different host" as advice, dispatched `polecat run` locally on macOS anyway, and lost 3 of 4 tasks to `ConnectionRefusedError`.

### Gate 2: PKB Readiness Probe (issue #600)

Run `polecat ping-pkb` on the host that will execute `polecat run`. Probes the same `PkbClient._initialize()` path the worker hits at boot. Failure → `ConnectionRefusedError` in the worker → lost task. Refuse to dispatch.

```bash
# Local dispatch — probe locally
polecat ping-pkb || { echo "PKB unreachable; refusing dispatch"; exit 5; }

# Remote dispatch — probe ON the target host
ssh "$TARGET_HOST" "zsh -i -c 'polecat ping-pkb'" \
  || { echo "PKB unreachable from $TARGET_HOST; refusing dispatch"; exit 5; }
```

| Code | Meaning                                                        |
| ---- | -------------------------------------------------------------- |
| 0    | PKB reachable, MCP handshake + low-cost call succeeded         |
| 4    | `PKB_MCP_URL` is unset — fix the env on the target host        |
| 5    | Reachable check failed — fix the URL or expose PKB to the host |

### Gate 3: Pre-flight Confirmation Summary (task-4cea5008, aops-e2d639e2)

After Gates 1 and 2 pass, pauli MUST produce a 4-row pre-flight confirmation table and include it in its verdict. The grep below IS the row 2 evidence source.

This gate is the [Halt-on-substitute](../SKILL.md#halt-on-substitute) discipline specialised for pre-flight. Same halt protocol — set the epic to `blocked` (canonical "external dependency on a human decision"), record the report in the body, exit. No silent substitution.

| Row | Field                  | Source of truth                                                                                          | Halt-if-unknown rule                                                               |
| --- | ---------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 1   | **Task ID**            | The epic / subtask being dispatched                                                                      | Halt if no task ID resolved                                                        |
| 2   | **Source repo**        | Inferred from file paths the task names (AC, body, gate-1 named file/symbol) — NOT from `project=` alone | Halt if no file path is named, or named file does not resolve to exactly one repo  |
| 3   | **project= field**     | Task's `project:` frontmatter                                                                            | Halt if missing OR disagrees with row 2 (Polecat #3 class)                         |
| 4   | **Next link in chain** | Task this dispatch unblocks (parent's next ready child OR next subtask of same epic)                     | Halt if no next link AND epic has more than one ready descendant (orientation rot) |

**Row 2 mechanic** — pauli reads the task body and AC, extracts named files / symbols, and greps the working tree to confirm each named file resolves to exactly one repo. Bare repo names ("brain", "aops-core", "polecat") are not evidence — only files / symbols that grep can locate count for row 2. If multiple file paths are named and they resolve to different repos, that is a row 2 halt (ambiguous source).

Worked replays (the table MUST halt these — both are dogfood references):

- **Polecat #3** — frontmatter says `project: brain`; AC names a file under `aops-core/`. Row 2 grep resolves to `aops-core`; row 3 frontmatter says `brain`. Mismatch → halt at row 2/3 boundary.
- **pkb→public-PR incident** — task source files live under `$ACA_DATA/` (private PKB clone); `project=` and the implied target repo are public. Row 2 grep resolves source to the private clone; row 3 / target disagrees. Halt before any commit or push reaches a public repo.

## Pre-Dispatch Validation (PKB Consistency)

Before pauli emits a `dispatch` verdict, validate the task exists with matching content in all three places the worker's bootstrap will consult:

- Local disk (`ls $ACA_DATA/tasks/task-<id>*`)
- Local CLI index (`pkb show task-<id>`)
- Remote PKB MCP (`get_task` via MCP)

If MCP returns `Task not found` while local sees it, work through three failure modes (NONE of them are vector reindex — reindex affects only `pkb search` / semantic queries, never CRUD):

1. **Local push not landed.** Check `cd $ACA_DATA && git status && git log origin/main..HEAD`. If you're ahead of origin or have uncommitted changes touching the task file, push.
2. **Remote pull cron stalled.** If the remote (the MCP host) has an unresolved sync conflict its pull cron silently halts. Requires manual resolution on the remote host — escalate to the user.
3. **MCP server's in-memory index is stale.** The PKB MCP server is a long-running daemon with an in-memory index that does NOT auto-refresh on file changes. Ask the user to confirm all hosts are at the same commit. If yes, this is the cause. Fix: user restarts the MCP container/process; no in-process refresh signal exists.

Triage cheapest first: check (1) yourself, ask the user about (2), only escalate (3) after the user confirms hosts are in sync.

**Other validation** (target currency, repo correctness, AC implementability):

- Are the files / modules the task will touch still current? Check for deprecated code, files that no longer exist on the default branch, components rewritten or moved.
- Does the task belong in this repository? Body and AC may reference other repos; if the deliverable lives elsewhere, redirect — don't dispatch.
- Can the AC be met against the current codebase? If AC references APIs / tools / patterns that no longer exist, the task needs updating before dispatch.

If validation fails: pauli recommends filing a fix-task with the fix scope, or halting if the gap requires human direction. Always leave a loose thread.

**Recovery from a stuck claim**: if a polecat claimed a task but exited before spawning a worktree (no entry in `polecat list`, no directory under `$POLECAT_HOME/worktrees/`, but task shows `status: in_progress`): run `polecat reset-stalled --hours 0 --force`, then re-dispatch once validation passes.

## Critic Gate for High-Blast-Radius Tasks

Some tasks carry risk of irreversible harm: OTA firmware updates, production deployments, data migrations, file deletions at scale, uploads to external systems. These require independent review of the task spec BEFORE dispatch — the entity that executes must not be the same entity that decides whether to execute.

### When the gate applies

A task requires critic-gated dispatch if ANY of:

- Task is tagged `high-risk`, `irreversible`, `production`, or `destructive`
- Task body mentions: OTA, flash, deploy, migrate, delete (at scale), upload to external system — heuristic indicators, not exhaustive
- Task modifies infrastructure (CI/CD workflows, deployment configs, DNS)
- Task targets a remote/physical system where failure requires physical intervention to recover
- **Pauli judgment** (authoritative): action closes a recovery path, affects systems beyond version control, or has blast radius disproportionate to scope

Pauli judgment is the primary trigger; tag matching and keyword heuristics are defense-in-depth.

### Gate Protocol

1. **Prepare dispatch review context** (task spec, target state from evidence, blast radius, rollback plan).
2. **Invoke critic** — pauli already IS the critic; it self-applies the questions: is the spec complete? Are preconditions verified from evidence? Does the action close any recovery path? Verdict: `SAFE_TO_DISPATCH` / `NEEDS_REFINEMENT` / `DO_NOT_DISPATCH`.
3. **Gate decision**:

| Verdict          | Result                                                       |
| ---------------- | ------------------------------------------------------------ |
| SAFE_TO_DISPATCH | Pauli recommends dispatch                                    |
| NEEDS_REFINEMENT | Pauli recommends filing a fix-task for refinement            |
| DO_NOT_DISPATCH  | Pauli recommends halting with status `review` and the reason |

4. **Record gate result** in the task body's Pattern Memory.
5. **Human override**: humans can set the task back to `queued` and append `CRITIC OVERRIDE: <rationale>` — pauli dispatches on the next preflight without re-invoking the gate.

### Rollback Plan Requirements

Every critic-gated task MUST include a Rollback Plan in the task body before dispatch:

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

| Reversibility   | Dispatch allowed? | Additional requirement                          |
| --------------- | ----------------- | ----------------------------------------------- |
| automatic       | Yes               | Rollback steps must be executable by agent      |
| manual-remote   | Yes               | Human must be reachable (not overnight/weekend) |
| manual-physical | NO — refuse       | Escalate to human with full context             |
| irreversible    | NO — refuse       | Set `review`, present alternatives to human     |

**Refusal grounds** (from issue #454 — any one is sufficient): rollback requires physical intervention; action closes the only recovery path; preconditions are inferred not verified; success criteria are vague or untestable; failure detection has no out-of-band evidence path.

If the rollback plan only addresses version control (e.g., `git revert`) but the task modifies external systems, the plan is incomplete — git revert undoes the code change, it doesn't un-flash a device or un-deploy a service.

## Halt-on-Infeasibility Gate

Worker type, project, and repo are explicit user parameters with trust, cost, audit, and identity semantics. They are **hard requirements**. Adaptation in dispatch applies to _how_ a requested worker is invoked (local CLI vs SSH+tmux vs `workflow_dispatch` runner) — **never** to _which_ worker is invoked. Silent substitution of worker type is forbidden.

### When the gate fires

The gate fires whenever **any** of the following cannot be satisfied:

- **Worker type**: the requested worker family cannot be invoked through any transport this environment supports.
- **Project**: the requested project context cannot be loaded (`$ACA_DATA` missing, project alias unresolved).
- **Repo**: the target repository is not reachable (no clone, no auth, no SSH path to a host that has it).
- **Transport**: every transport that _could_ invoke the requested worker has failed environment discovery.

A failure on a single transport is **not** infeasibility — try the others first.

### Protocol

1. **Equip or halt.** If the failure is a missing tool or permission gap on a transport that _could_ work, **do not halt.** Pauli recommends filing a fix-task to equip the host (e.g., "install tmux on nicwin", "fix PKB_MCP_URL on target"). Re-dispatch is a separate action in the next supervisor tick after the fix-task lands — pauli does not bundle both into a single recommendation.
2. **Halt on infeasibility.** If the worker type, project, or repo is fundamentally unreachable or unsupported, halt. Do not substitute. Do not "adapt" to a different worker type.
3. **Produce a dispatch infeasibility report** in the epic body under `## Dispatch Infeasibility Report` — Requested (worker, project, repo), Missing / Failed Discovery (each transport tried), Substitutes Available (cost / trust / audit deltas — DO NOT auto-pick).
4. **Interactive session**: surface the report; wait for explicit affirmative before dispatching anything. A bare "ok" is sufficient; silence is not. Record the user's choice before dispatch.
5. **Autonomous (loop) session**: do **not** substitute. Set the epic to `needs_decision`, leave the report in the body, exit. The next interactive supervisor invocation picks it up.
6. **Never** invoke a substitute worker without an explicit approval line in the task body.

**User intent** (aops-725a0549): "If there are gaps, we should fill them, not refuse to dispatch." A tool gap is a bug in the environment, not a reason to stop the epic.

## Dispatch Protocol

```bash
# Claude worker for a specific task
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

**Jules notes**: pipe task context from `aops task` into `jules new` — gives Jules the full task body, relationships, and AC. Sessions are async; check via `jules remote list --session`. One session per task. "Completed" sessions still require human approval on the Jules web UI before PRs appear.

### Coordinated Branch Dispatch

For tightly coupled subtasks (3+ tasks modifying overlapping files or contributing to a single logical feature), pauli may coordinate multiple polecats onto a shared feature branch instead of individual `polecat/<task-id>` branches.

**When to use** (decide during DECOMPOSE, not DISPATCH):

- 3+ subtasks modify the same files
- Tasks contribute to a single logical feature that makes more sense as one PR
- Individual PRs would create a chain of merge conflicts

**Setup** (before dispatching any worker):

1. `git fetch origin && git checkout -b feature/<epic-id> origin/main && git push -u origin feature/<epic-id>`
2. `gh pr create --draft --title "<epic title>" --body "<summary>\n\nTracks <epic-id>" --base main --head feature/<epic-id>`
3. Record in Supervisor State: `**Feature Branch**: feature/<epic-id> (PR #NNN, draft)`

**Worker instructions** (add to each subtask body):

```markdown
## Branch Instructions

Push commits to branch `feature/<epic-id>` (already exists on remote).
Do NOT create a new branch. Pull before pushing:
git pull origin feature/<epic-id>
Do NOT file a separate PR — work contributes to draft PR #NNN.
Call `mcp__pkb__release_task` with branch="feature/<epic-id>" when done.
```

**Sequencing**: dispatch one polecat at a time to the shared branch. Record "branch lock: task-abc" in the epic body. Next polecat dispatches only after the current one releases its task.

**Completion**: when all subtasks are done, mark draft PR ready: `gh pr ready <PR-number>`.

**Fallback**: if a polecat fails to push (conflict, etc.), fall back to individual-branch mode for remaining tasks. If coordinated dispatch is producing repeated conflicts, abort coordinated mode.

**Deadlock prevention**: `polecat reset-stalled --hours 4` will reset a hung branch-locked worker, implicitly releasing the lock.

## Post-Dispatch

The supervisor checks status on its next ORIENT tick — it does not actively poll.

**Stale task cleanup** (periodic, not real-time):

```bash
polecat reset-stalled --hours 4 --dry-run
polecat reset-stalled --hours 4
```

Run periodically via the `stale-check` cron hook to clean up crashed workers.

**Worker failures surface as missing PRs.** If a worker fails, no PR appears. The task stays `in_progress` until stale-check resets it to `queued` for the next dispatch cycle.

**Auto-finish override loop**: when a task was already completed by another worker (e.g., Jules fixed it), polecat auto-finish detects zero changes and resets to queued, creating an infinite retry loop. Workaround: mark the task `done` manually. See `aops-fdc9d0e2`.

## Remote Dispatch via SSH + tmux

When pauli is running on a different machine from the polecat host, use SSH + tmux so workers survive network interruptions (lid close, VPN drop).

### Environment Discovery

All four checks must pass — including the PKB readiness probe ON the target host:

```bash
# 1. SSH connectivity
ssh -o ConnectTimeout=10 TARGET_HOST "echo connected"

# 2. Polecat availability (alias loaded in interactive zsh)
ssh TARGET_HOST "zsh -i -c 'polecat --help'"

# 3. tmux availability
ssh TARGET_HOST "which tmux"

# 4. PKB reachability FROM the target host (issue #600 gate)
ssh TARGET_HOST "zsh -i -c 'polecat ping-pkb'"
```

If any fails, halt. Do not improvise alternatives.

The fourth check is the critical one for the 2026-04 incident behind issue #600 — SSH + tmux + polecat all worked, but `PkbClient._initialize()` crashed because the PKB MCP/HTTP endpoint was not reachable from `nicwin`'s WSL2 namespace. Probing first turns a worker crash into a supervisor halt with a clear remediation path.

**Reachability pre-check for incident tasks**: if a task requires the worker to SSH into a _third_ machine, verify that hop before dispatch:

```bash
ssh TARGET_HOST "ssh -o ConnectTimeout=5 REMOTE_TARGET 'echo reachable'"
```

### Dispatch

```bash
ssh TARGET_HOST "tmux new-session -d -s 'polecat-TASKID' 'zsh -i -c \"polecat run -t TASKID -p PROJECT\"'"
```

The `zsh -i -c` wrapping ensures the polecat alias is available regardless of tmux's default-shell setting.

**Verify sessions are running** after dispatch:

```bash
ssh TARGET_HOST "tmux has-session -t 'polecat-TASKID' && echo \"Session 'polecat-TASKID' is running\""
```

Session existence is the primary verification signal. A synchronous headless supervisor cannot poll pane output — accept session existence as sufficient.

**Append a dispatch log** to each task body via PKB, then **read back** to confirm the append landed (MCP append tools can silently fail).

### Ground Rules

1. **Do NOT monitor or poll.** Dispatch, verify sessions started, exit.
2. **If SSH fails**, halt immediately. Retry once at most.
3. **If tmux session already exists** with that name, check if it's running a polecat. If yes, skip — do not duplicate.
4. **Do NOT modify task status.** Polecat handles status transitions.
5. **Critic gate still applies.** HIGH-risk tasks must pass the gate before SSH dispatch.
6. **Report operational observations**: repo drift, required rebases, stale mirrors, unexpected startup errors.

## Parallel Dispatch into a Shared Repo

When dispatching multiple general-purpose subagents (not polecat workers) at once into the same underlying repo — e.g. via the Task tool with `isolation: worktree` — the nominal isolation is **not sufficient**. Agents still race on the shared checkout. Every parallel dispatch must follow this pattern.

### Mandatory per-agent setup

Each agent's brief MUST instruct it to create its own private worktree **before** any work, and remove it at the end:

```bash
git fetch origin
git worktree add /tmp/wt-<task-id> -b <branch-name> origin/<base-branch>
cd /tmp/wt-<task-id>
# ... do work ...
# on exit: git worktree remove /tmp/wt-<task-id>
```

### Mandatory push pattern

`branch.autoSetupMerge=always` is common on aops machines, so `git checkout -b feature origin/main` sets the new branch's upstream to `origin/main`. A plain `git push -u origin <branch>` then tries to push to `refs/heads/main` and is rejected by branch protection. Always use an explicit refspec:

```bash
git push -u origin <branch>:<branch>
```

### No-touch lists

When dispatching N parallel agents into one repo, compute each agent's **no-touch list** = every file or path any other agent is expected to touch, plus any in-flight dirty changes. Include the list verbatim in the brief. Without it, agents improvise and integration becomes unrecoverable.

### Required report shape

Every parallel-dispatched agent must return a structured report as its final deliverable:

```markdown
- **Branch**: <branch-name>
- **Commits**: <SHA1>, <SHA2>, ...
- **Files touched**: <list>
- **Files NOT touched** (from no-touch list): confirmed
- **Deviations from brief**: <none | list>
- **Deferred verification**: <none | list of unrunnable tests with reproduce steps>
```

The supervisor uses this directly to assemble a bundle branch and to file follow-up verification tasks.
