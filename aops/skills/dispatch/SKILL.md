---
name: dispatch
description: Dispatch and supervise the distributed execution of a task with children — routing each task unit to the right worker surface (polecat container, in-session subagent, or agent team) per the workflow pauli assembled.
---

# Epic Dispatch

This skill is the MANDATORY pathway for all polecat dispatch. Raw `polecat run` invocations outside this skill bypass dispatch doctrine and are a violation.

An epic is just a task with children — no special machinery. What governs it is the workflow pauli assembled at decomposition ("assemble" is reserved for workflows built from composable rules, not for collections of tasks).

You are a delegating supervisor in charge of delivering the entire Epic. Importantly:

- You never do the work yourself, but you are responsible for coordinating the distributed execution of an Epic task with sequenced and parallel workers.
- You must not delegate a task that is not 'queued' or that has unmet dependencies.
- You must inspect completed work: verify the return contract by side-effect (status flip + evidence + output URL on the PKB task), and ensure the pauli-specified independent review tasks execute with receipts landing in the PKB. You do NOT substitute your own quality certification for the worker's internal QA (that is the worker's business) or for independent review.
- All steps of an Epic must be worked and completed before the tasks are considered done; the whole Epic must be delivered and assessed in its entirety.
- Your responsibility ends when all an Epic's tasks are completed, partial, failed, or blocked. `partial` is a legal, expected handback — NOT a failure (see [spec-partial-work-tight-loop-delivery §4](../../../specs/polecat/spec-partial-work-tight-loop-delivery.md)). Read it as new graph information: verify its continue tasks exist and route the remainder.
- You are not responsible for the separate approval process once these tasks are completed.

## Instructions

1. Claim the parent Epic for yourself.

First, claim the Epic through the Personal Knowledge Base (PKB) tool: `claim_task`.

- This will lock and assign the epic to you, avoiding conflicts.
- This parent epic is where you will log all your work, findings, and decisions.
- Make sure you update the Epic as you go so that if you are interrupted, you will be able to resume.

2. Check all dependencies and children.

- Use `get_dependency_tree(<epic-id>)` to get the dependency tree.
- A child with an unmet `depends_on` is not dispatchable this pass.
- Eligibility = FULLY-SPEC'D + queued + dependencies met — regardless of children. A task with children may be dispatched whole to ONE worker, who owns internal sequencing/decomposition and returns ONE deliverable: evidence + an output URL written to the PKB task (contract home: [specs/enforcement/task-contract.md](../../../specs/enforcement/task-contract.md)).
- If you do route children separately, the assembled workflow must still consolidate into one deliverable for the principal — never a spray of per-child PRs reviewed individually.
- This consolidation duty is not scoped to one epic's own children: before dispatching any ready task, check for other ready tasks touching the same file/subsystem — sibling tasks in different epics count too. Bundle them into ONE worker producing ONE PR whose body lists all task ids, tested together.
- If you are blocked on a task with a dependency outside of the epic's hierarchy, you must HALT and return any work you were able to complete.

3. Sequence tasks and plan your dispatch process.

- Immediately before you dispatch a task, you must invoke the `brief` skill to compose the delegation instructions.
- DO NOT brief tasks prematurely; you should ONLY EVER brief a task that is ready to dispatch right now, in this specific iteration.
- You should do this fresh each time, even if a brief has been created before for a task, because the context may have changed.
- Use your tools to create a loop or reminder here to maintain a rolling fleet of workers.

4. Dispatch workers

At dispatch time you choose, per task, a surface (polecat container | in-session subagent | agent team) and a cadence (wait vs fire-and-forget). Cadence is a routing detail, not architecture — review shape does not depend on it. The machinery below is the polecat (fire-and-forget) instance.

**Polecat (fire-and-forget) launch.** The polecat launch command is the same everywhere — only the _transport_ to the
Docker host changes. First figure out **where you are relative to the Docker
daemon that runs polecats** (the WSL host `nicwin`), then pick the matching form.

**Resolve the polecat root** (run this first — it decides every path below):

