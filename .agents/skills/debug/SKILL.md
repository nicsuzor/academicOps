---
name: debug
description: Use when driving a framework run you intend to score — choosing a surface, dispatching a worker, or when asked to "debug a polecat", "run a polecat container interactively", "attach to a polecat session", "check polecat logs", or to verify that a change to plugins, hooks, lib/, skills, or the Dockerfile actually works inside a real container. Spins up a `polecat run` container under tmux for live interaction, leverages the Phoenix MCP server for authoritative telemetry and session debugging, and walks the layered check that separates "installed in the image" from "actually fires".
---

# Driving a framework run — surfaces, dispatch, and interactive debugging

The standard you hold while scoring a run is the [`dogfood`](../dogfood/SKILL.md) skill's "Supervising a trial". This file is how you drive one.

Mechanics and gotchas for the container surface: [`specs/polecat/tmux-interactive-driving.md`](../../../specs/polecat/tmux-interactive-driving.md).

## Choose a surface

Pick the cheapest surface that answers the question, and name it in your report — a result is only interpretable against the surface that produced it.

- **Headless `claude` or `agy`** for simple, low-risk work, with results returned to your own shell. To watch a local agent read-only: `agy --output-format stream-json --agent james --print "<prompt>" > <run-log>.jsonl 2>&1`, then read the log. Redirect; never pipe through `tail` or any other filter — a filter buffers until exit, so a running job and a hung one look the same. And read the reported `status`, not the exit code: `agy` exits `0` even when it returns `{"status":"ERROR","response":""}`. `agy`'s print mode also has its own deadline — `--print-timeout`, default `5m0s` — which kills any longer job mid-work and reports `"status":"ERROR","error":"context canceled"` with the work half-done and nothing committed. That failure is indistinguishable from a real one until you check `duration_seconds` against the timeout, so pass `--print-timeout` explicitly for any job that edits, builds, or rebuilds an image.
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

## Environment Pre-Flight Matrix

Before driving any Polecat container, verify all required host environment variables are set. `entrypoint.sh` and `lib/polecat/cli.py` enforce these requirements on startup:

| Variable                      | Mandatory For      | Typical Host Value / Source                               | Consequence if Missing / Invalid                                                      |
| ----------------------------- | ------------------ | --------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `POLECAT_HOME`                | All container runs | `$HOME/.polecat` or `/home/nic/.aops`                     | Container launcher exits immediately: `Error: no polecat home configured`             |
| `POLECAT_IMAGE`               | All container runs | `ghcr.io/nicsuzor/aops-crew:latest`                       | Container launcher exits immediately: `Error: no container image configured`          |
| `AOPS_SESSIONS`               | All container runs | `/home/nic/src/sessions`                                  | Container launcher exits: `Error: no sessions root configured`                        |
| `GEMINI_CONFIG_DIR`           | `agy` runs         | `$HOME/.gemini` or `/home/nic/.gemini`                    | `agy` boots into an unanswerable Google OAuth login prompt inside the container       |
| `AOPS_BOT_GH_TOKEN`           | All container runs | `gh-token-placeholder` or bot PAT                         | Container `entrypoint.sh` aborts with `Missing AOPS_BOT_GH_TOKEN`                     |
| `GIT_AUTHOR_NAME`             | All container runs | `AcademicOps Bot`                                         | Container `entrypoint.sh` aborts with `Missing GIT_AUTHOR_NAME`                       |
| `GIT_AUTHOR_EMAIL`            | All container runs | `bot@academicops.org`                                     | Container `entrypoint.sh` aborts with `Missing GIT_AUTHOR_EMAIL`                      |
| `GENAI_ENGINE_TRACE_ENDPOINT` | All container runs | `http://services-new.stoat-musical.ts.net:4318/v1/traces` | Container `entrypoint.sh` aborts with `FATAL: GENAI_ENGINE_TRACE_ENDPOINT is not set` |

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

