---
name: debug
description: Drive and audit a real framework run -- choose an execution surface, dispatch a worker, spin up a polecat container under tmux for live interaction, and hand off to `phoenix` for what the run did. Use when asked to debug a polecat, investigate what broke a container or client mechanism (such as authentication, a token, or a service), run a polecat container interactively, attach to a polecat session, check container or session logs, or verify that a change to plugins, hooks, `lib/`, or skills actually fires inside a real container rather than merely being installed in the image. Covers both clients, `claude` and `agy`. Not the standard for scoring the run itself -- that is `dogfood`.
---

# Driving a Framework Run

Score runs under the `dogfood` skill ("Supervising a trial"). Container mechanics: [`specs/polecat/tmux-interactive-driving.md`](../../../specs/polecat/tmux-interactive-driving.md).

## Choose a Surface

Pick the cheapest surface that answers the question and name it in your report (results are only interpretable against their surface):

- **Headless `claude` or `agy`**: Simple, low-risk local checks returning to your shell.
- **Interactive polecat container (tmux)**: Isolated runs requiring live input or TUI observation.
- **Headless polecat dispatch**: `polecat_run_container` via `services` MCP or `polecat -t <id>` for isolated task execution.

Spawn independent shell agents in the background without polling or sleeping; wait for completion notifications.

## Dispatch Invariants

- **Dispatch fully specified `queued` tasks**: The launch path skips graph and eligibility checks; leaving a task at `inbox` is a creation defect.
- **Build before dispatching, never inside the container**: Containers run the baked image, not your working tree; run `make docker-build`, then dispatch.
- **Never create a git worktree**: Delegate into your current worktree or into a container.
- **Verify the executing surface, not `git status`**: `dist/` is gitignored, so a clean tree can still serve stale or modified build artifacts.

## Tracking and Epistemics

- **Refresh current-state notes**: Search the PKB for a current-state note on target surfaces, treat it as a dated observation for its named build, re-run relied cells, and rewrite the note in place.
- **Create a tracking task before return**: Link a parent in the PKB naming the dispatch, expected output, and acceptance criteria from `specs/` or the PKB (inability to locate a spec is itself a framework finding).
- **Discriminate before scoring**: Name the observation separating your verdict from the rival explanation (file `undetermined` if absent). For broken-mechanism asks (auth, tokens, services), trace the full lifecycle -- prior failing logs/traces, token refresh, state transitions, and read-only mounts -- rather than treating a fresh startup check as refutation.
- **Score tool records, never self-reports**: Verify execution via `ida:phoenix` spans, `agy` `transcript_full.jsonl` (`tool_calls`), or `claude` session JSONL (`tool_use`); agents can read stale files and report cached output as live calls.
- **Audit on completion**: Claim the tracking record, assess outputs against acceptance criteria, audit and correct the worker's task state, and route significant lessons to `learn`.

## Probes and Container Driving

- Run probes once per client (`claude` and `agy`); one passing client does not verify the other.
- Re-run an `agy` failure without `--agent` first: pass without `--agent` isolates the fault to the agent definition's `tools:` list (silent starvation to ten tools vs hard error in `agy-cli.log`).
- If running local headless probes, launching/driving/tearing down a tmux polecat container, auditing `$AOPS_SESSIONS` logs, or locating inside-container transcripts, read [references/container-recipes.md](references/container-recipes.md) before executing commands.
- If diagnosing a failure from any step, read [references/gotchas.md](references/gotchas.md) before improvising a fix.

## Validate a Dev Change

Walk these layers in order after changing `plugins/*/hooks`, `lib/`, or skills; stop at the first failure, run twice (once per client), and quote verbatim excerpts in your report:

1. **Pre-flight**: Confirm `_log_fire` and `_load_handlers` in `lib/hooks/dispatch.py` do not return early.
2. **Image freshness**: Verify the container image is fresh against its `Dockerfile`.
3. **Structural**: Confirm plugins are installed in the container image.
4. **Boot signals**: `claude` renders banner and `❯` in `/workspace`; `agy` clears the 2-3 s auth race and renders its plan name.
5. **First prompt**: Send a tool-calling prompt and assert the model output or tool-call record in the pane or transcript.
6. **Exercise changed path**: Invoke the modified skill, hook, or tool call and capture execution output.
7. **Audit**: Verify non-error `TOOL` spans via `ida:phoenix` and run the host filesystem audit (`run.json` and `polecat-session-hooks.jsonl`).
8. **Teardown**: Send `/exit`, wait for transcript flush (`sleep 2`), and kill the tmux session.