```bash
# ${CLAUDE_PLUGIN_ROOT} is the documented Claude Code plugin-root token, but
# it is NOT reliably exposed as a live shell variable to skill-invoked bash
# commands on every client — so treat it as a first try, not the sole
# mechanism. Fall back to a filesystem search of the known per-client
# install locations (where the core plugin ships polecat/cli.py),
# then to $AOPS/aops or $AOPS for in-repo dev.
#
# Every candidate is validated to actually CONTAIN the workspace-isolation
# fix (`resolve_isolated_workspace`) before being accepted (aops_63985c64:
# an installed plugin/dist copy can silently predate that fix — a stale
# ~/.gemini/config/plugins/aops-jr build from before the fix landed was
# found on this host, matched this same find, and would have been silently
# selected and used to bind-mount the shared canonical checkout read-write
# into the container). A stale/invalid candidate is skipped, never used; if
# nothing valid is found the resolution fails closed with a clear error
# instead of silently dispatching on unvalidated code.
_pc_isolation_ok() {
  [ -f "$1/polecat/cli.py" ] && grep -q "resolve_isolated_workspace" "$1/polecat/cli.py" 2>/dev/null
}

POLECAT_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
_pc_isolation_ok "$POLECAT_ROOT" || POLECAT_ROOT=""

if [ -z "$POLECAT_ROOT" ] && [ -n "$AOPS" ] && _pc_isolation_ok "$AOPS/aops"; then
  POLECAT_ROOT="$AOPS/aops"
fi

if [ -z "$POLECAT_ROOT" ]; then
  for _pc_candidate in $(find "$HOME/.claude/plugins" "$HOME/.gemini/config/plugins" \
      -maxdepth 7 -type f -path '*aops*/polecat/cli.py' 2>/dev/null \
      | xargs -r -n1 dirname | xargs -r -n1 dirname); do
    if _pc_isolation_ok "$_pc_candidate"; then
      POLECAT_ROOT="$_pc_candidate"
      break
    fi
  done
fi

if [ -z "$POLECAT_ROOT" ] && [ -n "$AOPS" ] && _pc_isolation_ok "$AOPS"; then
  POLECAT_ROOT="$AOPS"
fi

if [ -z "$POLECAT_ROOT" ]; then
  echo "FATAL: no polecat/cli.py with workspace isolation (resolve_isolated_workspace)" \
       "found in \$CLAUDE_PLUGIN_ROOT, \$AOPS/aops, installed plugins, or \$AOPS." \
       "Refusing to dispatch on unvalidated/stale code — sync or rebuild the plugin" \
       "install before retrying." >&2
  return 1 2>/dev/null || exit 1
fi
```

**Detect your context** (run this — it decides the form for you):

```bash
# You can dispatch LOCALLY (no ssh) iff the polecat CLI is on this filesystem
# AND you can reach a Docker daemon from here.
test -f "$POLECAT_ROOT/polecat/cli.py" && docker info >/dev/null 2>&1 && echo LOCAL || echo REMOTE
```

- `LOCAL` → you are **on the WSL host**, or **inside a container with the host's
  Docker socket mounted (Docker-out-of-Docker / DooD)**. In both cases `polecat
  run` spawns _sibling_ containers on the host daemon. Dispatch directly — **do
  not** wrap in `ssh wsl`.
- `REMOTE` → you are on a different host (e.g. a cloud Cowork box). Reach the WSL
  host over SSH.

The launch command (substitute one of the three transports):