| Dimension                    | Claude Code (`claude`)                                              | Antigravity CLI (`agy`)                                                                                                          |
| ---------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Authentication & Staging** | Configured via `.claude/settings.json` and API keys in environment. | Requires `$GEMINI_CONFIG_DIR` staging via `setup_staging()` (`antigravity-oauth-token`). Without it, boots into OAuth wall.      |
| **Startup Rendering Race**   | Immediate rendering of model banner and `❯` input prompt.           | Renders `⚠ Verifying your account...` for 2–3 seconds before header plan name (`nic.suzor@gmail.com (Google AI Ultra)`) appears. |
| **Logging Surface**          | Native stdout/stderr output visible via `docker logs <container>`.  | Redirects output to internal log files. `docker logs` returns **empty**. Host logs land at `$AOPS_SESSIONS/.../agy-cli.log`.     |
| **Agent Definition**         | Supports `--agent <name>` (e.g. `@orchestrate:james`).              | Supports `--agent <name>` (e.g. `james`). Headless `agy --agent <name>` + MCP verified working end-to-end (commit `250921f8d`).  |
| **Default Prompt Flag**      | Accepts positional prompt strings.                                  | Requires explicit `-i`/`--prompt-interactive` or `-p`/`--print` flags for non-interactive prompts.                               |

## Interact & Readiness Protocol

```bash
# 1. Poll pane output for client boot readiness signal
tmux capture-pane -t "$TMUX_NAME" -p -S -2000

# - For claude: Wait until prompt box with '❯' renders.
# - For agy: Wait 2-3s for auth race to clear and plan name ('nic.suzor@gmail.com') to render in header.

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
   - `agy`: Confirm 2–3s auth race clears and plan name (`nic.suzor@gmail.com`) renders in header block.
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

| Symptom / Error                                                                     | Root Cause                                                                              | Immediate Fix / Remediation                                                                                                                      |
| ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `no server running on /tmp/tmux-...`                                                | Inline tmux command failed in `/bin/sh -c` due to quoting or missing PATH exports       | Use launch script wrapper file `/tmp/launch-$SESSION.sh`                                                                                         |
| Session log directory named after prompt string                                     | Passed `-p` option after `run` without `--` separator; Click parsed `-p` as `--project` | Place `--` (double-dash) before agent flags and prompts                                                                                          |
| `agy` stuck at Google OAuth login prompt                                            | `GEMINI_CONFIG_DIR` missing or lacks `antigravity-oauth-token`                          | Set `GEMINI_CONFIG_DIR=~/.gemini` and ensure token exists                                                                                        |
| `docker logs <container>` returns empty for `agy`                                   | `agy` redirects logs to internal log files                                              | Read host bind-mounted file `$AOPS_SESSIONS/.../agy-cli.log`                                                                                     |
| `fatal: not a git repository` in container                                          | `-d` passed a linked git worktree directory                                             | Use full git clone directory for `-d` or pass `-p <project>`                                                                                     |
| Premature boot failure report for `agy`                                             | Captured pane during 2–3s `⚠ Verifying your account...` auth rendering race             | Wait 2–3 seconds for header plan name to render before inspecting                                                                                |
| MCP tool calls missing in agent response                                            | Agent grepped answers from host disk files rather than executing tools                  | Inspect Phoenix MCP SQL `SELECT count(*) FROM spans WHERE span_kind='TOOL' AND attributes->>'session.id'='<UUID>'` to verify real tool execution |
| `⚠ Agent execution terminated due to error` + an error ID, nothing else in the pane | agy agent frontmatter names a tool absent from its registry                             | `grep "not found in registry" <session>/agy-cli.log`; drop the offending names from `build/tool_map.toml`'s `accepted_tools`                     |
| Headless `agy` returns `"error":"context canceled"` with work half-done             | Job outran `--print-timeout` (default `5m0s`)                                           | Compare `duration_seconds` against the timeout; re-run with an explicit `--print-timeout`                                                        |
| `delivery_guard_failed` after a probe that wrote files                              | The probe's own artefacts are uncommitted in the workspace                              | Expected for a write probe — not a framework defect; confirm the named files are the probe's before treating it as one                           |
