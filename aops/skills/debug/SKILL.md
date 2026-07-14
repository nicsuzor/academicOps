---
name: debug
description: This skill should be used when the user asks to "debug a polecat",
  "run a polecat container interactively", "attach to a polecat session", "spin
  up a debug polecat", "check what a polecat is doing", or "check polecat logs".
  Spins up a `polecat run` container under tmux for live interaction and
  explains where to find both the live user-facing view and the durable
  host-side session logs.
---

# /aops:debug — Interactive Polecat Debugging

Spin up a real `polecat run` container under `tmux`, interact with it live,
and know where the two kinds of logs live. Full mechanics, gotchas, and the
plugin dev-loop live in [[specs/polecat/tmux-interactive-driving.md]] — read
that for anything not covered here; do not duplicate it.

## Spin up a session

```bash
export TMUX_NAME="polecat-debug-$RANDOM"
tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 \
  "polecat run agy -p aops -s $TMUX_NAME"
```

Swap `agy` for `claude` to debug the Claude client instead, or `shell` for a
plain shell in the container with no agent. Swap `-p aops` for
`-d <repo-path>` when the target project has no entry in
`~/.aops/local.yaml`. Passing `-s "$TMUX_NAME"` ties the tmux session name
to the host log directory name — do this every time so the two are trivial
to correlate afterward.

## Interact with it

```bash
tmux send-keys -t "$TMUX_NAME" -l "your prompt text here"
tmux send-keys -t "$TMUX_NAME" Enter          # Enter is always a separate send-keys call
tmux send-keys -t "$TMUX_NAME" Down Down Enter # raw keys for menu/UI navigation
```

## View the live, user-facing state

```bash
tmux capture-pane -t "$TMUX_NAME" -p -S -2000   # -S for scrollback, not just the viewport
```

This is exactly what a human attached to the session would see — prompts,
responses, dialogs, TUI chrome. Use it to judge _behavior_. It vanishes with
the tmux session; it is not a durable record.

## View the official, durable logs

Everything the container writes to its own session-state path is
live-bind-mounted to the host, so it survives independent of the tmux
session:

```
$AOPS_SESSIONS/logs/<YYYYMMDD>/<session-id>/<project>/
```

`<session-id>` is whatever was passed to `-s` above. Inside that directory:

- `polecat-session-hooks.jsonl` — the aops-core hook event log; the primary
  signal for "did the framework actually fire," not just "did the UI render
  something."
- `polecat-session-exit_reflection.md` / `-hydration.md` / `-ida.md` — gate
  check-files, present only if those gates fired.
- The agent's own raw session transcript, written natively (Claude's
  `<session-uuid>.jsonl`, or Gemini/Antigravity's session JSON) — read
  directly with `jq`/`grep`/`less`. There is currently no
  transcript-to-markdown conversion tool in this repo; ignore any doc that
  references one.

## Clean up

```bash
tmux send-keys -t "$TMUX_NAME" -l "/exit"; tmux send-keys -t "$TMUX_NAME" Enter
sleep 2   # let the client flush its own session file
tmux kill-session -t "$TMUX_NAME"
```

No manual container cleanup is needed — `run`'s `docker run --rm`
self-removes the container on exit.
