---
name: dispatch
description: Launch an autonomous worker on one task in an isolated Docker sandbox with its own git clone.
---

# Dispatch

Your only job is to launch workers: one task, one sandbox, one private clone.

- You never do the work yourself.
- Asked for anything else, HALT.
- On any infrastructure or tooling failure, HALT and report it. No workarounds.

## The clone carries only committed work

`--clone` gives the container its own git clone. The container cannot see the
host's working tree. Anything the worker must see -- a task file, a kit, a
Makefile target, a plugin change -- is committed and pushed to the task
branch `<epic_name>-<task_id>` before sandbox creation, or it does not exist
inside the sandbox.

## Launch

```bash
EPIC_NAME=$(git rev-parse --abbrev-ref HEAD)
BRANCH="${EPIC_NAME}-${TASK_ID}"
NAME="${BRANCH}"
KITS="--kit lib/kits/agy --kit lib/kits/aops"
ENV_FLAGS=()
[ -n "${PKB_MCP_URL:-}" ] && ENV_FLAGS+=(-e PKB_MCP_URL)

git checkout -B "$BRANCH" "$EPIC_NAME"
git push -u origin "$BRANCH"

sbx create --clone --name "$NAME" "${ENV_FLAGS[@]}" $KITS agy .
if [ -n "${PKB_MCP_URL:-}" ]; then
  PKB_HOST=$(echo "$PKB_MCP_URL" | sed -E 's|^https?://([^/:]+).*|\1|')
  sbx policy allow network --sandbox "$NAME" "$PKB_HOST:443" >/dev/null 2>&1 || true
fi
```

`sbx create` returns once the sandbox exists, but the `aops` kit's startup
command is still building and installing the framework from the clone. The
worker cannot resolve `/aops:pull` until it finishes. Wait for it, bounded:

```bash
for i in $(seq 1 24); do
  log=$(sbx exec "$NAME" -- tail -3 /var/log/sbx-kit-startup.log 2>&1)
  case "$log" in
    *"dispatcher complete"*) break ;;
    *"fail /etc/durable-startup"*) echo "$log"; exit 1 ;;
  esac
  [ "$i" = 24 ] && { echo "TIMEOUT: $log"; exit 1; }
  sleep 15
done

sbx run --name "$NAME" --kit lib/kits/agy agy . -- -p "/aops:pull $TASK_ID"
```

A `fail` line or the timeout is a HALT. Report the log verbatim; do not retry
into a sandbox whose framework did not install.

## Collect

The sandbox's commits reach the host through a git remote named after it (`sandbox-$NAME`).
Fetch the commits and merge the task branch back into `$EPIC_NAME`:

```bash
git fetch "sandbox-$NAME"
git checkout "$EPIC_NAME"
git merge --ff-only "sandbox-$NAME/$BRANCH" || git merge "sandbox-$NAME/$BRANCH"
git push origin "$EPIC_NAME"
sbx rm -f "$NAME"
```

Fetch before you remove. `sbx rm -f` destroys the clone and the daemon serving
it, and uncollected commits go with them. Once all tasks in the epic are complete,
file a single PR from `$EPIC_NAME`.

## Notes

- `sbx exec <name> -- <cmd>` runs a command in an existing sandbox.
- `sbx ls` lists sandboxes and their status.
- The kits are the only configuration. Pass no images and no docker flags.
- `lib/kits/agy` supplies the client; `lib/kits/aops` builds the framework from
  the clone and installs it for that client. Both are required.
- The workspace path inside the container is `$WORKSPACE_DIR`, and it matches
  the host repository path. The host repository is separately mounted read-only
  at `/run/sandbox/source`.

## Report

Return whatever the caller asked for; the sandbox name and its fetched ref if
they said nothing.

Report the outcome and explicit tri-state:

- **Never started**: `sbx create` exited non-zero, or the kit startup command
  logged `fail`. Cite the verbatim error or log line.
- **Ran and failed**: the agent ran and exited non-zero, or the task it was
  given is not in a terminal state. Cite the exit code and the task status.
- **Succeeded**: the agent ran to completion and the task reached `done`,
  `review`, `partial`, or `cancelled`. Cite the task status and the fetched ref.
