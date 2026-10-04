---
name: debug
description: Drive and audit a real framework run — choose an execution surface, dispatch a worker, spin up a polecat container under tmux for live interaction, and pull authoritative telemetry from the Phoenix span store via the `services` MCP proxy. Use when asked to debug a polecat, run a polecat container interactively, attach to a polecat session, check container or session logs, establish what a session actually did, or verify that a change to plugins, hooks, `lib/`, or skills actually fires inside a real container rather than merely being installed in the image. Covers both clients, `claude` and `agy`. Not the standard for scoring the run itself — that is `dogfood`.
---

# Driving a framework run

The standard you hold while scoring a run is [`dogfood`](../dogfood/SKILL.md),
"Supervising a trial". This file is how you drive one. Container mechanics and
gotchas: [`specs/polecat/tmux-interactive-driving.md`](../../../specs/polecat/tmux-interactive-driving.md).

## Choose a surface

Pick the cheapest surface that answers the question, and name it in your report
— a result is only interpretable against the surface that produced it.

- **Headless `claude` or `agy`** for simple, low-risk work, with results
  returned to your own shell. To watch a local agent read-only:
  `agy --agent james --print "<prompt>"`
- **A polecat container** when the work needs isolation. Driving one
  interactively is the rest of this file.
- **The `pc` launcher with a task id** for complex work you will not supervise.
  It is fire-and-forget: results do not come back to you and you get no
  completion notification either way.

Spawn independent agents from `Bash` in the background. Do not poll and do not
sleep — go idle and read the result when the completion notification arrives.

## Dispatch so the run is worth scoring

- **A dispatchable task is yours to produce.** Dispatch tasks that are fully
  specified and `queued`. Nothing on the launch path reads the graph or checks
  eligibility, so a task left at `inbox` is a defect in how you created it, not
  in the launcher. Amend the launcher's own instructions only when the task
  record genuinely cannot carry the fix.
- **Build the image before you dispatch, never inside it.** A container runs the
  framework baked into its image, not the tree you are sitting in, and nothing
  on the launch path checks freshness. The loop is `make docker-build`, then
  dispatch against the fresh image.
- **Never create a git worktree.** Delegate into the worktree you are already
  in, or into a container.
- **`git status` is not a cleanliness check.** The framework runs from `dist/`,
  which is gitignored. A worker that reverts tracked source and reports a clean
  tree can still have left its probe in every built artifact and in the image.
  Verify the surface that actually executes.

## Hold the run's acceptance criteria on a tracking record

Search the PKB first for a current-state note on the surfaces you are about to
test: which were last observed working, which failing, against which build. Read
it as an observation with a date on it, not as fact — it was true of the build
it names. Re-run the cells you will rely on, and when you finish rewrite that
note rather than adding a second one beside it; a stale state note reads as
current, so it is worse than none.

Before the worker returns, create a tracking task in the PKB, with a parent,
naming what was dispatched, the output expected, and how you will test it
against the acceptance criteria that apply. Find those criteria while the worker
runs — a spec you cannot locate in `specs/` or the PKB within a few calls is
itself a framework failure, and that is the finding.

Before recording that anything passed or failed, name the observation that
discriminates it from the alternative explanation; where none was made, file
`undetermined` rather than a verdict. A silent agent is equally consistent with
work finished and unreported.

On completion: claim the record, review the output against those criteria, and
write your assessment onto it. Check that the worker updated its own task
honestly and correct the record where it did not, or reassign the work where the
record cannot be corrected into a true one. Where the run produced a significant
failure or an unexpected success, `learn` turns it into a lesson.

## Probes

Run probes once per client; a pass on one is no evidence for the other.

**Re-run an agy failure without `--agent` before you believe it.** If a probe
fails under `--agent <name>` and passes without it, the agent definition is
broken, not the surface. The usual cause is the frontmatter `tools:` list, which
fails in two directions:

- **Absent or empty → silent starvation.** agy restricts the agent to ten
  read-only tools and boots normally. Nothing errors; the agent simply has no
  `write_to_file`, `run_command` or `invoke_subagent`, improvises, and reports a
  plausible failure of its own. Make "list your own callable tools" step one of
  any probe — a ten-name list is the tell.
- **Naming a tool agy does not register → hard failure.** The pane shows only
  `⚠ Agent execution terminated due to error.` with an error ID; the real
  message is in `agy-cli.log`:
  `failed to resolve components: unknown component: tool "<name>" not found in registry`.
  One bad name kills the whole agent, so read that log before concluding
  anything from the pane.

