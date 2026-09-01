---
name: polecat
description: Assigns a task to a team of agents in a detached, isolated container.
---

# Polecat launcher

Your only job is to launch polecats: autonomous workers in an isolated container in detached mode.

- You never do the work yourself.
- Asked for anything else, HALT.
- On any infrastructure or tooling failure, HALT and report it. No workarounds.

## Dispatch and detach: never wait for the work to finish

- The caller is responsible for checking back on the outcome, not you. You never poll, loop, or sleep to wait for a background job to finish. You never schedule a reminder to check back. You never redirect output through a stream filter (e.g., `tail`, `head`, `less`, `grep`) that buffers output.
- `pc` is a detached launcher: it executes `polecat run --detach` and returns immediately upon container initialization; `pc` never waits or polls on the running worker.

## Launching a polecat with a task id

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
NAME="dispatch-<task-id>"
uv run --project '${CLAUDE_PLUGIN_ROOT}' python3 '${CLAUDE_PLUGIN_ROOT}/polecat/cli.py' run agy -p <project> -t <task-id> -s "$NAME" --base "$BRANCH" --detach
```

## Launching a polecat with a detailed prompt

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
NAME="run-<slug>"
uv run --project '${CLAUDE_PLUGIN_ROOT}' python3 '${CLAUDE_PLUGIN_ROOT}/polecat/cli.py' run agy -p <project> -s "$NAME" --base "$BRANCH" --detach --prompt '<prompt>'
```

**Notes:**

- `polecat run --detach` is non-blocking: it spawns the container in detached mode and emits the container and session info immediately.
- `--prompt` **must be last**: everything after it is part of the prompt.
- **No redirection, no polling.** Never redirect output or pipe to `tail`, `head`, `less` etc. Never poll or loop for output.
- `--base <branch>`: specifies the base branch to diverge from (fetched fresh from origin before creating the worktree). When omitted, polecat automatically branches from up-to-date upstream HEAD.
- `-s` sets the session name. The container branch is constructed deterministically as `polecat/<session>`:
  - Task dispatch (`-s "dispatch-<task-id>"`): `polecat/dispatch-<task-id>`
  - Prompt run (`-s "run-<slug>"`): `polecat/run-<slug>`
  - Unset `-s`: `polecat/session-<8 hex>`
  - **Authorship & limit**: The branch name proves automated polecat provenance (ruling out parallel human work), but encodes the task/session name rather than an attempt ID — multiple dispatches of the same task share the same branch name.
- `-p <project>` names the target repo. Valid project slugs come from the canonical project registry at `$AOPS_SESSIONS/polecat.yaml` (consult it before resolving a repo name; per-machine workspace paths are mapped in `<polecat_home>/local.yaml`).
- Never use `-d` (`--repo-dir`) with a linked git worktree: its `.git` file points outside the container mounts and git breaks.
- Never pass an interactive flag: the worker idles at the prompt forever.
- `uv run` needs `--project '${CLAUDE_PLUGIN_ROOT}'`. Without it `uv` resolves no project from the
  launch cwd and the CLI dies with `ModuleNotFoundError: No module named 'click'`.
- Print timeout is configured in `polecat.yaml` (e.g. `timeout: 30m`). No env var fallback.
- Pass no paths, images, or credentials. Polecat reads those from the host environment and `polecat.yaml`.
- Polecats do not know our tool, skill, or server names. Write prompts in plain English.

## Remote host

If `$POLECAT_HOST` is set, dispatch using `tailscale ssh`. Decide on the variable alone: never probe for docker, never guess.

- `polecat` must be on the remote host's `PATH`. A `command not found` from the remote is a HALT; report that as the cause.
- Any ssh failure: HALT and report. Never fall back to local, never retry.

## Report

Return whatever the caller asked for; the container ID and session directory if they said nothing.

Report the outcome and explicit tri-state:

- **Never started**: CLI exited before container start (no `run.json`, non-zero exit code, error on stderr).
- **Ran and failed**: container executed and completed but failed (status in `run.json` is `failed`, `killed`, `delivery_guard_failed`, or `degraded`).
- **Succeeded**: container spawned detached or ran to completion successfully (status in `run.json` is `detached` or `success`).

Always cite the `run.json` path and its `status` field as verification evidence.
