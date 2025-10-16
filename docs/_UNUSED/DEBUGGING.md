# Debugging Guide

## Overview

This guide provides the authoritative workflow for debugging and validating the system.

## The Simplified Golden Path Workflow

**Two Core Tools:**

1.  **Log Analysis**: Use structured log analysis for setup and configuration issues.
2.  **Live Flow Debugging**: Use an interactive debugger for flow control.

**Debugging loop:**

1.  **Start the Server**: Launch the backend API.
2.  **Check Logs First**: Use structured log tools to check for configuration errors.
3.  **Test Connectivity**: Verify API health endpoints.
4.  **Debug Live Flows**: Execute flows and inspect messages.
5.  **Stop the Server**: Terminate the backend process.

---

## 1. Start the Server

Use the appropriate command to start the API server in the background, e.g. `make debug`.

This command should handle killing any old processes and start a new one, logging output to a file in `/tmp/`.

For advanced debugging, you may want to launch the server directly to monitor stdio in real-time:

```bash
# Example command
uv run python -m buttermilk.runner.cli run=api llms=debug verbose=true
```

**⚠️ WARNING**: This command may not time out. Only use if your agent can manage background processes.

---

## 2. Check Logs First (Setup Issues)

Structured logs are the first place to check for configuration and setup errors.

**Canonical command:**
```bash
# Example command to get logs
uv run python -m buttermilk.debug.ws_debug_cli logs -n 20
```

**Alternative log levels:**
```bash
# Show only errors and warnings
uv run python -m buttermilk.debug.ws_debug_cli logs -n 20 -l ERROR

# Show more detail with DEBUG level
uv run python -m buttermilk.debug.ws_debug_cli logs -n 50 -l DEBUG
```

---

## 3. Debug Live Flows

For live flow debugging, use an interactive debugger that acts as a UI replacement, allowing agents to control flows interactively in real-time.

### Legacy ws_debug_cli Commands (Still Available)

**Flow Control:**
- `start <flow_name> [query]` - Start a flow with optional initial query
- `send <text>` - Send a response to the current flow
- `logs -n <number>` - Show last n lines from latest log file

**Session Control:**
- `clear-session` - Clear message history
- `test-connection` - Test WebSocket connection

*   **Test Connection:**
    ```bash
    uv run python -m buttermilk.debug.ws_debug_cli test-connection
    ```

### SUCCESS CRITERIA: Complete Flow Execution

- Flow runs through ALL agents sequentially
- All agents produce visible output.
- Session shows completion, not hanging.

---

## 4. Stop the Server

When you are finished debugging, use the appropriate command to stop the background API server, e.g. `make kill_api`.

This ensures no orphaned processes are left running.

---

## Troubleshooting Common Issues

### Make Target Issues

**Problem**: `make kill_api` fails with "command not found" or process errors.
**Solution**: 
1. Verify you're in the project root directory
2. Check if processes are actually running: `ps aux | grep <process_name>`
3. If the make command fails, manually kill processes: `pkill -f "<process_name>"`

### WebSocket Debug CLI Issues

**Problem**: `--wait` option fails with "requires argument" error.
**Solution**: Always provide a numeric value: `--wait 5` instead of just `--wait`

**Problem**: Commands hang or timeout.
**Solution**: 
1. Verify the API server is running.
2. Test connection first.
3. Check logs.

### Log Analysis Tips

**Problem**: Log outputs are too verbose for analysis.
**Solution**: 
- Use level filtering.
- Limit output with `-n` parameter for recent entries.
- Focus on specific timeframes when issues occurred.
- **Follow OUTPUT RULE**: Summarize findings instead of dumping raw logs.

### Output Conciseness Guidelines

When using debugging tools, agents must:
- **Extract key findings** instead of showing full command output
- **Limit excerpts** to 10-15 lines maximum per tool invocation
- **Summarize patterns** rather than listing individual log entries
- **Highlight specific errors** or success indicators only
- **Use bullet points** for key findings rather than prose explanations