```bash
# The inner command (identical in all three contexts):
#   tmux new-session -d -s pc-<id> \
#     "uv run --project ${POLECAT_ROOT%/aops} $POLECAT_ROOT/polecat/cli.py run agy -p <project> -t <id> \
#      2>&1 | tee /tmp/pc-<id>.log"

# --- Context A: REMOTE (another host) ---
# Note: POLECAT_ROOT here resolves on the REMOTE (WSL host) side, not locally —
# the single-quoted ssh payload is deliberately unexpanded on this end. Same
# freshness-validated resolution as the LOCAL block above (aops_63985c64) —
# every candidate must actually contain `resolve_isolated_workspace`, and
# resolution fails closed (non-zero exit, no dispatch) if none do.
ssh wsl '_pc_isolation_ok() { [ -f "$1/polecat/cli.py" ] && grep -q "resolve_isolated_workspace" "$1/polecat/cli.py" 2>/dev/null; }; \
  POLECAT_ROOT="${CLAUDE_PLUGIN_ROOT:-}"; \
  _pc_isolation_ok "$POLECAT_ROOT" || POLECAT_ROOT=""; \
  if [ -z "$POLECAT_ROOT" ] && [ -n "$AOPS" ] && _pc_isolation_ok "$AOPS/aops"; then POLECAT_ROOT="$AOPS/aops"; fi; \
  if [ -z "$POLECAT_ROOT" ]; then \
    for _pc_candidate in $(find "$HOME/.claude/plugins" "$HOME/.gemini/config/plugins" -maxdepth 7 -type f -path "*aops*/polecat/cli.py" 2>/dev/null | xargs -r -n1 dirname | xargs -r -n1 dirname); do \
      if _pc_isolation_ok "$_pc_candidate"; then POLECAT_ROOT="$_pc_candidate"; break; fi; \
    done; \
  fi; \
  if [ -z "$POLECAT_ROOT" ] && [ -n "$AOPS" ] && _pc_isolation_ok "$AOPS"; then POLECAT_ROOT="$AOPS"; fi; \
  if [ -z "$POLECAT_ROOT" ]; then echo "FATAL: no polecat/cli.py with workspace isolation found on remote host — refusing to dispatch." >&2; exit 1; fi; \
  tmux new-session -d -s pc-<id> \
  "uv run --project ${POLECAT_ROOT%/aops} $POLECAT_ROOT/polecat/cli.py run agy -p <project> -t <id> \
   2>&1 | tee /tmp/pc-<id>.log"'

# --- Context B: LOCAL, on the WSL host itself ---
tmux new-session -d -s pc-<id> \
  "uv run --project ${POLECAT_ROOT%/aops} $POLECAT_ROOT/polecat/cli.py run agy -p <project> -t <id> \
   2>&1 | tee /tmp/pc-<id>.log"

# --- Context C: LOCAL, already inside a WSL Docker container (DooD) ---
# Same as B — you are already on the daemon side; the mounted docker.sock makes
# `polecat run` launch sibling containers. Do NOT ssh (there is usually no
# `wsl` host alias inside the container, and no interactive SSH agent).
tmux new-session -d -s pc-<id> \
  "uv run --project ${POLECAT_ROOT%/aops} $POLECAT_ROOT/polecat/cli.py run agy -p <project> -t <id> \
   2>&1 | tee /tmp/pc-<id>.log"
```

- `-t <id>` seeds `/pull <id>` as the container's initial prompt. For `agy` this
  is delivered headless via `--print` so the worker **runs the task and exits**
  (the container tears down on completion). Do not add `-i`/`--prompt-interactive`
  for autonomous dispatch — that leaves agy idling at a ready prompt forever, a
  live container that looks like progress but never finishes.
- `-p <project>` is the task's own target repo — check the task, not the epic's
  `project` field; they can differ.

**Transport gotchas:**

- `ssh wsl` needs a working SSH key. In a non-interactive session the 1Password
  (or any agent-backed) key may refuse to sign (`agent refused operation`) — if
  the detect step says `LOCAL`, prefer that and skip SSH entirely.
- The `tee /tmp/pc-<id>.log` path is on **whichever host the command runs on**
  (the WSL host for A/B, the container's own `/tmp` for C). Read the log from the
  same side you launched it.

Confirm the session came up (`tmux ls | grep pc-`) and is executing (`tail /tmp/pc-<id>.log`; for agy, `docker ps` should show a fresh `aops-crew` container and the task status should flip to `in_progress` once `/pull` claims it).

## Verify by side-effect, never by self-report

A live session is not success; exit-0 on the launch wrapper is not success.
A unit is done when the return contract actually lands on the PKB task —
status flip + evidence + output URL — checked directly by you or a subagent.
The review-surface artifact (PR, doc) is one possible form of output URL, not
the assumed per-unit artifact. Never relay a worker's own "confirmed" as fact.

Always verify completion specifically against the brief's expected outputs and acceptance criteria.

## Watch for exits, don't poll

Wait on worker exit through a background-task notification or a `Monitor` on
the launch session — never a sleep loop. When one exits: verify its
side-effect, re-read the graph for whatever that unblocked, dispatch that.
Workers coordinate through `claim_task`'s atomic claim, not through you — you
don't need your own lock.

## React to what comes back

A FAIL or re-dispatch call from a review task is not a separate phase — it's
new information the next graph pass reads like any other. If a review found
something, decide (your judgment, not a lookup table) whether to file a fix
subtask wired with `depends_on` back to the failed unit, or re-dispatch the
same unit with the finding appended to its brief. Either way, wire it into
the graph rather than holding it in your head — the next pass has to see it
without you.
