---
name: debug
description: Use when asked to "debug a polecat", "run a polecat container interactively", "attach to a polecat session", "check polecat logs", or to verify that a change to plugins, hooks, lib/, skills, or the Dockerfile actually works inside a real container. Spins up a `polecat run` container under tmux for live interaction, says where the durable host-side session state lands, and walks the layered check that separates "installed in the image" from "actually fires".
---

# Interactive polecat debugging

Spin up a real `polecat run` container under `tmux` and interact with it live.
Mechanics and gotchas: [`specs/polecat/tmux-interactive-driving.md`](../../../specs/polecat/tmux-interactive-driving.md).
Do not duplicate that here.

## Spin up

Resolve the checkout under test first, and spell it out in every command. Never
`$AOPS`, never an alias, never a relative path — the spec's Gotchas say what
each of those breaks and why the symptom misleads.

Write the launch into a small script and hand tmux the script path, not an
inline command — the spec's "The pattern" shows the invocation; a version of it
carrying env assignments and nested quoting through `sh -c` is where this step
dies before the container starts.

```bash
CHECKOUT="$(git rev-parse --show-toplevel)"   # the tree whose change you are testing
export TMUX_NAME="polecat-debug-$RANDOM"
cat > /tmp/launch-$TMUX_NAME.sh <<EOF
#!/bin/bash
export POLECAT_HOME=... POLECAT_IMAGE=... GIT_AUTHOR_NAME=... GIT_AUTHOR_EMAIL=... AOPS_BOT_GH_TOKEN=...
exec uv run --project "$CHECKOUT" python "$CHECKOUT/lib/polecat/cli.py" \\
  run claude -d <repo-path> -s "$TMUX_NAME"
EOF
chmod +x /tmp/launch-$TMUX_NAME.sh
tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 "/tmp/launch-$TMUX_NAME.sh"
```

Swap `claude` for `agy` to debug the Antigravity client, or `shell` for a plain
shell with no agent. Use `-p <project>` in place of `-d <repo-path>` when the
project has a `paths` entry in `$POLECAT_HOME/local.yaml`. Always pass
`-s "$TMUX_NAME"` so the tmux session name and the host log directory name
match.

Set every variable the script exports; the spec's "Dev-loop" section says what
each is for and which are required. Keep the workspace under `$HOME` — the
spec's Gotchas say why a mount source outside the VM's shared paths fails
silently rather than loudly.

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
or commands, `lib/polecat/cli.py`, `lib/polecat/defaults/*`, `entrypoint.sh`,
or the Dockerfile. This is what separates "the files are in the image" from
"the framework actually fires" — a plugin that installs cleanly and does
nothing is the failure this catches.

Before §0, write down the one thing your change was supposed to make happen
inside a container — the specific hook, skill, agent, command or CLI behaviour
it touched. §3 and §4 are scored against that sentence, not against "the
session looked fine".

**Run the whole walk once per client.** §0 and the pre-flight are shared; §2
through §6 are per-client and run twice — once with `claude`, once with `agy`.
Asymmetric breakage between them is common, and a pass on one is no evidence
for the other. Do not report the walk complete with one client run. Within a
client, walk the layers in order and stop at the first failure: a later
layer's result is uninterpretable once an earlier one is broken.

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
`capture-pane -p -S -2000`. The pass condition is an empty input prompt the
client is waiting on, with no onboarding or folder-trust dialog above it:

- `claude` — the banner block (`Claude Code v<version>`, the model line, and
  `/workspace` as cwd), then an `❯` on its own line inside the horizontal-rule
  input box. `/workspace` in the banner is also your check that the mount
  landed; any other cwd means `-d`/`-p` resolved somewhere unintended.
- `agy` — its own ready prompt with no "Do you trust the contents of this
  project?" dialog. Polecat pre-trusts `/workspace`, so that dialog appearing
  is a `setup_staging()` failure, not something to click through.

**Footer chrome is not a boot signal.** That means the two bottom lines below
the input box — the ccstatusline row (`Model: … | Ctx: … | ⎇ <branch> | (+n,-n)`)
and the mode row (`⏵⏵ auto mode on …`). Both render while the client is still
starting, so neither tells you it is ready. Read the input box, not the footer.

**§3 First prompt.** Send a trivial prompt and capture again. A hook-blocked
error is a pass for this layer, not a failure: the hook fired and reported.
Treat the error text as primary evidence. The response itself is the liveness
signal — do not build a poll loop beside it.

**§4 Exercise the path you changed.** Invoke a skill and dispatch a subagent
from inside the session — and choose ones that run through the code your change
touched, named in the sentence you wrote before §0. An arbitrary skill that
resolves proves the skill machinery works and says nothing about your change;
that is the failure this layer exists to catch. Where no shipped skill or
subagent reaches your change, drive it directly (the command, the tool call,
the hook's trigger) and say in your report that you did so. Verify visible
output in the pane, not merely that the call returned: a skill that resolves
and produces nothing passes a structural check and fails here.

**§5 Observability.** Confirm `polecat-session-hooks.jsonl` is present and
populated in the session directory, and that the PKB MCP answers rather than
refusing or timing out. The spec says what that file is evidence of, under
"Log & artifact locations". An empty or missing hook log is a finding only if
the pre-flight found hooks live; otherwise it says nothing about your change.

**§6 Cleanup.** `/exit`, then `tmux kill-session`. Confirm no container is left
behind (`docker ps` shows none for this session — `run` passes `--rm`). Then go
back to §2 for the client you have not run yet.

On failure, file one issue per root cause, not per symptom.
