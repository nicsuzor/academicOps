---
id: polecat-tmux-interactive-driving
title: "Driving Polecat Sessions Interactively via tmux"
type: spec
status: ready
tier: polecat
depends_on: []
tags: [spec, polecat, tmux, debugging, interactive]
---

# Driving Polecat Sessions Interactively via tmux

Canonical spec for how an agent (or a human) drives a `polecat run` container
interactively — sending input, reading output, and locating logs — without a
wrapper harness.

`lib/polecat/cli.py` exposes a single `run` subcommand (bind-mount
workspace, forward env, `docker run` claude/agy/shell/sleep) — no task
claiming, no PR filing, no `crew`/`nuke`/`swarm`/`list`. This spec covers
driving `run` only — see [[polecat-system]] for what `run` does end to end.

## Guarantee

A tmux pane — even one spawned detached (`tmux new-session -d`) — presents a
real TTY to the process running inside it. `polecat run` decides whether to
pass Docker's `-it` flag by checking `sys.stdin.isatty()`
(`lib/polecat/cli.py`, `run()`) unless a headless flag (`-p`,
`--print`) is present in the trailing args. So
`polecat run <agent> -p <project>` launched inside tmux gets full interactive
Docker behavior (`-p` here is polecat's own `--project`, not the agent's
headless prompt flag).

## The pattern

```bash
# 1. Spawn a detached session with an explicit, correlatable name. Give it a
#    large geometry so the UI renders properly. Use the explicit `uv run`
#    path, not the bare `polecat`/`pc` alias — see Gotchas.
CHECKOUT="$(git rev-parse --show-toplevel)"   # never $AOPS — see Gotchas
export TMUX_NAME="polecat-debug-$RANDOM"

# Write the launch to a script and hand tmux the path, not an inline command.
# Env assignments, a `uv run` invocation and a quoted prompt do not survive one
# round of shell quoting inside `tmux new-session` — see Gotchas.
cat > /tmp/"$TMUX_NAME".sh <<EOF
#!/bin/bash
exec uv run --project $CHECKOUT python $CHECKOUT/lib/polecat/cli.py \
  run -d $CHECKOUT -s $TMUX_NAME agy -- \
  'what directory are you in? answer in one sentence, then stop.'
EOF
chmod +x /tmp/"$TMUX_NAME".sh
tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 /tmp/"$TMUX_NAME".sh
# -s ties the host log dir's session-id to the tmux session name, provided the
# name survives sanitization unchanged — see "Log & artifact locations" below.
# A bare no-prompt launch exercises a
# different code path than a real /pull <task> dispatch — reproduce with a
# representative prompt first, only drop it once the
# symptom is confirmed to reproduce either way.

# 2. Send literal text and an Enter keystroke
# NOTE: -l ensures special characters aren't interpreted as tmux commands
tmux send-keys -t "$TMUX_NAME" -l "hello world"
tmux send-keys -t "$TMUX_NAME" Enter

# 3. Send raw control keys for UI navigation
tmux send-keys -t "$TMUX_NAME" Down Down Enter

# 4. Capture the pane contents to verify UI state
# -p prints to stdout, -S -N captures N lines of scrollback
tmux capture-pane -t "$TMUX_NAME" -p -S -2000

# 5. End the session cleanly, then kill tmux
tmux send-keys -t "$TMUX_NAME" -l "/exit"
tmux send-keys -t "$TMUX_NAME" Enter
sleep 2  # let the client flush its own session file before the pane dies
tmux kill-session -t "$TMUX_NAME"
```

For `claude` instead of `agy`, swap the inner command (same explicit-path
form): `... run claude -p aops -s $TMUX_NAME`. For a plain shell in the
container (no agent, just a debug prompt): `... run shell -p aops -s
$TMUX_NAME`.

