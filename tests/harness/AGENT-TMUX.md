# Agent Tmux Pattern

For local CLI verification, agents should drive `tmux` directly rather than using a wrapper harness. A minimal tmux pattern gives you full interactive control over the CLI to verify behaviours.

## The Pattern

```bash
# 1. Spawn a detached session. Give it a large geometry so the UI renders properly.
export TMUX_NAME="test-session-$RANDOM"
tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 'polecat crew -g aops'

# 2. Send literal text and an Enter keystroke
# NOTE: -l ensures special characters aren't interpreted as tmux commands
tmux send-keys -t "$TMUX_NAME" -l "hello world"
tmux send-keys -t "$TMUX_NAME" Enter

# 3. Send raw control keys for UI navigation
tmux send-keys -t "$TMUX_NAME" Down Down Enter

# 4. Capture the pane contents to verify UI state
# -p prints to stdout, -S -N captures N lines of scrollback
tmux capture-pane -t "$TMUX_NAME" -p -S -2000

# 5. End the session cleanly to trigger artifact sync, then kill tmux
tmux send-keys -t "$TMUX_NAME" -l "/exit"
tmux send-keys -t "$TMUX_NAME" Enter
sleep 2  # wait for teardown to flush hooks
tmux kill-session -t "$TMUX_NAME"
```

## Gotchas

- **Alias Resolution:** tmux uses `/bin/sh` by default, so shell aliases like `polecat` or `pc` might not resolve. Use the full path (`uv run --project $AOPS $AOPS/polecat/cli.py crew ...`) if the test environment doesn't have the alias installed.
- **Enter key:** Always send `Enter` as a separate `send-keys` invocation after sending literal text with `-l`. Do not embed `\n` in the literal string.
- **Scrollback:** The `-S -<n>` flag on `capture-pane` is essential; otherwise, you only capture the current viewport (50 lines), which may not contain the response you're looking for.
- **Artifact Teardown Rescue:** For `polecat crew` sessions, if you suspect the worker is wedged and won't respond to `/exit`, you can use `polecat crew --capture-on-exit /path/to/out` when launching it. Polecat will automatically rescue artifacts (even from inside the container) when it receives `SIGTERM` or standard exit.
