---
name: debug
description: Use when driving a framework run you intend to score — choosing a surface, dispatching a worker, or when asked to "debug a polecat", "run a polecat container interactively", "attach to a polecat session", "check polecat logs", or to verify that a change to plugins, hooks, lib/, skills, or the Dockerfile actually works inside a real container. Spins up a `polecat run` container under tmux for live interaction, leverages the Phoenix MCP server for authoritative telemetry and session debugging, and walks the layered check that separates "installed in the image" from "actually fires".
---

# Driving a framework run — surfaces, dispatch, and interactive debugging

The standard you hold while scoring a run is the [`dogfood`](../dogfood/SKILL.md) skill's "Supervising a trial". This file is how you drive one.

Mechanics and gotchas for the container surface: [`specs/polecat/tmux-interactive-driving.md`](../../../specs/polecat/tmux-interactive-driving.md).

## Choose a surface

Pick the cheapest surface that answers the question, and name it in your report — a result is only interpretable against the surface that produced it.

- **Headless `claude` or `agy`** for simple, low-risk work, with results returned to your own shell. To watch a local agent read-only: `agy --agent james --print "<prompt>"`
- **A polecat container** when the work needs isolation. Driving one interactively is the rest of this file.
- **The `pc` launcher with a task id** for complex work you will not supervise. It is fire-and-forget: results do not come back to you and you get no notification of completion, successful or otherwise.

Spawn independent agents from `Bash` in the background. Do not poll and do not sleep — go idle, and read the result when the completion notification arrives.

## Dispatching so the run is worth scoring

- **A dispatchable task is yours to produce.** Dispatch tasks that are fully specified and `queued`. A task you left at `inbox` is not dispatchable, and that is a defect in how you created it, not in the launcher — nothing on the launch path reads the graph or checks eligibility. Set the status and properties correctly, then dispatch. Amend the launcher's own instructions only when the task record genuinely cannot carry the fix.
- **Build the image before you dispatch, never inside it.** A container runs the framework baked into its image, not the tree you are sitting in, and nothing on the launch path checks freshness. The loop is `make docker-build`, then dispatch against the fresh image.
- **Never create a git worktree.** Delegate into the worktree you are already in, or into a container. Spawning a worktree to sidestep a collision is a workaround, and you do not have authority to invent one.
- **`git status` is not a cleanliness check.** The framework runs from `dist/`, which is gitignored. A worker that reverts tracked source and reports a clean tree can still have left its probe in every built artifact and in the image. Verify the surface that actually executes.

## Hold the run's acceptance criteria on a tracking record

Before the worker returns, create a tracking task in the PKB naming what was dispatched, the output expected, and how you will test it against the acceptance criteria that apply. Give it a parent. Find those criteria while the worker runs — a spec you cannot locate in `specs/` or the PKB within a few calls is itself a framework failure, and that is the finding.

Before recording that anything passed or failed, name the observation that discriminates it from the alternative explanation; where none was made, file `undetermined` rather than a verdict. A silent agent is equally consistent with work finished and unreported — look for the work before you conclude anything about the agent.

On completion: claim the record, review the output against those criteria, and write your assessment onto it. Check that the worker updated its own task honestly, and correct the record where it did not — or reassign the work where the record cannot be corrected into a true one. Where the run produced a significant failure or an unexpected success, `learn` is what turns it into a lesson.

## Before you drive anything, find out what is already known

Search the PKB for a current-state note on the surfaces you are about to test — which ones were last observed working, which were failing, and against which build. Someone has usually already spent a session establishing that, and a matrix you re-derive by hand is a matrix you pay for twice.

Read what you find as an observation with a date on it, not as fact: it was true of the build it names. Re-run the cells you are about to rely on, and when you finish, rewrite that note rather than adding a second one beside it. A stale state note is worse than none, because it reads as current.

## Scripted probes

