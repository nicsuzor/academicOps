---
name: debug
description: Use when asked to "debug a polecat", "run a polecat container interactively", "attach to a polecat session", or "check polecat logs". Spins up a `polecat run` container under tmux for live interaction, and says where the durable host-side session state lands.
---

# Interactive polecat debugging

Spin up a real `polecat run` container under `tmux` and interact with it live.
Mechanics and gotchas: [`specs/polecat/tmux-interactive-driving.md`](../../../specs/polecat/tmux-interactive-driving.md).
Do not duplicate that here.

## Spin up

```bash
export TMUX_NAME="polecat-debug-$RANDOM"
tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 \
  "uv run python plugins/aops/polecat/cli.py run agy -p aops -s $TMUX_NAME 'what directory are you in? answer in one sentence, then stop.'"
```

Use the explicit path, not a shell alias — inside the `sh -c` tmux spawns, an
unresolved alias kills the whole tmux server, not just the pane.

Swap `agy` for `claude` to debug the Claude client, or `shell` for a plain shell
with no agent. Swap `-p aops` for `-d <repo-path>` when the target project has no
`paths` entry in `$POLECAT_HOME/local.yaml`. Always pass `-s "$TMUX_NAME"` so the
tmux session name and the host log directory name match.

**Never pass `-d` a linked git worktree.** Its `.git` is a file pointing at the
main checkout's `.git/worktrees/<name>`, which is outside the mounted directory,
so every git command in the container fails with `fatal: not a git repository`.
`-d` skips clone-based isolation by design and mounts the path as-is, so nothing
repairs this. Add a `paths` entry for the worktree in `$POLECAT_HOME/local.yaml`
and run with `-p <project>` instead.

**Reproduce the real invocation before simplifying.** Whether a prompt or `-t
<task>` is present changes what the client renders before going idle; a
simplified repro can look like a dead hang while pointing at the wrong layer.

**Check the client's flag surface before assuming its behaviour:**

```bash
docker run --rm --entrypoint agy "$POLECAT_IMAGE" --help
```

agy has no bare-positional-prompt convention — an initial prompt lands only via
`-i`/`--prompt-interactive` or `-p`/`--print`. `cli.py`'s `run()` handles this,
but know it is there before concluding a dropped prompt means a crash.

## Interact

```bash
tmux send-keys -t "$TMUX_NAME" -l "your prompt text here"
tmux send-keys -t "$TMUX_NAME" Enter           # Enter is always a separate call
tmux send-keys -t "$TMUX_NAME" Down Down Enter # raw keys for menu navigation
```

## Read the live state

```bash
tmux capture-pane -t "$TMUX_NAME" -p -S -2000   # -S for scrollback
```

This is exactly what an attached human would see. Use it to judge behaviour. It
dies with the tmux session; it is not a durable record.

## Read the durable state

`run` prints `Workspace:` and `Session logs:` on start. The session directory is
bind-mounted live into the container, so it survives the tmux session:

```
$AOPS_SESSIONS/logs/<YYYYMMDD>/<session-id>/<project>/
```

It holds the agent's own raw transcript, written natively by the client —
Claude's `<session-uuid>.jsonl`, or agy's `agy-brain/`, `agy-logs/`, and
`agy-cli.log`. Read them directly with `jq`/`grep`/`less`. There is no
transcript-to-markdown converter in this repo; ignore any doc claiming one.

## Clean up

```bash
tmux send-keys -t "$TMUX_NAME" -l "/exit"; tmux send-keys -t "$TMUX_NAME" Enter
sleep 2   # let the client flush its session file
tmux kill-session -t "$TMUX_NAME"
```

No container cleanup is needed — `run` uses `docker run --rm`.
