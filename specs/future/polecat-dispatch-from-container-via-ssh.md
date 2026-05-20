---
id: polecat-dispatch-from-container-via-ssh
title: Dispatching polecats from a containerised orchestrator — SSH-tmux, not DinD
type: spec
status: proposed
tier: core
depends_on: []
supersedes: [aops-junior-container-plan-section-3]
related: [aops-18572bc0, task-ddb2fc23, epic-4234682b, aops-04cad256]
tags: [spec, polecat, dispatch, containers, ssh, tmux]
created: 2026-05-21
revision: 1
---

# Polecat dispatch from a containerised orchestrator — SSH-tmux

## Problem

An orchestrator running inside a Docker container (e.g. junior-in-container, a crew worker, a remote dev environment) needs to dispatch polecat workers. The naive design — Docker-in-Docker, mount the host docker socket, translate worktree paths between container and host views — has compounding gaps:

- `$POLECAT_HOME` and `$AOPS_SESSIONS` are filesystem paths; forwarding the container's view of them breaks the host docker daemon's bind-mount step.
- Worktrees and session dirs created inside the parent's filesystem disappear from under spawned children when the parent dies → child crashes on first file write.
- Path translation (`_container_to_host_path()`) only covers paths already inside a host-mounted directory; nesting compounds the surface.

The mechanics _can_ be made to work, but they couple every container that wants to dispatch tightly to the host's filesystem and require non-trivial gymnastics to survive parent-container death.

## Decision

**Dispatch polecats from the host, not from inside containers.** The container opens an SSH session to the host, runs `polecat run …` inside a host-side `tmux` window, and disconnects. The polecat container is then a fully independent host process.

Lifecycle:

1. Orchestrator inside the parent container resolves the task to dispatch.
2. It opens an SSH session to the host (`host.docker.internal` or a configured `POLECAT_HOST`).
3. The remote command is `tmux new-session -d -s polecat-<task-id> 'polecat run <args>'`.
4. Orchestrator disconnects. Parent container can die freely — the tmux session and the polecat-spawned worker container remain.
5. To observe progress, the orchestrator (or any successor) re-attaches via `ssh host -t tmux attach -t polecat-<task-id>`, or reads logs/sessions at the canonical host paths.

## Why this beats DinD

- **Zero path translation.** Polecat runs as a host process with host-native `$POLECAT_HOME`, `$AOPS_SESSIONS`, `$AOPS`. No env-map gymnastics, no `_container_to_host_path()` extension.
- **Lifecycle independence by construction.** Parent dying does not poison child state; child worktrees are on host disk, not inside a vanishing container filesystem.
- **Same code path as a human typing `polecat run`.** No new dispatch transport to test, debug, or maintain. The container is a thin trigger; all behaviour is host-side and identical to interactive use.
- **Already documented patterns.** SSH and tmux are universal; observability (re-attach, read logs) is native.

## Required surface area

Per-container, one-time setup:

1. SSH client present (already in worker Dockerfile via `openssh-client`).
2. SSH key with permission to run `polecat run` on the host. Stored as a staged file (same mechanism as Claude credentials at `/tmp/staging`).
3. Host reachability — `host.docker.internal` on Mac/Windows; explicit `POLECAT_HOST` on Linux.
4. Host-side `sshd` accepting the worker's key, restricted via `authorized_keys` `command="…"` to the polecat dispatch wrapper (no general shell access).
5. Host-side `tmux` installed (universally available; no action needed in most environments).

Per-dispatch:

- A thin wrapper script (`scripts/polecat-dispatch-via-ssh.sh`) invoked by the in-container orchestrator. Takes the task spec on stdin, formats the SSH command, returns the tmux session name.

## Non-goals

- Not extending polecat itself with a "remote dispatch" mode. That's `task-ddb2fc23` territory; this spec uses unmodified `polecat run`.
- Not solving multi-host fan-out. One host per orchestrator-container relationship.
- Not replacing existing crew or direct polecat invocation. This is an additional dispatch path for the in-container case only.

## Fitness rubric

The dispatch is fit if:

- A polecat dispatched this way completes after the parent container is killed (not paused — `docker kill`'d).
- Worktree and session artefacts land at the canonical host paths (`$POLECAT_HOME/polecat/<task-id>`, `$AOPS_SESSIONS/...`), identical to a host-initiated dispatch.
- The orchestrator can re-discover and re-attach to the tmux session by name after restart.
- No code path in `polecat/cli.py` is modified.

## Open questions

- Authentication: short-lived SSH cert vs. long-lived key in `authorized_keys`. Default to the latter for now (matches credential model elsewhere).
- Should the wrapper script enforce a task-ID-derived tmux session name (predictable, re-discoverable) or generate one and return it? Default: derived.
- Multi-tenancy: if two orchestrator containers dispatch the same task ID, tmux session names collide. Defer — same-task double-dispatch is a PKB-level concern, not a transport one.

## Related kill-list

- Supersedes §3 of `aops-junior-container-plan` (host-side dispatcher daemon vs DinD trade-off — now resolved in favour of host-side SSH dispatch).
- `task-ddb2fc23` ("spawn workers on remote hosts") retains independent motivation for the laptop→WSL daemon case but no longer needs to cover from-container dispatch.
- No code to remove — DinD path was never built. Only the design line is being closed.
