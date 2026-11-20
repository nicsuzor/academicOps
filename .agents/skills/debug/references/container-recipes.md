# Container and Client Driving Recipes

Command recipes for launching, driving, and auditing headless or tmux-hosted `claude` and `agy` sessions.

## Headless Local Probe

Watch a local agent read-only without container isolation:

```bash
agy --agent james --print "<prompt>"
```

## Client Differences and Probe Diagnostics

- **`agy` auth and startup**: Requires `$GEMINI_CONFIG_DIR` staged with `antigravity-oauth-token`. Renders `⚠ Verifying your account...` for 2-3 s before its header plan name (`username (Google AI Ultra)`) appears, writes logs to files rather than stdout, and requires `-i`/`--prompt-interactive` or `-p`/`--print` (whereas `claude` accepts a positional prompt).
- **`--agent` flags**: Both clients take `--agent <name>` (`@aops:james` for `claude`, `james` for `agy`).
- **Absent or empty `tools:` in `agy` frontmatter**: Restricts the agent to ten read-only tools with no boot error; make `"list your own callable tools"` step 1 of any probe (a ten-name list indicates starvation).
- **Unregistered tool in `agy` frontmatter**: Terminates with `⚠ Agent execution terminated due to error.` and an error ID; inspect `agy-cli.log` for `failed to resolve components: unknown component: tool "<name>" not found in registry`.

## Launch a Container Under tmux

Write the invocation to a launch script rather than passing an inline command string to `tmux new-session` (inline strings break on shell expansion, nested quoting, and virtualenv resolution inside `/bin/sh -c`). Always pass `--` before agent flags and prompts, and `-x 220 -y 50` so TUI headers and status lines do not wrap-corrupt.

```bash
CHECKOUT="$(git rev-parse --show-toplevel)"
export TMUX_NAME="polecat-debug-$RANDOM"
LAUNCH_SCRIPT="/tmp/launch-${TMUX_NAME}.sh"

cat > "$LAUNCH_SCRIPT" <<EOF
#!/usr/bin/env bash
export POLECAT_IMAGE="${POLECAT_IMAGE:-polecat:latest}"

# Run via the installer-supplied polecat host launcher on PATH:
exec polecat -d "$CHECKOUT" -s "$TMUX_NAME" -i -- claude -p "call pkb get_status() and return results"
# For agy:
# exec polecat -d "$CHECKOUT" -s "$TMUX_NAME" -i -- agy -p "call pkb get_status() and return results"
EOF
chmod +x "$LAUNCH_SCRIPT"

tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 "$LAUNCH_SCRIPT"
```

## Drive and Tear Down

`capture-pane` reads an ephemeral buffer that dies with the tmux session; capture anything you intend to cite.

```bash
# Readiness: claude waits for '❯'; agy waits 2-3s for auth clear and plan name.
tmux capture-pane -t "$TMUX_NAME" -p -S -2000

# Send literal prompt text so tmux does not interpret key names.
tmux send-keys -t "$TMUX_NAME" -l "your prompt text here"
tmux send-keys -t "$TMUX_NAME" Enter

# TUI menu navigation
tmux send-keys -t "$TMUX_NAME" Down Down Enter

# Teardown (container cleanup is automatic with --rm)
tmux send-keys -t "$TMUX_NAME" -l "/exit"; tmux send-keys -t "$TMUX_NAME" Enter
sleep 2   # allow transcript flush through the bind-mount
tmux kill-session -t "$TMUX_NAME" 2>/dev/null || true
```

## Telemetry and Host Filesystem Audit

Inspect tool calls, model output, errors, latencies, and token spend from Arize Phoenix via `ida:phoenix` (generates `<slug>.outline.md` and runs Phoenix MCP queries).

Host container artifacts land under `$AOPS_SESSIONS/logs/<YYYYMMDD>/<session-id>/workspace/`:

```bash
SESS_DIR="$AOPS_SESSIONS/logs/$(date +%Y%m%d)/$TMUX_NAME/workspace"
jq '{schema_version, exit_code, agent_exit_code, final_task_status, task_guard_outcome}' "$SESS_DIR/run.json"
jq -c '.' "$SESS_DIR/polecat-session-hooks.jsonl" | head -n 10
```

Pass assertions: `run.json` has `.schema_version == 1` and `.exit_code == 0`; every line in `polecat-session-hooks.jsonl` conforms to `ts` (ISO 8601 microsecond UTC), `client` (`claude`|`agy`), `event`, `session_id`, and `tool`.

## Read Durable State Inside a Container

`$AOPS_SESSIONS` is never forwarded into a single-repository container; read each client's state root instead:

| Whose conversation | Path inside the container |
| - | - |
| Yours, under `claude` | `$CLAUDE_CONFIG_DIR/projects/<slugified-cwd>/<session-uuid>.jsonl`, else `~/.claude/projects/...` |
| Worker spawned via `Agent` | `<project dir>/<your-session-uuid>/subagents/agent-*.jsonl` plus `.meta.json` |
| `agy` worker | `~/.gemini/antigravity-cli/brain/<conversation-id>/.system_generated/logs/transcript.jsonl` and `transcript_full.jsonl` |

`$AOPS_SESSION_STATE_DIR` names the host-mounted directory holding live `polecat-session-hooks.jsonl` (`run.json` is written on the host after container exit). Discover session JSONLs newest first (`--kind subagent` narrows to workers, `--json` formats machine-readable):

```bash
PYTHONPATH="$(git rev-parse --show-toplevel)/lib/py" uv run python -m transcripts.discovery --kind subagent
```
