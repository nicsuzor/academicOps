---
name: debug
description: Use when asked to "debug a polecat", "run a polecat container interactively", "attach to a polecat session", "check polecat logs", or to verify that a change to plugins, hooks, lib/, skills, or the Dockerfile actually works inside a real container. Spins up a `polecat run` container under tmux for live interaction, says where the durable host-side session state lands, and walks the layered check that separates "installed in the image" from "actually fires".
---

# Interactive polecat debugging

Spin up a real `polecat run` container under `tmux` and interact with it live.
Mechanics and gotchas: [`specs/polecat/tmux-interactive-driving.md`](../../../specs/polecat/tmux-interactive-driving.md).
Do not duplicate that here.

## Spin up

```bash
export TMUX_NAME="polecat-debug-$RANDOM"
tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 \
  "uv run --project $AOPS python $AOPS/plugins/aops/polecat/cli.py run agy -p aops -s $TMUX_NAME 'what directory are you in? answer in one sentence, then stop.'"
```

Use the absolute path, not a shell alias and not a relative one — inside the
`sh -c` tmux spawns, neither an unresolved alias nor a path relative to some
other cwd resolves, and the failure kills the whole tmux server rather than
just the pane. `capture-pane` then reports `no server running`, which reads
like a tmux problem rather than a command-not-found.

**Check `$AOPS` names the checkout you are testing, before you spin up.** It is
not guaranteed to be set, and where it is set it commonly names the main clone
— so from a worktree the command above launches that other tree's `cli.py`
against your session and reports a result that has nothing to do with your
change. Unset, it expands to an empty `--project` and a bad script path, which
fails inside `sh -c` and produces exactly the `no server running` symptom
described above.

```bash
echo "$AOPS"                 # must equal the checkout under test
export AOPS="$(git rev-parse --show-toplevel)"   # if it does not
```

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

## Validate a dev change

Run after any change to `plugins/*/hooks`, `lib/`, the shipped skills, agents
or commands, `plugins/aops/polecat/cli.py`, `plugins/aops/polecat/defaults/*`,
`entrypoint.sh`, or the Dockerfile. This is what separates "the files are in
the image" from "the framework actually fires" — a plugin that installs
cleanly and does nothing is the failure this catches.

Run both clients. Asymmetric breakage between `claude` and `agy` is common,
and a pass on one is not evidence for the other. Walk the layers in order and
stop at the first failure: a later layer's result is uninterpretable once an
earlier one is broken.

**Pre-flight: are hooks live?** Read `_log_fire` and `_load_handlers` in
`lib/hooks/dispatch.py`. While either returns before its body, no hook fires and
no hook log is written for any client, whatever your change did. If that is the
state you find, §5 cannot pass and §3 cannot tell you anything about hook
behaviour — run both anyway, and read their results as uninformative rather than
as failures. Establish this before §0, not after a confusing §5.

**§0 Build the image from your change.** `make docker-build` reuses the layer
cache and is right for the edit loop. Before certifying anything, use
`make verify-docker` — a cached layer can carry the previous plugin set into
an image that looks rebuilt, and a green result on that image is evidence of
nothing.

**§1 Structural check.** `make docker-smoke-test` boots the real image and
asserts every plugin `build/marketplace.toml` declares is installed and enabled
under `claude` and present under agy, that `$ACA_DATA` matches what `cli.py`
mounts layer-3 rules onto, and that the agy session mount target is writable.
Seconds, no tmux. A marketplace cache-miss or a failed plugin install is silent
at startup and only surfaces later as missing tools; this catches it
immediately. For what a structural pass does and does not prove, read the
spec's "Plugin structural check" — the layers below are what it says to
corroborate with.

**§2 Boot signals.** Spin a session with the tmux pattern above, then
`capture-pane -p -S -2000`. Expect a ready prompt with no onboarding or
folder-trust dialog blocking it. Do not read footer chrome as a boot signal —
it renders before the client is ready.

**§3 First prompt.** Send a trivial prompt and capture again. A hook-blocked
error is a pass for this layer, not a failure: the hook fired and reported.
Treat the error text as primary evidence. The response itself is the liveness
signal — do not build a poll loop beside it.

**§4 Skill and subagent exercise.** Invoke a skill and dispatch a subagent from
inside the session. Verify visible output in the pane, not merely that the call
returned. A skill that resolves and produces nothing passes a structural check
and fails here.

**§5 Observability.** Confirm `polecat-session-hooks.jsonl` is present and
populated in the session directory, and that the PKB MCP answers rather than
refusing or timing out. The spec says what that file is evidence of, under
"Log & artifact locations". An empty or missing hook log is a finding only if
the pre-flight found hooks live; otherwise it says nothing about your change.

**§6 Cleanup.** `/exit`, then `tmux kill-session`. Repeat for the other client.

On failure, file one issue per root cause, not per symptom.