`agy` gates its ready prompt behind a folder-trust dialog ("Do you trust the
contents of this project?") for any workspace not in its trust store. For
polecat-launched `agy`, `setup_staging()` pre-trusts `/workspace` by injecting
it into `antigravity-cli/settings.json`'s `trustedWorkspaces` array (the
authoritative store for agy 1.1.x — the top-level `trustedFolders.json` is the
legacy gemini-cli mechanism agy ignores), so the container boots straight to
the ready prompt with no dialog and no swallowed seed prompt. If you drive a
**bare** `agy` (outside polecat) against an untrusted folder, the dialog will
still appear: send `Enter` once after boot to accept the default ("Yes, I
trust this folder") before sending any real prompt.

## Log & artifact locations

There are two distinct places to look, and they answer different questions.
See [[polecat-system]] for what the CLI is doing when it writes to either.

### 1. User-facing: the live pane (what the agent/human sees)

`tmux capture-pane -t "$TMUX_NAME" -p -S -2000` — this is the rendered
terminal UI exactly as a person attached to the session would see it
(prompts, responses, tool-call summaries, TUI chrome). Use this to verify
_behavior_ — did the agent respond, did a dialog block it, did onboarding
fire. It is not a durable log; it exists only while the tmux session is
alive (or until scrollback rotates out).

### 2. Official: the host-side session directory (what's actually recorded)

`lib/polecat/cli.py` bind-mounts a host directory straight into the container —
not a copy-on-exit step, a live mount — so everything the agent writes to
its own session-state path is visible on the host in real time, session
alive or dead:

```
$AOPS_SESSIONS/logs/<YYYYMMDD>/<session-id>/<project-or-"workspace">/
```

Where `<session-id>` is what you passed to `-s`/`--session-name` **after
sanitization** (or an autogenerated `session-<uuid8>` if omitted — pass `-s`
explicitly so you can find it again). `cli.py` rewrites every character outside
`[a-zA-Z0-9_.-]` to `_` and strips leading and trailing `._-`, so a name
carrying a slash, colon, or space lands in a directory that is not spelled the
way you typed it. Keep `-s` inside that character set and the name you pass is
the directory you get; the `polecat-debug-$RANDOM` above already is.
`$AOPS_SESSIONS` is required and has no fallback: unset, `polecat
run` exits non-zero before starting a container, because a guessed root would
collect transcripts the export pipeline never scans. This directory is designed
to contain:

- **`polecat-session-hooks.jsonl`** — the shared hook runtime's (`lib/hooks/`)
  event log: every hook firing (`SessionStart`, `SubagentStop`, `Stop`,
  `PreToolUse`, …). This is the primary signal for "did the framework
  actually fire," as distinct from "did the UI render something." Its
  absence is a functional defect, not an alternate valid state.
- **The agent's own raw session transcript** — for `claude`/`shell`/`sleep`,
  this path _is_ Claude Code's own `-<slugified-cwd>` session-state
  directory for `cwd=/workspace` (`/home/worker/.claude/projects/-workspace`),
  so its native `<session-uuid>.jsonl` lands here directly. For `agy`, it is
  `agy-brain/<uuid>/.system_generated/logs/transcript.jsonl`: `run()` mounts
  `$SESSDIR/agy-brain` to `/home/worker/.gemini/antigravity-cli/brain`.
  `_transcript_paths()` (`lib/polecat/cli.py`) reads both shapes, so
  `_seed_confirmed()` takes the same primary evidence that a seeded task was
  actually seen whichever CLI ran the dispatch.
- **`run.json`** — the run record, including a `transcript` block naming which
  transcript the run persisted, its size, and how many landed. `found: false`
  also files a `degraded[]` entry: a run that recorded nothing must not read
  the same as one that recorded a full conversation.

Read the raw JSONL transcript directly (`jq`, `grep`, `less`) when working inside a live container. The transcript-to-markdown converter in `lib/py/transcripts/` (specified in `specs/transcript-pipeline.md`) runs as a host-side batch process over completed sessions rather than in-session.

**`docker logs` is not a reliable source for agy.** agy redirects its own
stdout/stderr to its internal log file rather than the container's actual
stdout/stderr streams, so `docker logs <container>` reads empty even while
agy is fully alive and working — this is not evidence that nothing is
happening. `lib/polecat/cli.py`'s `run()` passes agy `--log-file
/home/worker/.gemini/antigravity-cli/cli.log`, bind-mounted straight to
`agy-cli.log` in the session directory above, so the real log is readable
directly on the host (`tail`/`grep`, no `docker exec` needed) without racing
container teardown to grab it.

## Gotchas

- **Alias resolution can silently kill the whole tmux session, not just the
  pane.** `tmux new-session -d -s NAME 'polecat run ...'` spawns
  `/bin/sh -c 'polecat run ...'` as the pane's only process. `polecat` is a
  `.venv/bin/polecat` console-script, put on `PATH` by shell-rc activation
  that a bare `sh -c` never sources — if it's not resolvable, the pane's
  command fails instantly, the pane closes, and because it was the only
  session, the entire tmux server exits. `tmux capture-pane` then reports
  `no server running on /tmp/tmux-...-default`, which reads like a
  tmux/environment problem rather than a command-not-found. Always use the
  explicit path, never the bare command, when spawning inside tmux:
  `uv run --project <checkout> python <checkout>/lib/polecat/cli.py run ...`
  (the `pc` alias has the identical failure mode for the identical reason).
- **Hand tmux a script, not a long inline command.** The pane's command runs
  under `/bin/sh -c`, and everything a real launch needs — several environment
  assignments, a `uv run` invocation, a quoted prompt — has to survive one round
  of shell quoting inside the `tmux new-session` argument. A backslash
  continuation or a nested quote that does not survive it produces a command
  that fails instantly, which closes the pane, which kills the tmux server when
  it was the only session: the `no server running` symptom again, from a third
  cause. Writing the launch to a small executable script and passing its path
  removes the quoting layer entirely.
- **`$AOPS` is not a safe stand-in for the checkout under test.** It is not
  guaranteed to be set, and where it is set it commonly names the main clone —
  so a command written against it launches that tree's `cli.py` from a
  worktree, and reports a result about code you did not change. Unset, it
  expands to nothing, producing a bad script path and an empty `--project`,
  which fails inside `sh -c` and presents as the same `no server running`
  symptom as the alias failure above. Spell the checkout path explicitly in
  anything that drives a session.
- **Enter key:** Always send `Enter` as a separate `send-keys` invocation
  after sending literal text with `-l`. Do not embed `\n` in the literal
  string.
- **Scrollback:** The `-S -<n>` flag on `capture-pane` is essential;
  otherwise you only capture the current viewport (~50 lines), which may
  not contain the response you're looking for.
- **No manual cleanup step needed:** `run`'s underlying `docker run` already
  passes `--rm`, so the container self-removes on exit.
- **A bind-mount source outside the VM's shared paths fails silently, as an
  empty directory rather than an error.** Where the daemon runs in a VM
  (colima, Docker Desktop), only the host paths that VM is configured to share
  reach the container. A `-v` whose source is outside them does not fail —
  Docker creates an empty root-owned directory at the target instead, so the
  mount appears to exist while containing nothing, and a write to it fails
  with a permission error that reads like a UID problem. On colima, `mounts:
  []` in `~/.colima/default/colima.yaml` means only `$HOME` is shared, which
  excludes both `/tmp` and the `/var/folders/...` path Python's `tempfile` (and
  so pytest's `tmp_path`) resolves to. Keep any workspace or probe directory
  under `$HOME`, and read a permission denial on a fresh mount as a candidate
  mount-source problem before treating it as a UID mismatch.
- **Wedged-worker rescue:** if a worker won't respond to `/exit`, there is
  no dedicated rescue flag — the session dir is a live bind-mount rather
  than a copy-at-exit, so whatever's already been _written_ survives
  regardless of how the container dies, but this has not been established
  as a full replacement for a dedicated rescue mechanism. Treat a wedged
  session as a live gap.

## Dev-loop: testing plugin source in a locally built image

Iterate on plugin source (`lib/`, `plugins/*/hooks`, `skills`, `commands`,
`agents`) and test it inside a container built from this checkout's own
source, without touching whatever image a released `polecat run` would pull.

`-p aops` resolves via `<polecat_home>/local.yaml`'s `paths` map (see
[[polecat-system]]), so `local.yaml` needs an `aops` entry pointing at this
checkout first:

```bash
CHECKOUT="$(git rev-parse --show-toplevel)"   # never $AOPS — see Gotchas
mkdir -p "$POLECAT_HOME"
cat > "$POLECAT_HOME/local.yaml" <<EOF
paths:
  aops: $CHECKOUT
EOF
```

`entrypoint.sh` refuses to start without a commit identity and a GitHub
token — a `dev-probe` session needs both set, same as any other `run`
invocation; a real bot token is not required for a session that never pushes:

An `agy` dev-loop session additionally needs `$GEMINI_CONFIG_DIR` set on the
host, or it boots straight into an interactive Google OAuth wall instead of a
ready prompt. `setup_staging()` (`lib/polecat/cli.py`) stages agy's
credentials — `antigravity-oauth-token` and `installation_id` — from
`$GEMINI_CONFIG_DIR/antigravity-cli/` into the container; unset, no
credential is staged and agy has nothing to authenticate with. `claude`
dev-loop sessions are unaffected — this variable is agy-only.

```bash
make docker-build                    # assembles dist/ then builds the image
                                      # from AOPS_DIST_SOURCE=local, tagging
                                      # ghcr.io/nicsuzor/aops-crew:latest
GIT_AUTHOR_NAME="Your Name" GIT_AUTHOR_EMAIL="you@example.com" \
AOPS_BOT_GH_TOKEN=dev-probe-placeholder \
POLECAT_IMAGE=ghcr.io/nicsuzor/aops-crew:latest \
  uv run --project $CHECKOUT python $CHECKOUT/lib/polecat/cli.py run claude -p aops -s dev-probe
```

Drive that session with the same tmux pattern as above. To send and capture
rather than attach live, put the block above into a script and hand tmux the
path — those env assignments will not survive quoting inside an inline
`tmux new-session` argument.
Edit → `make docker-build` → relaunch; there is no live-mount, so a source
change needs a rebuild before it's visible in the container.

**Plugin structural check** (no tmux needed): the image's own `ENTRYPOINT`
(`entrypoint.sh`) refuses to run at all without a commit identity and a GitHub
token (same as the dev-loop session above), which a pure "what's installed"
check needs neither of — bypass it with `--entrypoint sh -c` rather than
supplying placeholder credentials a read-only check has no use for:
`docker run --rm --entrypoint sh ghcr.io/nicsuzor/aops-crew:latest -c 'claude
plugin list'` and `docker run --rm --entrypoint sh
ghcr.io/nicsuzor/aops-crew:latest -c 'ls
/home/worker/.gemini/antigravity-cli/plugins/'` — expect every plugin declared
in `build/marketplace.toml` from both, each `claude plugin list` entry showing
`Status: ✔ enabled`. This structural check
alone is not sufficient evidence of a healthy session — a plugin reported as
installed is not proof its MCP servers or hooks are actually active for the
running session; corroborate with a functional check (a real tool call, a
populated `polecat-session-hooks.jsonl`).

## Artifacts

A driving session that wants to keep probe output (`pane.log`, a copy of
host-side session state) writes it wherever the session's own scratch space is.
Nothing is written automatically and no location is reserved.
