---
name: polecat
description: Launch autonomous agent workers inside isolated, detached containers. Use to dispatch tasks or prompts to containerized workers without blocking.
---

# Polecat Launcher

Spawns autonomous workers in isolated, detached containers via `polecat run --detach`. Returns immediately upon initialization without polling or blocking.

## Dispatch Commands

### Task Dispatch

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
polecat run agy -p <project> -t <task-id> -s "dispatch-<task-id>" --base "$BRANCH" --detach
```

### Prompt Dispatch

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
polecat run agy -p <project> -s "run-<slug>" --base "$BRANCH" --detach --prompt '<prompt>'
```

## Options and Rules

- `--prompt`: Must be the final argument; everything following is captured as prompt text.
- `--base <branch>`: Base branch to diverge from. Defaults to upstream HEAD when omitted.
- `-s <session>`: Sets session name. Branch is created as `polecat/<session>`.
- `-p <project>`: Canonical repository slug from `$AOPS_SESSIONS/polecat.yaml`.
- **Detached operation**: Do not pipe to stream filters (`tail`, `head`, `grep`) or poll for output. Caller handles downstream tracking.
- **Remote execution**: If `$POLECAT_HOST` is defined, dispatch via `tailscale ssh`. Halt immediately on connection or command failure.

## Verification Report

Return container ID, session directory, and initial status from `run.json`:

- **Never started**: CLI exited before container initialization.
- **Ran and failed**: Container exited with failure status (`failed`, `killed`, `degraded`).
- **Succeeded / Detached**: Container spawned detached or completed successfully.
