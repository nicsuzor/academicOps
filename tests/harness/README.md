# tests/harness — interactive polecat crew probes

This directory is the artifact dropbox for agent-driven probes of
`polecat crew`. There is no wrapper harness anymore (see #1110 — it was
replaced by inline `tmux`).

> This file owns the **tmux mechanics**. For the **validation workflow**
> (what to verify, what signals indicate hooks/plugins/skills are
> actually loaded vs. just file-present), see
> [`aops-core/skills/aops/workflows/11-self-test.md`](../../aops-core/skills/aops/workflows/11-self-test.md)
> § 2.

For local CLI verification, drive `tmux` directly rather than using a
wrapper. A minimal tmux pattern gives you full interactive control over
the CLI to verify behaviours.

## The pattern

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

- **Alias resolution:** `tmux` uses `/bin/sh` by default, so shell aliases
  like `polecat` or `pc` might not resolve. Use the full path
  (`uv run --project $AOPS $AOPS/polecat/cli.py crew ...`) if the test
  environment doesn't have the alias installed.
- **Enter key:** Always send `Enter` as a separate `send-keys` invocation
  after sending literal text with `-l`. Do not embed `\n` in the literal
  string.
- **Scrollback:** The `-S -<n>` flag on `capture-pane` is essential;
  otherwise you only capture the current viewport (~50 lines), which may
  not contain the response you're looking for.
- **Artifact teardown rescue:** If you suspect the worker is wedged and
  won't respond to `/exit`, launch with
  `polecat crew --capture-on-exit /path/to/out`. Polecat then rescues
  artifacts (even from inside the container) on `SIGTERM` or standard exit.
  Note: `tmux kill-session` SIGKILLs the docker client, so capture-on-exit
  only fires on a clean `/exit` — host-side artifacts under
  `$AOPS_SESSIONS/crew/<name>/<project>/` are the reliable source of truth.

## Artifacts

Probe outputs land under `artifacts/<probe-name>/` — typically
`pane.log` plus a copy of the host-side session state.

## Known findings the pattern has surfaced

- **#938** — `polecat crew` (claude) boots unauthenticated; the headless
  `.claude.json` template lacks `oauthAccount`/`hasCompletedOnboarding`,
  so workers re-run onboarding instead of picking up the staged
  `.credentials.json`. (Auth model has since moved to env-only via
  `CLAUDE_CODE_OAUTH_TOKEN` — re-verify whether the bug still reproduces
  before acting on this.)
- **#939** — Gemini crew hooks/transcripts only sync on clean polecat
  exit; wedged sessions lose observability unless extracted from the
  container.