**Never score a capability on what the agent says.** Ask an agent for a server's
output and it will grep that output out of any file lying around — including the
logs, task outputs and transcripts your own probing left behind — and report it
as though it had made the call. Score the tool-call record instead: Phoenix
`executeSql` (via `phoenix_execute`), `tool_calls` in agy's
`transcript_full.jsonl`, or `tool_use` in claude's session jsonl. That is what
authoritative MCP verification checks.

## Launch a container under tmux

Write the invocation into a launch script rather than passing an inline command
string to `tmux new-session`: inline commands break on shell expansion, nested
quoting, and virtualenv path resolution (`uv run python`) inside `/bin/sh -c`.

```bash
CHECKOUT="$(git rev-parse --show-toplevel)"
export TMUX_NAME="polecat-debug-$RANDOM"
LAUNCH_SCRIPT="/tmp/launch-${TMUX_NAME}.sh"

cat > "$LAUNCH_SCRIPT" <<EOF
#!/usr/bin/env bash
export POLECAT_IMAGE="${POLECAT_IMAGE:-polecat:latest}"

# Run via dotfiles host launcher (scripts/polecat):
exec polecat -d "$CHECKOUT" -s "$TMUX_NAME" -i -- claude -p "call pkb get_status() and return results"
EOF
chmod +x "$LAUNCH_SCRIPT"

tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 "$LAUNCH_SCRIPT"
```

- **Always place `--` before the agent's own flags and prompt**:

  ```bash
  polecat -d "$CHECKOUT" -s "$TMUX_NAME" -i -- claude -p "call pkb get_status() and return results"
  polecat -d "$CHECKOUT" -s "$TMUX_NAME" -i -- agy -p "call pkb get_status() and return results"
  ```

- **Always pass `-x 220 -y 50`** to `tmux new-session`, so TUI headers, input
  boxes, and status lines render without wrapping corruption.

Client differences that change how you drive: `agy` needs `$GEMINI_CONFIG_DIR`
staged with an `antigravity-oauth-token`, renders
`⚠ Verifying your account...` for 2–3 s before its header plan name
(`username (Google AI Ultra)`) appears, writes its logs to files rather than
stdout, and requires an explicit `-i`/`--prompt-interactive` or `-p`/`--print`
where `claude` accepts a positional prompt. Both take `--agent <name>`
(`@aops:james` for `claude`, `james` for `agy`).

## Drive it

```bash
# Readiness: poll the pane. claude — wait for the '❯' prompt box.
# agy — wait 2-3s for the auth race to clear and the plan name to render.
tmux capture-pane -t "$TMUX_NAME" -p -S -2000

# Send prompt text with -l (literal), so tmux does not parse it as keys.
tmux send-keys -t "$TMUX_NAME" -l "your prompt text here"
tmux send-keys -t "$TMUX_NAME" Enter

# TUI menu navigation (e.g. AskUserQuestion)
tmux send-keys -t "$TMUX_NAME" Down Down Enter
```

`capture-pane` reflects what an attached user sees. It is an ephemeral buffer
that dies with the tmux session, so capture anything you intend to cite.

Teardown — container cleanup is automatic with `--rm`:

```bash
tmux send-keys -t "$TMUX_NAME" -l "/exit"; tmux send-keys -t "$TMUX_NAME" Enter
sleep 2   # let the client flush its transcript buffer through the bind-mount
tmux kill-session -t "$TMUX_NAME" 2>/dev/null || true
```

## Authoritative telemetry (Phoenix via services MCP)

Phoenix is the durable telemetry store: untruncated payload attributes, exact
millisecond latencies, and full OpenTelemetry span trees, where local markdown
transcripts truncate tool inputs and outputs at ~300 characters. Phoenix is not
a separate MCP server; it is reached through the `services` MCP proxy via its
code-mode interface (`portal_codemode_execute`, or `mcp__services__portal_codemode_execute`).

Call `codemode.phoenix_execute` with an async Python block that invokes Phoenix tools
via `await call_tool(tool_name, params)`:

- `await call_tool("executeSql", {"sql": "..."})` to query allowlisted SQLite span-store tables.
- `await call_tool("getSpans", {...})` and `await call_tool("listProjectTraces", {...})` for span/trace enumeration.
- Discovery: `portal_codemode_search` (filtering for `phoenix`), `phoenix_list_tools`, or `describeSqlSchema`.

Read [`../../../lib/telemetry/phoenix-span-store.md`](../../../lib/telemetry/phoenix-span-store.md)
before writing any query — it holds the identifier-shape table
(`trace_id`/`session.id`/slug/`span_id`), the rule to filter on `session.id`
and never `trace_id`, why `turn_number` is not a reliable counter, and why a
`teammate_spawned` span's duration is not the worker's runtime. Then read
[`references/sql-recipes.md`](references/sql-recipes.md) for the query
recipes (A0 through H) that apply those facts.

