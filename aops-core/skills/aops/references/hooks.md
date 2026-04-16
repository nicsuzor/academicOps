---
title: Hooks & MCP Configuration
type: reference
category: ref
permalink: ref-hooks-guide
description: academicOps hook architecture, PATH bootstrap, MCP server config, and I/O schemas
---

# Hooks & MCP: academicOps Reference

For Claude Code's hook system in general, see the [official docs](https://code.claude.com/docs/en/hooks) and [plugins reference](https://code.claude.com/docs/en/plugins-reference). This document covers the academicOps-specific implementation.

## Active Hooks

| File                        | Event            | Purpose                               |
| --------------------------- | ---------------- | ------------------------------------- |
| session_env_setup.sh        | SessionStart     | Environment setup                     |
| sessionstart_load_axioms.py | SessionStart     | Injects AXIOMS, FRAMEWORK, HEURISTICS |
| user_prompt_submit.py       | UserPromptSubmit | Context enrichment via temp file      |
| policy_enforcer.py          | PreToolUse       | Block destructive operations          |
| autocommit_state.py         | PostToolUse      | Auto-commit data/ changes             |
| unified_logger.py           | ALL events       | Universal event logging               |

**Architecture principle**: Hooks inject context — they don't do LLM reasoning. Timeouts: 2-30 seconds. Hooks must NOT call the Claude/Anthropic API directly.

## Router Architecture

All hooks dispatch through `hooks/router.py`, launched via `hooks/router.sh`. The shell wrapper bootstraps PATH before delegating to Python. The router consolidates multiple hook outputs into a single response.

Register hooks in `HOOK_REGISTRY` in `hooks/router.py`:

```python
HOOK_REGISTRY = {
    "SessionStart": [
        {"script": "session_env_setup.sh"},
        {"script": "your_new_hook.py"},       # sync (default)
        {"script": "slow_hook.py", "async": True},  # async
    ],
}
```

## PATH Bootstrap (`scripts/ensure-path.sh`)

Claude Code launches plugin processes (hooks, MCP servers) with a minimal PATH (`/usr/bin:/bin:/usr/sbin:/sbin`). Tools like `uv`/`uvx` installed via Homebrew or pip are not found without explicit probing.

`scripts/ensure-path.sh` is the shared solution — sourced by both `hooks/router.sh` and `scripts/run-mcp.sh`. It:

1. Sets `$USER` if missing (launchd/Claude Desktop omit it, breaking `~/.env.system-paths`)
2. Sources `~/.env.system-paths` if present (Homebrew shellenv, Cargo, etc.)
3. Probes: `~/.local/bin`, `/home/debian/.local/bin`, `/usr/local/bin`, `/opt/homebrew/bin`, `/usr/bin`

This fixes the same class of bug encountered 6+ times across hooks, cron, Gemini workers, polecat, Docker, and MCP servers.

## MCP Server Launch (`scripts/run-mcp.sh`)

The PKB MCP server uses a wrapper script instead of calling `uvx` directly:

```json
{
  "command": "bash",
  "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/run-mcp.sh"],
  "env": { "PKB_MCP_URL": "${user_config.PKB_MCP_URL}" }
}
```

`run-mcp.sh` sources `ensure-path.sh`, validates `$PKB_MCP_URL`, ensures `UV_CACHE_DIR` is writable, then exec's `uvx fastmcp run "$PKB_MCP_URL"`.

**Template**: `aops-core/mcp.json.template` — has platform-specific sections for Claude (`${CLAUDE_PLUGIN_ROOT}`, `${user_config.*}`) and Gemini (`${extensionPath}`, `${PKB_MCP_URL}`).

## Hook I/O Schemas

### Exit Codes (PreToolUse)

| Exit | Action      | Message source     |
| ---- | ----------- | ------------------ |
| `0`  | Allow       | JSON on **stdout** |
| `1`  | Warn, allow | **stderr**         |
| `2`  | Block       | **stderr** only    |

Exit 2 ignores stdout entirely. For other hook types, always exit 0.

### Common Input (all hooks)

```json
{
  "session_id": "uuid",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/working/directory",
  "permission_mode": "bypassPermissions" | "requirePermissions",
  "hook_event_name": "PreToolUse" | "PostToolUse" | ...
}
```

### PreToolUse — additional fields and output

Input adds: `tool_name`, `tool_input` (tool-specific params).

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow" | "deny" | "ask"
  }
}
```

### PostToolUse — additional fields and output

Input adds: `tool_name`, `tool_input`, `tool_response`.

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Optional context injected into conversation"
  }
}
```

### Stop/SubagentStop — output

Must exit 0 for JSON to be processed:

```json
{
  "decision": "block",
  "reason": "Instructions for Claude (agent-visible)",
  "stopReason": "Message for user (user-visible)"
}
```

**Router warning**: `merge_outputs` must preserve `decision`, `reason`, `stopReason` — these are NOT in `hookSpecificOutput`.

### additionalContext triggers tool use

The `additionalContext` field can instruct the agent to use tools, not just add text. Use `"BEFORE answering, you MUST use the X tool..."` pattern. Cannot replace user prompt — only ADD context or BLOCK.

## Python Hook Conventions

**Location**: `aops-core/hooks/`. **Naming**: `{event}_{purpose}.py`.

```python
#!/usr/bin/env python3
import contextlib, json, sys
from typing import Any

def main():
    input_data: dict[str, Any] = {}
    with contextlib.suppress(json.JSONDecodeError):
        input_data = json.load(sys.stdin)

    output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
```

**Rules**: Use `lib.paths` (never hardcode), `.get()` with defaults, fail-fast on critical errors (exit 1), graceful degradation on optional operations. Router handles logging — individual hooks don't log.

## Debugging

Hook I/O logged to `~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl`. Run `claude --debug` for execution details.

## Gemini Differences

| Aspect          | Claude Code                | Gemini CLI                                    |
| --------------- | -------------------------- | --------------------------------------------- |
| Config file     | `~/.claude/settings.json`  | `~/.gemini/settings.json`                     |
| Plugin path var | `${CLAUDE_PLUGIN_ROOT}`    | `${extensionPath}`                            |
| Extension hooks | `hooks` in plugin settings | `hooks/hooks.json` in extension dir           |
| Safe settings   | N/A                        | `{"hooksConfig":{"enabled":true}}` (no auth!) |

When using `GEMINI_CLI_HOME` (polecat crew), don't set `security.auth.selectedType` — Gemini exits before hooks fire if auth doesn't match. Don't set `tools.sandbox.enabled: true` either.
