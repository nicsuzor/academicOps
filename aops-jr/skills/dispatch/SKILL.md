---
name: dispatch
description: Dispatch and supervise the distributed execution of an Epic task with sequenced and parallel polecat workers.
---

# Epic Dispatch

An Epic is an assembled workflow of related tasks that form a whole.

You are a delegating supervisor in charge of delivering the entire Epic. Importantly:

- You never do the work yourself, but you are responsible for coordinating the distributed execution of an Epic task with sequenced and parallel workers.
- You must not delegate a task that is not 'queued' or that has unmet dependencies.
- You must inspect completed work; distributed workers are notoriously lazy and sometimes stupid. It is up to you to ensure that each task is FULLY completed to a world-leading standard. You do NOT want to hand back work that does not meet our expectations.
- All steps of an Epic must be worked and completed before the tasks are considered done; the whole Epic must be delivered and assessed in its entirety.
- Your responsibility ends when all an Epic's tasks are completed, failed, or blocked.
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
- Only 'leaf' tasks (tasks with no children) are eligible for dispatch.
- You must dispatch each of a task's subtasks and verify completion before you dispatch a task with children.
- If you are blocked on a task with a dependency outside of the epic's hierarchy, you must HALT and return any work you were able to complete.

3. Sequence tasks and plan your dispatch process.

- Immediately before you dispatch a task, you must invoke the `brief` skill to compose the delegation instructions.
- DO NOT brief tasks prematurely; you should ONLY EVER brief a task that is ready to dispatch right now, in this specific iteration.
- You should do this fresh each time, even if a brief has been created before for a task, because the context may have changed.
- Use your tools to create a loop or reminder here to maintain a rolling fleet of workers.

4. Dispatch workers

The polecat launch command is the same everywhere — only the _transport_ to the
Docker host changes. First figure out **where you are relative to the Docker
daemon that runs polecats** (the WSL host `nicwin`), then pick the matching form.

**Resolve the aops-jr root** (run this first — it decides every path below):

```bash
# ${CLAUDE_PLUGIN_ROOT} is the documented Claude Code plugin-root token, but
# it is NOT reliably exposed as a live shell variable to skill-invoked bash
# commands on every client (verified empirically: unset under a real agy
# dispatch-skill invocation, task_e3979720) — so treat it as a first try,
# not the sole mechanism. Fall back to a filesystem search of the known
# per-client install locations (no monorepo checkout exists there — the
# plugin ships its own pyproject.toml + uv.lock at its install root), then
# to $AOPS/aops-jr for in-repo dev.
JR_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [ -z "$JR_ROOT" ] || [ ! -f "$JR_ROOT/polecat/cli.py" ]; then
  JR_ROOT="$(find "$HOME/.claude/plugins" "$HOME/.gemini/config/plugins" \
    -maxdepth 7 -type f -path '*aops-jr*/polecat/cli.py' 2>/dev/null \
    | head -1 | xargs -r dirname | xargs -r dirname)"
fi
if [ -z "$JR_ROOT" ] || [ ! -f "$JR_ROOT/polecat/cli.py" ]; then
  JR_ROOT="$AOPS/aops-jr"
fi
```

**Detect your context** (run this — it decides the form for you):

```bash
# You can dispatch LOCALLY (no ssh) iff the polecat CLI is on this filesystem
# AND you can reach a Docker daemon from here.
test -f "$JR_ROOT/polecat/cli.py" && docker info >/dev/null 2>&1 && echo LOCAL || echo REMOTE
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
#     "uv run --project $JR_ROOT $JR_ROOT/polecat/cli.py run agy -p <project> -t <id> \
#      2>&1 | tee /tmp/pc-<id>.log"

# --- Context A: REMOTE (another host) ---
# Note: JR_ROOT here resolves on the REMOTE (WSL host) side, not locally —
# the single-quoted ssh payload is deliberately unexpanded on this end.
ssh wsl 'JR_ROOT="${CLAUDE_PLUGIN_ROOT:-}"; \
  if [ -z "$JR_ROOT" ] || [ ! -f "$JR_ROOT/polecat/cli.py" ]; then \
    JR_ROOT="$(find "$HOME/.claude/plugins" "$HOME/.gemini/config/plugins" -maxdepth 7 -type f -path "*aops-jr*/polecat/cli.py" 2>/dev/null | head -1 | xargs -r dirname | xargs -r dirname)"; \
  fi; \
  if [ -z "$JR_ROOT" ] || [ ! -f "$JR_ROOT/polecat/cli.py" ]; then JR_ROOT="$AOPS/aops-jr"; fi; \
  tmux new-session -d -s pc-<id> \
  "uv run --project $JR_ROOT $JR_ROOT/polecat/cli.py run agy -p <project> -t <id> \
   2>&1 | tee /tmp/pc-<id>.log"'

# --- Context B: LOCAL, on the WSL host itself ---
tmux new-session -d -s pc-<id> \
  "uv run --project $JR_ROOT $JR_ROOT/polecat/cli.py run agy -p <project> -t <id> \
   2>&1 | tee /tmp/pc-<id>.log"

# --- Context C: LOCAL, already inside a WSL Docker container (DooD) ---
# Same as B — you are already on the daemon side; the mounted docker.sock makes
# `polecat run` launch sibling containers. Do NOT ssh (there is usually no
# `wsl` host alias inside the container, and no interactive SSH agent).
tmux new-session -d -s pc-<id> \
  "uv run --project $JR_ROOT $JR_ROOT/polecat/cli.py run agy -p <project> -t <id> \
   2>&1 | tee /tmp/pc-<id>.log"
```

- `-t <id>` seeds `/pull <id>` as the container's initial prompt. For `agy` this
  is delivered headless via `--print` so the worker **runs the task and exits**
  (the container tears down on completion). Do not add `-i`/`--prompt-interactive`
  for autonomous dispatch — that leaves agy idling at a ready prompt forever, a
  live container that looks like progress but never finishes (bug `aops_5e7c6cc0`).
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
A unit is done when its task status actually flips or the review-surface
artifact (PR, doc) actually exists — checked directly by you or a subagent. Never relay
a worker's own "confirmed" as fact.

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
