---
name: debug
description: Drive and audit a real framework run — choose an execution surface, dispatch a worker, spin up a `polecat run` container under tmux for live interaction, and pull authoritative telemetry from the Phoenix MCP span store. Use when asked to debug a polecat, run a polecat container interactively, attach to a polecat session, check container or session logs, establish what a session actually did, or verify that a change to plugins, hooks, `lib/`, skills, or the Dockerfile actually fires inside a real container rather than merely being installed in the image. Covers both clients, `claude` and `agy`. Not the standard for scoring the run itself — that is `dogfood`.
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

## Scripted probes

[`scripts/probe.sh`](scripts/probe.sh) drives one question;
[`scripts/matrix-probe.sh`](scripts/matrix-probe.sh) drives a capability matrix
— MCP reachability, skill resolution, subagent dispatch, permissions — and
prints PASS/FAIL per cell. Both take the client as their first argument. Run
them once per client; a pass on one is no evidence for the other. Whether the
plugins are installed at all is `make docker-smoke-test`.

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
`executeSql`, `tool_calls` in agy's `transcript_full.jsonl`, or `tool_use` in
claude's session jsonl. That is what `matrix-probe.sh`'s MCP cell does.

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
export POLECAT_HOME="${POLECAT_HOME:-$HOME/.polecat}"
export POLECAT_IMAGE="${POLECAT_IMAGE:-ghcr.io/nicsuzor/aops-crew:latest}"
export AOPS_SESSIONS="${AOPS_SESSIONS:-$HOME/src/sessions}"
export GEMINI_CONFIG_DIR="${GEMINI_CONFIG_DIR:-$HOME/.gemini}"
export GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-AcademicOps Bot}"
export GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-bot@academicops.org}"
export AOPS_BOT_GH_TOKEN="${AOPS_BOT_GH_TOKEN:-dummy_token_for_test}"

exec uv run --project "$CHECKOUT" python "$CHECKOUT/lib/polecat/cli.py" \
  run -d "$CHECKOUT" -s "$TMUX_NAME" claude -- -p "call pkb get_status() and return results"
EOF
chmod +x "$LAUNCH_SCRIPT"

tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 "$LAUNCH_SCRIPT"
```

- **Always place `--` before the agent's own flags and prompt**, because
  `lib/polecat/cli.py` defines `@click.option("-p", "--project")` on `run` and
  Click otherwise swallows the agent's `-p`:

  ```bash
  uv run python lib/polecat/cli.py run -p <project> -s <session> claude -- -p "call pkb get_status() and return results"
  uv run python lib/polecat/cli.py run -p <project> -s <session> agy -- -p "call pkb get_status() and return results"
  ```

- **Always pass `-x 220 -y 50`** to `tmux new-session`, so TUI headers, input
  boxes, and status lines render without wrapping corruption.

Client differences that change how you drive: `agy` needs `$GEMINI_CONFIG_DIR`
staged with an `antigravity-oauth-token`, renders
`⚠ Verifying your account...` for 2–3 s before its header plan name
(`username (Google AI Ultra)`) appears, writes its logs to files rather than
stdout, and requires an explicit `-i`/`--prompt-interactive` or `-p`/`--print`
where `claude` accepts a positional prompt. Both take `--agent <name>`
(`@orchestrate:james` for `claude`, `james` for `agy`).

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

Teardown — container cleanup is automatic, because `lib/polecat/cli.py` invokes
`docker run --rm`:

```bash
tmux send-keys -t "$TMUX_NAME" -l "/exit"; tmux send-keys -t "$TMUX_NAME" Enter
sleep 2   # let the client flush its transcript buffer through the bind-mount
tmux kill-session -t "$TMUX_NAME" 2>/dev/null || true
```

## Authoritative telemetry (Phoenix MCP)

Phoenix is the durable telemetry store: untruncated payload attributes, exact
millisecond latencies, and full OpenTelemetry span trees, where local markdown
transcripts truncate tool inputs and outputs at ~300 characters. Use the
`phoenix` MCP server's `executeSql`, `getSpans`, `listProjectTraces`, and
`execute`.

### Classify the identifier before you query

Searching `session.id` with a `trace_id` returns `{"data":[],"next_cursor":null}`
silently, which reads as "telemetry not retained" and is not.

| Identifier       | Shape                       | Example                                | Query pattern                                                         |
| ---------------- | --------------------------- | -------------------------------------- | --------------------------------------------------------------------- |
| **`trace_id`**   | 32 hex chars, **no dashes** | `c75f0a20a67140e791244eb5dfa64be5`     | `WHERE trace_id = '<32_HEX>'` — resolve to `session.id` via Recipe A0 |
| **`session.id`** | 36 chars, **dashed UUID**   | `22ec8f3e-72c1-4b15-9988-123456789abc` | `WHERE JSON_EXTRACT(attributes, '$.session.id') = '<UUID>'`           |
| **session slug** | 6–8 hex chars               | `22ec8f3e`                             | `WHERE JSON_EXTRACT(attributes, '$.session.id') LIKE '%<slug>%'`      |
| **`span_id`**    | 16 hex chars, **no dashes** | `a1b2c3d4e5f60718`                     | `WHERE span_id = '<16_HEX>'`                                          |

A query returning 0 rows is a reason to re-check the identifier's shape, never
by itself a finding that data was dropped.

### SQL recipes

The backend is an allowlisted SQLite database; use JSON extraction (`->>` or
`JSON_EXTRACT`).

**A0 — resolve a `trace_id` to its `session.id`.** Then pivot every subsequent
query onto `session.id`.

```sql
SELECT JSON_EXTRACT(attributes, '$.session.id') AS session_id,
       project_name, COUNT(*) AS span_count,
       MIN(start_time) AS first_seen, MAX(start_time) AS last_seen