[`scripts/probe.sh`](scripts/probe.sh) drives one question; [`scripts/matrix-probe.sh`](scripts/matrix-probe.sh) drives a capability matrix — MCP, skills, subagent dispatch, permissions — and prints PASS/FAIL per cell. Both take the client as their first argument, so the same command covers both surfaces. Run them once per client; a pass on one is no evidence for the other. They cover MCP reachability, skill resolution, subagent dispatch and permissions; whether the plugins are installed at all is `make docker-smoke-test`.

**Re-run an agy failure without `--agent` before you believe it.** If a probe fails under `--agent <name>` and passes without it, the agent definition is what is broken, not the surface. The usual cause is the frontmatter `tools:` list, which fails in two directions with two different signatures:

- **Absent or empty → silent starvation.** agy restricts the agent to ten read-only tools and boots normally. Nothing errors; the agent simply has no `write_to_file`, `run_command` or `invoke_subagent`, improvises with what is left, and reports a plausible failure of its own. Ask the agent to list its own callable tools as step one of any probe — a ten-name list is the tell.
- **Naming a tool agy does not register → hard failure.** The pane shows only `⚠ Agent execution terminated due to error.` with an error ID; the real message is in `agy-cli.log`: `failed to resolve components: unknown component: tool "<name>" not found in registry`. One bad name kills the whole agent, so always read that log before concluding anything from the pane.

**Never score a capability on what the agent says.** Ask an agent for a server's output and it will grep that output out of any file lying around — including the logs, task outputs and transcripts your own probing leaves behind — and report it as though it had made the call. Score the tool-call record instead — via Phoenix MCP SQL telemetry (`executeSql`), `tool_calls` in agy's `transcript_full.jsonl`, or `tool_use` in claude's session jsonl — which is what `matrix-probe.sh`'s MCP cell does.

## Spin Up: Launch Script Pattern & Driving Harness

Always write your container invocation into a launch script `/tmp/launch-$TMUX_NAME.sh` rather than passing inline command strings to `tmux new-session`. Inline commands fail when shell expansion, nested quoting, or virtualenv path resolution (`uv run python`) break inside `/bin/sh -c`.

### 1. The Canonical Launch Script Pattern

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

### 2. Mandatory Click `--` (Double-Dash) Parameter Separator

`lib/polecat/cli.py` defines `@click.option("-p", "--project")` on the `run` command.

If you pass `-p` after `run` without using `--` (e.g. `run -d <dir> -s <sess> claude -p "prompt"`), Click intercepts `-p` as `run`'s `--project` parameter, creating a session log folder named after the prompt text!

To prevent Click option collisions, **always place `--` (double-dash) before agent parameters and prompts**:

```bash
# CORRECT: Double-dash isolates inner agent flags from Click option parsing
uv run python lib/polecat/cli.py run -p <project> -s <session> claude -- -p "call pkb get_status() and return results"
uv run python lib/polecat/cli.py run -p <project> -s <session> agy -- -p "call pkb get_status() and return results"
```

### 3. Driving Parameters & Tmux Session Mechanics

- **Explicit Window Dimensions**: Always pass `-x 220 -y 50` when calling `tmux new-session`. This ensures consistent pane geometry so TUI headers, input boxes, and status lines render without wrapping corruption.
- **Git Worktree Gotcha**: Never pass a linked git worktree directory to `-d`. Linked worktrees contain a `.git` file referencing `.git/worktrees/<name>` outside the mounted container directory, causing all container git commands to fail with `fatal: not a git repository`. Use a full clone checkout with `-d`, or register a project mapping in `$POLECAT_HOME/local.yaml` and pass `-p <project>`.

## Client Asymmetries (`claude` vs `agy`)

The two agent clients exhibit significant operational and diagnostic asymmetries:

| Dimension                    | Claude Code (`claude`)                                              | Antigravity CLI (`agy`)                                                                                                         |
| ---------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Authentication & Staging** | Configured via `.claude/settings.json` and API keys in environment. | Requires `$GEMINI_CONFIG_DIR` staging via `setup_staging()` (`antigravity-oauth-token`). Without it, boots into OAuth wall.     |
| **Startup Rendering Race**   | Immediate rendering of model banner and `❯` input prompt.           | Renders `⚠ Verifying your account...` for 2–3 seconds before header plan name (`username (Google AI Ultra)`) appears.           |
| **Logging Surface**          | Native stdout/stderr output visible via `docker logs <container>`.  | Redirects output to internal log files. `docker logs` returns **empty**. Host logs land at `$AOPS_SESSIONS/.../agy-cli.log`.    |
| **Agent Definition**         | Supports `--agent <name>` (e.g. `@orchestrate:james`).              | Supports `--agent <name>` (e.g. `james`). Headless `agy --agent <name>` + MCP verified working end-to-end (commit `250921f8d`). |
| **Default Prompt Flag**      | Accepts positional prompt strings.                                  | Requires explicit `-i`/`--prompt-interactive` or `-p`/`--print` flags for non-interactive prompts.                              |

## Interact & Readiness Protocol

```bash
# 1. Poll pane output for client boot readiness signal
tmux capture-pane -t "$TMUX_NAME" -p -S -2000

# - For claude: Wait until prompt box with '❯' renders.
# - For agy: Wait 2-3s for auth race to clear and plan name to render in header.

# 2. Send prompt text using -l (literal text flag to prevent tmux key parsing errors)
tmux send-keys -t "$TMUX_NAME" -l "your prompt text here"

# 3. Always submit Enter as a separate tmux command
tmux send-keys -t "$TMUX_NAME" Enter

# 4. For TUI menu navigation (e.g., AskUserQuestion prompts):
tmux send-keys -t "$TMUX_NAME" Down Down Enter
```

## Read the Live State

```bash
tmux capture-pane -t "$TMUX_NAME" -p -S -2000
```

This reflects what an attached user sees. It is an ephemeral buffer that dies when the tmux session is killed.

## Authoritative Telemetry & Session Forensics (Phoenix MCP)

Phoenix is the authoritative, durable telemetry store for session traces. Unlike local markdown transcripts that truncate large tool inputs and outputs after ~300 characters, Phoenix stores **untruncated payload attributes**, **exact millisecond latencies**, and **full OpenTelemetry span call trees**.

Use the **`phoenix` MCP server** tools (`executeSql`, `getSpans`, `listProjectTraces`, `execute`) to perform instant, high-fidelity forensics on any session.

### 1. Direct Analytics SQL (`executeSql`) Recipes

Query the allowlisted SQLite database backend directly using standard SQL with JSON extraction operators (`->>` or `JSON_EXTRACT`):

#### A. Fast Session Discovery & Error Check

Find recent sessions, total span counts, error counts, and activity windows:

```sql
SELECT JSON_EXTRACT(attributes, '$.session.id') AS session_id,
       COUNT(*) AS span_count,
       SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) AS error_count,
       MIN(start_time) AS first_seen,
       MAX(start_time) AS last_seen
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') LIKE '%<SESSION_SLUG_OR_UUID>%'
GROUP BY session_id
ORDER BY last_seen DESC
LIMIT 10
```

#### B. Chronological Execution & Turn Sequence

Walk the full chronological execution flow of a session with computed latencies and input previews:

```sql
SELECT span_id, parent_id, name, span_kind, status_code, latency_ms,
       SUBSTRING(attributes->>'input.value', 1, 120) AS input_preview,
       SUBSTRING(attributes->>'output.value', 1, 120) AS output_preview
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
ORDER BY start_time ASC
```

#### C. Isolate Errors & Tool Failures

Instantly extract all failed tool executions or LLM exceptions with their untruncated error payloads:

```sql
SELECT span_id, name, span_kind, status_message, latency_ms,
       attributes->>'input.value' AS full_input,
       attributes->>'output.value' AS full_output
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
  AND status_code = 'ERROR'
ORDER BY start_time ASC
```

#### D. Verify Tool Execution vs Hallucination

Prove whether an agent actually called tools or hallucinated/grepped disk files:

```sql
SELECT name, COUNT(*) AS invocations,
       ROUND(AVG(latency_ms), 1) AS avg_ms,
       MAX(latency_ms) AS max_ms
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
  AND span_kind = 'TOOL'
GROUP BY name
ORDER BY invocations DESC
```