### Telemetry invariants specific to this store

- **No parent↔child linking attribute exists.** A spawned subagent's session
  never carries the parent's id. Correlate by prompt text and time window
  (Recipe F, in `references/sql-recipes.md`); substring-searching for the
  parent UUID finds only sessions that _mention_ it in conversation text.
- **Bare timestamps are rejected.** `start_time >= '2026-08-19 22:12:00'` fails
  with `unsupported_syntax`; a time of day needs an explicit offset
  (`'2026-08-19 22:12:00+00:00'`). A bare date is accepted and read as UTC.
- **A container run emitting only `CHAIN` spans** with zero `TOOL`/`LLM` spans
  means telemetry is not being forwarded — check
  `GENAI_ENGINE_TRACE_ENDPOINT` in the container's environment.

## Host filesystem audit

Container artifacts land at
`$AOPS_SESSIONS/logs/<YYYYMMDD>/<session-id>/workspace/`.

```bash
SESS_DIR="$AOPS_SESSIONS/logs/$(date +%Y%m%d)/$TMUX_NAME/workspace"
jq '{schema_version, status, exit_code, delivery_guard, transcript, degraded}' "$SESS_DIR/run.json"
jq -c '.' "$SESS_DIR/polecat-session-hooks.jsonl" | head -n 10
uv run pytest tests/transcripts/test_polecat_discovery.py -v
```

Pass assertions: `run.json` has `.schema_version == 1`, `.status == "success"`,
`.delivery_guard.ok == true`, and `.transcript.found == true` with
`event_count > 0`. Every `polecat-session-hooks.jsonl` line conforms to the
five-field schema `ts` (ISO 8601, microsecond UTC), `client` (`claude`|`agy`),
`event`, `session_id`, `tool`.

## Read durable state from inside a container

`$AOPS_SESSIONS` is never forwarded into a single-repository container, so every
path above names a host directory you cannot reach. What you can reach is each
client's own state root:

| Whose conversation               | Where it lands inside the container                                                                                           |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Yours, under `claude`            | `$CLAUDE_CONFIG_DIR/projects/<slugified-cwd>/<session-uuid>.jsonl`, else `~/.claude/projects/...`                             |
| A worker you spawned via `Agent` | `<the same project dir>/<your-session-uuid>/subagents/agent-*.jsonl`, with a `.meta.json` beside it naming the agent that ran |
| An `agy` worker you launched     | `~/.gemini/antigravity-cli/brain/<conversation-id>/.system_generated/logs/transcript.jsonl` and `transcript_full.jsonl`       |

`$AOPS_SESSION_STATE_DIR` names the host-mounted directory, so
`polecat-session-hooks.jsonl` sits beside your own transcript and is readable
live. `run.json` is not there: the host writes it after the container exits.

List all of them, newest first, tagged by client, kind, agent, and parent
session — `--kind subagent` narrows to workers, `--json` makes it
machine-readable:

```bash
PYTHONPATH="$(git rev-parse --show-toplevel)/lib/py" uv run python -m transcripts.discovery --kind subagent
```

Then read the JSONL each row names. A worker's `tool_use` records are what you
score its claims against; its own report is not evidence that anything ran.

## Validate a dev change

Run this after modifying `plugins/*/hooks`, `lib/`, or skills. Walk the layers in
order and stop at the first failure. Run the whole walk twice, once per client.
Quote verbatim excerpts from `capture-pane`, session logs, and Phoenix output in
your report.

1. **Pre-flight** — confirm `_log_fire` and `_load_handlers` in
   `plugins/ida/hooks/dispatch.py` are not returning early.
2. **§0 image freshness** — verify container image freshness against the `Dockerfile` it was built from.
3. **§1 structural** — confirm plugins are installed in the container image.
4. **§2 boot signals** — `claude`: banner and `❯` box render inside
   `/workspace`. `agy`: the 2–3 s auth race clears and the plan name renders.
5. **§3 first prompt** — send a prompt (e.g. `"call pkb get_status() and return
   results"`) and **assert the model output string or the tool-call record** in
   the pane or transcript. A rendered prompt box is not proof of success.
6. **§4 exercise the changed path** — invoke the specific changed skill, hook,
   or tool call and capture the execution output.
7. **§5 audit** — `SELECT count(*) FROM spans WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'`
   in Phoenix via `services` `phoenix_execute`; assert `TOOL` spans exist with `status_code != 'ERROR'`. Then the
   host filesystem audit above.
8. **§6 teardown** — `/exit`, `sleep 2`, kill the session.

## Diagnostic gotchas

Read [`references/gotchas.md`](references/gotchas.md) for the symptom → cause
→ fix table before improvising a fix to any of the failures above.