FROM spans
WHERE trace_id = '<32_HEX_TRACE_ID>'
GROUP BY session_id, project_name
```

**A — session discovery and error check.**

```sql
SELECT JSON_EXTRACT(attributes, '$.session.id') AS session_id,
       COUNT(*) AS span_count,
       SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) AS error_count,
       MIN(start_time) AS first_seen, MAX(start_time) AS last_seen
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') LIKE '%<SESSION_SLUG_OR_UUID>%'
GROUP BY session_id
ORDER BY last_seen DESC
LIMIT 10
```

**B — chronological execution.** Add `AND span_kind = 'TOOL'` to audit tool
calls only; swap the `SUBSTRING(...)` for the bare column to read payloads
whole.

```sql
SELECT span_id, parent_id, name, span_kind, status_code, latency_ms,
       SUBSTRING(attributes->>'input.value', 1, 120) AS input_preview,
       SUBSTRING(attributes->>'output.value', 1, 120) AS output_preview
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
ORDER BY start_time ASC
```

**C — errors and tool failures, untruncated.**

```sql
SELECT span_id, name, span_kind, status_message, latency_ms,
       attributes->>'input.value' AS full_input,
       attributes->>'output.value' AS full_output
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
  AND status_code = 'ERROR'
ORDER BY start_time ASC
```

**D — tool-call fingerprint.** Proves what the agent actually invoked, against
what it claims.

```sql
SELECT name, COUNT(*) AS invocations,
       ROUND(AVG(latency_ms), 1) AS avg_ms, MAX(latency_ms) AS max_ms
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
  AND span_kind = 'TOOL'
GROUP BY name
ORDER BY invocations DESC
```

Ground every claim about what a report asserts in these spans, and distinguish
the two zero cases when you write it up. Zero tool calls for an item is
"the agent did not execute actions for these items", not "these items are not
done". One fuzzy `task_search` returning nothing is a search miss, not proof the
target does not exist.

**E — token accounting and cache ratio.**

```sql
SELECT name,
       SUM(llm_token_count_prompt) AS prompt_tokens,
       SUM(llm_token_count_completion) AS completion_tokens,
       SUM(CAST(JSON_EXTRACT(attributes, '$.\"llm.prompt_details.cache_read\"') AS INTEGER)) AS cache_read_tokens
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
  AND span_kind = 'LLM'
GROUP BY name
```

**F — correlate a spawned subagent's own session.** The child carries no
attribute pointing at the parent. Match its root turn to the exact prompt text
the parent's `Agent` call sent (visible in the parent's `AGENT` span, Recipe G)
and to time proximity — the child's first span lands within seconds. A named
subagent's root turn opens `<teammate-message teammate_id="team-lead">...`, so
match on the tail of the parent's prompt. Then pull the child's full span list
with Recipe B.

```sql
SELECT JSON_EXTRACT(attributes, '$.session.id') AS session_id, span_id, start_time,
       SUBSTR(attributes->>'input.value', 1, 300) AS input_preview
