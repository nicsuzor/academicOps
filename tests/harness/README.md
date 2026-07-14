# tests/harness — interactive polecat probes

This directory is the artifact dropbox for agent-driven probes of
`polecat run`. There is no wrapper harness anymore (see #1110 — it was
replaced by inline `tmux`).

> **2026-07-15:** `polecat/cli.py` (the old 5734-line CLI with `crew`,
> `nuke`, `swarm`, `list`, `finish`, task-claiming, etc.) was deleted
> 2026-07-14 (commit `e70e96475`) and replaced by the much smaller
> `polecat/cli_lite.py`, renamed to `polecat/cli.py` on 2026-07-15. The only
> surviving subcommand is `run` (agent_cmd ∈ `claude`/`agy`/`shell`/`sleep`;
> flags `-p/--project`, `-d/--repo-dir`, `-s/--session-name`, `--mcp-url`).
> Examples below use `run` in place of the old `crew`. `run` auto-detects
> interactivity via `sys.stdin.isatty()` — a tmux pane (even spawned with
> `-d`) presents a real TTY, so `polecat run` inside tmux gets the same
> interactive Docker (`-it`) behavior `crew` used to provide (verified
> empirically 2026-07-15).

> This file owns the **tmux mechanics**. For the **validation workflow**
> (what to verify, what signals indicate hooks/plugins/skills are
> actually loaded vs. just file-present), see
> [`11-self-test.md`](../../.agents/skills/aops/workflows/11-self-test.md)
> § 2.

For local CLI verification, drive `tmux` directly rather than using a
wrapper. A minimal tmux pattern gives you full interactive control over
the CLI to verify behaviours.

## The pattern

```bash
# 1. Spawn a detached session. Give it a large geometry so the UI renders properly.
export TMUX_NAME="test-session-$RANDOM"
tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 'polecat run agy -p aops'

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
  (`uv run --project $AOPS $AOPS/polecat/cli.py run ...`) if the test
  environment doesn't have the alias installed.
- **Enter key:** Always send `Enter` as a separate `send-keys` invocation
  after sending literal text with `-l`. Do not embed `\n` in the literal
  string.
- **Scrollback:** The `-S -<n>` flag on `capture-pane` is essential;
  otherwise you only capture the current viewport (~50 lines), which may
  not contain the response you're looking for.
- **No cleanup step needed:** `run`'s underlying `docker run` already
  passes `--rm`, so the container self-removes on exit — there is no
  `polecat nuke`/`list-crew` equivalent to run afterward (those subcommands
  no longer exist).
- **Wedged-worker rescue is currently unsupported:** the old `--capture-on-exit`
  flag (rescue artifacts from inside the container on `SIGTERM` if a worker
  won't respond to `/exit`) has no equivalent in `cli.py`'s `run` —
  `entrypoint.sh` has no `SIGTERM` trap. `run` does live-bind-mount the
  session dir into the container (`-v session_dir:container_session_path`)
  rather than copying artifacts out at exit, so whatever's already been
  _written_ to that path is visible on the host regardless of how the
  container dies — but this is not a verified drop-in replacement for a
  genuinely wedged worker (untested as of 2026-07-15). If you hit a wedged
  polecat session, treat it as a live gap, not a documented workaround.

## Artifacts

Probe outputs land under `artifacts/<probe-name>/` — typically
`pane.log` plus a copy of the host-side session state.

## Dev-loop: testing plugin source in a dev image

Iterate on plugin source (hooks, lib, skills, commands, agents, scripts)
and test it against **both** `claude` and `antigravity` (`agy`) inside a
container, without touching the production image real polecats pull.

```bash
make build-dev                              # refresh dist/ (fast, no Docker)
make build-docker-dev                       # rebuild :dev only (layer-cached)
scripts/dev-crew.sh start claude            # or: start antigravity
scripts/dev-crew.sh send <name> "hello"
scripts/dev-crew.sh watch <name> --once
scripts/dev-crew.sh stop <name>
```

`scripts/dev-crew.sh` is a thin tmux wrapper (start/send/watch/logs/stop)
pointed at `tests/harness/dev-polecat.yaml`, a static config (no live
bind-mount) that targets `ghcr.io/nicsuzor/aops-crew:dev`. Edit → rebuild →
relaunch; there is no instant-visibility mount, so re-run the first two
commands after each source change.

**Not a pre-ship check.** `make verify-docker` (clean `--no-cache`) remains
the real gate — it proves the plugin installs cleanly from a fresh `dist/`.

**Plugin structural check** (no tmux needed): `docker run --rm
ghcr.io/nicsuzor/aops-crew:dev claude plugin list` and `docker run --rm
ghcr.io/nicsuzor/aops-crew:dev ls /home/worker/.gemini/antigravity-cli/plugins/`
— expect exactly `aops` and `aops-tools` from both (see
[`11-self-test.md`](../../.agents/skills/aops/workflows/11-self-test.md) §2
"Plugin pre-check").

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