#### E. Token Accounting & Prompt Cache Ratio

Inspect LLM token usage and cache efficiency across turns:

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

#### F. Correlate a Spawned Subagent's Own Session

A subagent's session carries no attribute linking it back to the parent — a substring search for the parent's UUID across `attributes` will not find it. Correlate instead by matching the child's root turn to the exact prompt text the parent's `Agent` tool call sent (visible in the parent's own `AGENT`-kind span, Recipe G) and by time proximity — a spawned session's first span lands within seconds of the parent's `Agent` tool call:

```sql
SELECT JSON_EXTRACT(attributes, '$.session.id') AS session_id, span_id, start_time,
       SUBSTR(attributes->>'input.value', 1, 300) AS input_preview
FROM spans
WHERE span_kind = 'CHAIN' AND (parent_id IS NULL OR parent_id = '')
  AND start_time >= '<WINDOW_START>+00:00' AND start_time <= '<WINDOW_END>+00:00'
  AND attributes->>'input.value' LIKE '%<DISTINCTIVE PHRASE FROM THE PROMPT>%'
ORDER BY start_time ASC
```

A named subagent's own root turn opens with `<teammate-message teammate_id="team-lead">...` — the distinctive phrase to match on is the tail of the exact prompt text from the parent's `Agent` tool call. Once you have the child's `session.id`, pull its full span list (Recipe B, no `LIMIT`) to see its whole story: tool calls made, last activity, whether it ever closed.

#### G. Dispatch-Mode Fingerprint: named (teammate) vs unnamed (background task)

Whether an `Agent` tool call was given a `name` selects a different code path, visible directly in the payload of its own `AGENT`-kind span — read this off the span, do not infer it from timing or behaviour:

```sql
SELECT span_id, status_code, latency_ms, start_time,
       attributes->>'output.value' AS full_output
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<PARENT_SESSION_UUID>'
  AND span_kind = 'AGENT'
ORDER BY start_time ASC
```

- **Named** (`name` param set): output is `{"status": "teammate_spawned", "teammate_id": "<name>@session-<slug>", "agent_type": "...", "tmux_session_name": "...", ...}`. The span itself closes in ~150–250ms regardless of what the agent goes on to do — that is only the spawn acknowledgement, never the final result. The real result is delivered later, asynchronously, as an inbound `<teammate-message teammate_id="<name>">` injected as a new turn in the **parent's** own trace (search the parent session for `attributes->>'input.value' LIKE '%teammate-message%'`). A `{"type":"idle_notification","idleReason":"available"}` teammate-message means the named agent went idle — that is not evidence of completion or of being stuck; go check the agent's own session (Recipe F) for what it last did.
- **Unnamed**: output is `{"isAsync": true, "status": "async_launched", "agentId": "...", "outputFile": "...", "canReadOutputFile": false}`. This mode has an explicit, OTel-visible close event — search the parent session for `attributes->>'input.value' LIKE '%task-notification%'` to find a `<task-notification><status>completed</status>...<usage><duration_ms>N</duration_ms></usage></task-notification>` block. Teammate mode has **no equivalent close event anywhere in Phoenix**: the idle-heartbeat loop that keeps a named agent's pane alive runs below whatever boundary OTel instruments, so Phoenix can show a teammate delivered its result and went quiet, but cannot itself prove it later exited. Corroborate "still alive" against host-level evidence (e.g. `tmux list-panes ... pane_dead`), not telemetry alone.

#### H. Tool-Usage Fingerprint — did the agent structurally have the tool it needed?

Before concluding a silent or stuck agent "failed to report," check whether it ever called the tool that reporting requires, and whether its `agent_type` even carries that tool:

```sql
SELECT name, span_kind, COUNT(*) AS n
FROM spans
WHERE JSON_EXTRACT(attributes, '$.session.id') = '<CHILD_SESSION_UUID>'
GROUP BY name, span_kind
ORDER BY n DESC
```

Zero `SendMessage`/`send_message` rows in a named-teammate session, alongside real work visible in `Bash`/other tool spans and `status_code: UNSET` throughout, means the agent did its job and had no channel to report it — not that it hung or errored. Cross-check the spawning agent type's declared `Tools:` allowlist (visible in the session's own agent roster, or the plugin's agent-definition frontmatter) before attributing silence to a bug in the agent's behaviour rather than its tool grant.

### 2. Single-Pass Programmatic Diagnostics via `execute` (Code-Mode)

Instead of multiple round-trips, run a complete forensic evaluation script inside Phoenix's `execute` runtime:

```python
# Async execution block in Phoenix MCP `execute`
session_uuid = "<SESSION_UUID>"

summary = await call_tool("executeSql", {
    "sql": f"""
    SELECT COUNT(*) as total_spans,
           SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) as errors,
           SUM(CASE WHEN span_kind = 'TOOL' THEN 1 ELSE 0 END) as tool_calls,
           SUM(CASE WHEN span_kind = 'LLM' THEN 1 ELSE 0 END) as llm_calls
    FROM spans WHERE JSON_EXTRACT(attributes, '$.session.id') = '{session_uuid}'
    """
})

errors = await call_tool("executeSql", {
    "sql": f"""
    SELECT name, status_message, attributes->>'output.value' as output
    FROM spans WHERE JSON_EXTRACT(attributes, '$.session.id') = '{session_uuid}' AND status_code = 'ERROR'
    """
})

return {"summary": summary, "errors": errors}
```

### 3. Critical Telemetry Invariants & Rules

- **Filter strictly on `attributes->>'session.id'` (or `session_identifier`), NEVER on `trace_id` alone**: OpenTelemetry context propagates across inter-agent messages, meaning a single trace can span multiple sessions. Filtering on `trace_id` pulls foreign session work into your diagnostic view.
- **Short Slug Matching**: When given a short session slug (e.g. `9456cfd1`), use substring matching (`LIKE '%<slug>%'`) because Phoenix indexes full UUIDs.
- **Turn Counter Ordering**: `arthur.turn_number` is scoped per-tracer-state and resets across subagents. Always sort by `start_time` for session-wide chronology.
- **Container Telemetry Coverage**: If a container run emits only `CHAIN` spans (`claude-code-turn`) with zero `TOOL`/`LLM` spans, check `GENAI_ENGINE_TRACE_ENDPOINT` forwarding in the container's environment.
- **No parent↔child linking attribute**: A spawned subagent's session never carries the parent's session id (or any other parent-pointer) in its `attributes`. Correlate by prompt-text match and time window (Recipe F) — never by substring-searching for the parent UUID, which returns only sessions that happen to _mention_ it in conversation text, not the spawned children.
- **Bare timestamps are rejected**: `start_time >= '2026-08-19 22:12:00'` fails with `unsupported_syntax` — a time of day needs an explicit offset: `'2026-08-19 22:12:00+00:00'`. A bare date with no time (`'2026-07-01'`) is accepted and read as UTC.

---

## Host Filesystem Inspection (Secondary Audit)

When inspecting host-side container artifacts (located at `$AOPS_SESSIONS/logs/<YYYYMMDD>/<session-id>/workspace/`):

### 1. Audit Session Execution Manifest (`run.json` Schema v1)

```bash
SESS_DIR="$AOPS_SESSIONS/logs/$(date +%Y%m%d)/$TMUX_NAME/workspace"

jq '{schema_version, status, exit_code, delivery_guard, transcript, degraded}' "$SESS_DIR/run.json"
```

**Pass Assertions**:

- `.schema_version == 1`
- `.status == "success"`
- `.delivery_guard.ok == true`
- `.transcript.found == true` (with `event_count > 0`)

### 2. Audit Shared Hook Telemetry (`polecat-session-hooks.jsonl`)

```bash
jq -c '.' "$SESS_DIR/polecat-session-hooks.jsonl" | head -n 10
```

**Pass Assertions**: Each line must strictly conform to the 5-field schema: `ts` (ISO 8601 with microsecond UTC), `client` (`claude`|`agy`), `event`, `session_id`, `tool`.

### 3. Run Transcript Discovery Unit Tests

```bash
uv run pytest tests/transcripts/test_polecat_discovery.py -v
```

---

## Read the durable state from inside a container

Supervising from inside a single-repository container, you have no
`$AOPS_SESSIONS` — it is never forwarded in, so every path in the section above
names a host directory you cannot reach. Stop looking for it. What you can reach
is each client's own state root, holding exactly what this container's run
wrote:

| Whose conversation               | Where it lands inside the container                                                                                           |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Yours, under `claude`            | `$CLAUDE_CONFIG_DIR/projects/<slugified-cwd>/<session-uuid>.jsonl`, else `~/.claude/projects/...`                             |
| A worker you spawned via `Agent` | `<the same project dir>/<your-session-uuid>/subagents/agent-*.jsonl`, with a `.meta.json` beside it naming the agent that ran |
| An `agy` worker you launched     | `~/.gemini/antigravity-cli/brain/<conversation-id>/.system_generated/logs/transcript.jsonl` and `transcript_full.jsonl`       |

`$AOPS_SESSION_STATE_DIR` names the directory the host has mounted, so
`polecat-session-hooks.jsonl` sits beside your own transcript and is readable
live. `run.json` is not there: the host writes it after the container exits, so
mid-run there is no run record to read.

List every one of them, newest first, tagged by client, kind, agent and parent
session — `--kind subagent` narrows it to the workers, `--json` makes it
machine-readable:

```bash
PYTHONPATH="$(git rev-parse --show-toplevel)/lib/py" uv run python -m transcripts.discovery --kind subagent
```

Then read the JSONL each row names. A worker's `tool_use` records are what you
score its claims against; its own report is not evidence that anything ran.

---

## Clean Up
```bash
tmux send-keys -t "$TMUX_NAME" -l "/exit"; tmux send-keys -t "$TMUX_NAME" Enter
sleep 2   # Allow client to flush transcript buffer and host bind-mounts
tmux kill-session -t "$TMUX_NAME" 2>/dev/null || true
```

Container cleanup is automatic because `lib/polecat/cli.py` invokes `docker run --rm`.

---

## Validate a Dev Change (6-Stage Verification Walk)

Run this protocol after modifying any framework code (`plugins/*/hooks`, `lib/`, skills, `lib/polecat/cli.py`, `entrypoint.sh`, Dockerfile).

### Protocol Rules:

- **Dual-Client Verification**: Run the verification walk twice — once with `claude`, once with `agy`.
- **Sequential Evaluation**: Walk the layers in order. Stop at the first failure.
- **Verbatim Evidence Mandatory**: Include verbatim excerpts from `tmux capture-pane`, session log files, and Phoenix MCP query outputs in your final report.

### Step-by-Step Walk:

1. **Pre-flight (Hooks Check)**: Verify `_log_fire` and `_load_handlers` in `lib/hooks/dispatch.py` are not returning early.
2. **§0 Image Build & Freshness**: Run `make docker-build` followed by `make verify-docker` to guarantee image layer freshness.
3. **§1 Structural Smoke Test**: Run `make docker-smoke-test` to confirm plugin installation in container image.
4. **§2 Container Boot Signals**:
   - `claude`: Confirm banner and `❯` input box render inside `/workspace`.
   - `agy`: Confirm 2–3s auth race clears and plan name renders in header block.
5. **§3 First Prompt & Model Output Assertion**: Send prompt (e.g. `"call pkb get_status() and return results"`) and capture pane. **You MUST assert the model output string or tool call record** (e.g. PKB status / tool execution results) in the captured pane or session transcript. Merely rendering the prompt box is NOT proof of success.
6. **§4 Exercise Changed Path**: Invoke the specific changed skill, hook, or tool call and capture the visible execution output.
7. **§5 Observability & Authoritative Audit (Phoenix MCP + Host Audit)**:
   - Run `executeSql` against Phoenix MCP to verify span emission:
     ```sql
     SELECT count(*) FROM spans WHERE JSON_EXTRACT(attributes, '$.session.id') = '<SESSION_UUID>'
     ```
   - Assert that `TOOL` spans exist and `status_code != 'ERROR'`.
   - Audit `run.json` (`status: "success"`, `delivery_guard.ok: true`), verify `polecat-session-hooks.jsonl` events, and run `pytest tests/transcripts/test_polecat_discovery.py`.
8. **§6 Clean Teardown**: Send `/exit`, wait `sleep 2`, kill session.

---

## Diagnostic Gotchas & Reference

| Symptom / Error                                                                     | Root Cause                                                                                              | Immediate Fix / Remediation                                                                                                                                              |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `no server running on /tmp/tmux-...`                                                | Inline tmux command failed in `/bin/sh -c` due to quoting or missing PATH exports                       | Use launch script wrapper file `/tmp/launch-$SESSION.sh`                                                                                                                 |
| Session log directory named after prompt string                                     | Passed `-p` option after `run` without `--` separator; Click parsed `-p` as `--project`                 | Place `--` (double-dash) before agent flags and prompts                                                                                                                  |
| `agy` stuck at Google OAuth login prompt                                            | `GEMINI_CONFIG_DIR` missing or lacks `antigravity-oauth-token`                                          | Set `GEMINI_CONFIG_DIR=~/.gemini` and ensure token exists                                                                                                                |
| `docker logs <container>` returns empty for `agy`                                   | `agy` redirects logs to internal log files                                                              | Read host bind-mounted file `$AOPS_SESSIONS/.../agy-cli.log`                                                                                                             |
| `fatal: not a git repository` in container                                          | `-d` passed a linked git worktree directory                                                             | Use full git clone directory for `-d` or pass `-p <project>`                                                                                                             |
| Premature boot failure report for `agy`                                             | Captured pane during 2–3s `⚠ Verifying your account...` auth rendering race                             | Wait 2–3 seconds for header plan name to render before inspecting                                                                                                        |
| MCP tool calls missing in agent response                                            | Agent grepped answers from host disk files rather than executing tools                                  | Inspect Phoenix MCP SQL `SELECT count(*) FROM spans WHERE span_kind='TOOL' AND attributes->>'session.id'='<UUID>'` to verify real tool execution                         |
| `⚠ Agent execution terminated due to error` + an error ID, nothing else in the pane | agy agent frontmatter names a tool absent from its registry                                             | `grep "not found in registry" <session>/agy-cli.log`; drop the offending names from `build/tool_map.toml`'s `accepted_tools`                                             |
| Headless `agy` returns `"error":"context canceled"` with work half-done             | Job outran `--print-timeout` (default `5m0s`)                                                           | Compare `duration_seconds` against the timeout; re-run with an explicit `--print-timeout`                                                                                |
| `delivery_guard_failed` after a probe that wrote files                              | The probe's own artefacts are uncommitted in the workspace                                              | Expected for a write probe — not a framework defect; confirm the named files are the probe's before treating it as one                                                   |
| Named subagent never returns / repeats `idle_notification` forever                  | `name` on the `Agent` tool call spawns a persistent teammate with no OTel-visible exit event (Recipe G) | Do not wait on the tool call; watch the parent session for an inbound `<teammate-message>`, and check the child's own session (Recipe F) for whether it already sent one |
| Named subagent did real work but never reported it                                  | Its `agent_type`'s tool allowlist has no `SendMessage` — the only delivery channel for teammate mode    | Recipe H: confirm zero `SendMessage` spans, then check the agent-type's declared `Tools:` — this is a capability gap, not a hang or a bug in the agent                   |
| `executeSql` result "exceeds maximum allowed tokens", dumped to a `.txt` file       | Query returned too many rows or unbounded `input.value`/`output.value` columns                          | Narrow the `SELECT` with `SUBSTR(...)`, add a tighter `WHERE`/`LIMIT`; if already dumped, read the saved file with `jq` rather than re-querying                          |