FROM spans
WHERE span_kind = 'CHAIN' AND (parent_id IS NULL OR parent_id = '')
  AND start_time >= '<WINDOW_START>+00:00' AND start_time <= '<WINDOW_END>+00:00'
  AND attributes->>'input.value' LIKE '%<DISTINCTIVE PHRASE FROM THE PROMPT>%'
ORDER BY start_time ASC
```

**G — dispatch-mode fingerprint.** Read the `AGENT` spans' `output.value` to
tell a named host teammate from a background task from a container.

```sql
SELECT span_id, status_code, latency_ms, start_time,
       attributes->>'output.value' AS full_output
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<PARENT_SESSION_UUID>'
  AND span_kind = 'AGENT'
ORDER BY start_time ASC
```

- **Named teammate (host)** — output is
  `{"status": "teammate_spawned", "teammate_id": "<name>@session-<slug>", "agent_type": "...", "tmux_session_name": "...", ...}`
  and it emits `<teammate-message>` turns to the parent. A payload
  `{"type":"idle_notification","idleReason":"available"}` is the teammate bus,
  which polecat containers cannot reach — so seeing it proves the worker was a
  named host session, not a container. `available` means only that the agent
  finished its turn with an empty queue; it claims nothing about what got done.
  The `AGENT` span closes in ~150–250 ms on spawn acknowledgement and has no
  OTel close event, so never read its duration as the worker's runtime.
- **Unnamed background task** — output is
  `{"isAsync": true, "status": "async_launched", "agentId": "...", "outputFile": "...", "canReadOutputFile": false}`.
  This mode does have an OTel-visible close: search the parent session for
  `attributes->>'input.value' LIKE '%task-notification%'` to find
  `<task-notification><status>completed</status>...<usage><duration_ms>N</duration_ms></usage></task-notification>`.
- **Polecat container** — writes `$AOPS_SESSIONS/logs/.../run.json`,
  `polecat-session-hooks.jsonl`, and container stdout logs. Never emits teammate
  bus messages.

**H — did the agent structurally have the tool it needed?** Before concluding a
silent agent "failed to report", check whether it ever called the tool
reporting requires, and whether its `agent_type` even grants it.

```sql
SELECT name, span_kind, COUNT(*) AS n
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<CHILD_SESSION_UUID>'
GROUP BY name, span_kind
ORDER BY n DESC
```

Zero `SendMessage`/`send_message` rows in a named-teammate session, alongside
real work in `Bash` and other tool spans and `status_code: UNSET` throughout,
means the agent did its job and had no channel to report it. Cross-check the
agent type's declared `Tools:` allowlist before attributing silence to a bug in
its behaviour rather than its tool grant.

Phoenix's `execute` tool runs an async Python block that can `await
call_tool("executeSql", {"sql": ...})` several times and return one object — use
it to collapse a multi-query pass into a single round-trip.

### Telemetry invariants

- **Filter on `attributes->>'session.id'` (or `session_identifier`), never on
  `trace_id`.** OTel context propagates across inter-agent messages, so one
  trace can span several sessions and a trace-scoped query pulls foreign work
  into your view. Use `trace_id` only to resolve the session (Recipe A0).
- **No parent↔child linking attribute exists.** A spawned subagent's session
  never carries the parent's id. Correlate by prompt text and time window
  (Recipe F); substring-searching for the parent UUID finds only sessions that
  _mention_ it in conversation text.
- **`turn_number` is per-tracer-state** and resets across subagents. Sort
  by `start_time` for session-wide chronology.
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

Run this after modifying `plugins/*/hooks`, `lib/`, skills,
`lib/polecat/cli.py`, `entrypoint.sh`, or the Dockerfile. Walk the layers in
order and stop at the first failure. Run the whole walk twice, once per client.
Quote verbatim excerpts from `capture-pane`, session logs, and Phoenix output in
your report.

1. **Pre-flight** — confirm `_log_fire` and `_load_handlers` in
   `lib/hooks/dispatch.py` are not returning early.
2. **§0 image freshness** — `make docker-build`, then `make verify-docker`.
3. **§1 structural** — `make docker-smoke-test` confirms the plugins are
   installed in the image.
4. **§2 boot signals** — `claude`: banner and `❯` box render inside
   `/workspace`. `agy`: the 2–3 s auth race clears and the plan name renders.
5. **§3 first prompt** — send a prompt (e.g. `"call pkb get_status() and return
   results"`) and **assert the model output string or the tool-call record** in
   the pane or transcript. A rendered prompt box is not proof of success.
6. **§4 exercise the changed path** — invoke the specific changed skill, hook,
   or tool call and capture the execution output.
7. **§5 audit** — `SELECT count(*) FROM spans WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'`
   in Phoenix; assert `TOOL` spans exist with `status_code != 'ERROR'`. Then the
   host filesystem audit above.
8. **§6 teardown** — `/exit`, `sleep 2`, kill the session.

## Diagnostic gotchas

| Symptom                                                                       | Cause                                                                                              | Fix                                                                                                                               |
| ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `no server running on /tmp/tmux-...`                                          | Inline tmux command failed in `/bin/sh -c` on quoting or missing PATH exports                      | Use the `/tmp/launch-$TMUX_NAME.sh` wrapper                                                                                       |
| Session log directory named after the prompt string                           | `-p` passed after `run` without `--`; Click parsed it as `--project`                               | Put `--` before agent flags and prompts                                                                                           |
| `agy` stuck at a Google OAuth prompt                                          | `GEMINI_CONFIG_DIR` missing or lacks `antigravity-oauth-token`                                     | Set `GEMINI_CONFIG_DIR=~/.gemini` and ensure the token exists                                                                     |
| `docker logs <container>` empty for `agy`                                     | `agy` redirects to internal log files                                                              | Read `$AOPS_SESSIONS/.../agy-cli.log`                                                                                             |
| `fatal: not a git repository` in the container                                | `-d` was given a linked git worktree, whose `.git` file points outside the mount                   | Use a full clone for `-d`, or register a project mapping in `$POLECAT_HOME/local.yaml` and pass `-p <project>`                    |
| Premature `agy` boot-failure report                                           | Pane captured during the 2–3 s `⚠ Verifying your account...` race                                  | Wait for the header plan name before inspecting                                                                                   |
| MCP tool calls missing from the agent's response                              | The agent grepped answers off disk instead of executing tools                                      | `SELECT count(*) FROM spans WHERE span_kind='TOOL' AND attributes->>'session.id'='<UUID>'`                                        |
| `⚠ Agent execution terminated due to error` + an error ID, nothing else       | agy agent frontmatter names a tool absent from its registry                                        | `grep "not found in registry" <session>/agy-cli.log`; drop the offending names from `build/tool_map.toml`'s `accepted_tools`      |
| Headless `agy` returns `"error":"context canceled"` with work half-done       | Job outran `--print-timeout` (default `5m0s`)                                                      | Compare `duration_seconds` against the timeout; re-run with an explicit `--print-timeout`                                         |
| `delivery_guard_failed` after a probe that wrote files                        | The probe's own artefacts are uncommitted in the workspace                                         | Expected for a write probe; confirm the named files are the probe's before treating it as a defect                                |
| Named subagent never returns / repeats `idle_notification` forever            | `name` on the `Agent` call spawns a persistent teammate with no OTel-visible exit event (Recipe G) | Do not wait on the tool call; watch the parent for an inbound `<teammate-message>`, and check the child's own session (Recipe F)  |
| Named subagent did real work but never reported it                            | Its `agent_type`'s allowlist has no `SendMessage` — the only delivery channel in teammate mode     | Recipe H: confirm zero `SendMessage` spans, then check the declared `Tools:` — a capability gap, not a hang                       |
| `executeSql` result "exceeds maximum allowed tokens", dumped to a `.txt` file | Query returned too many rows, or unbounded `input.value`/`output.value` columns                    | Narrow with `SUBSTR(...)` and a tighter `WHERE`/`LIMIT`; if already dumped, read the saved file with `jq` rather than re-querying |
| `{"data":[],"next_cursor":null}` searching for a session by id                | Queried `session.id` with a 32-hex `trace_id`                                                      | Resolve via `WHERE trace_id = '<32_HEX>'` (Recipe A0) first                                                                       |
| Report asserts items "not done" or "failed" with no tool evidence             | Agent assumed the outcome after 0 tool calls or a single search miss                               | Recipe D: distinguish 0 tool calls (never attempted) from tool executions that failed                                             |
