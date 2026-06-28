---
title: Hooks & MCP Configuration
type: reference
category: ref
permalink: ref-hooks-guide
description: academicOps hook architecture, PATH bootstrap, MCP server config, and I/O schemas
---

# Hooks & MCP: academicOps Reference

> **Scope split with `GATES.md`.** This file is the **hook infrastructure** reference: router architecture, PATH bootstrap, MCP wiring, hook I/O schemas, Gemini differences. For the **runtime catalogue of gates that fire via this router** (what each gate is, how it's configured in `polecat.yaml`, how to verify it's firing, how to debug it), see [`specs/GATES.md`](../../../../specs/GATES.md). For raw JSONL forensics, see [[forensics-details]].

For Claude Code's hook system in general, see the [official docs](https://code.claude.com/docs/en/hooks) and [plugins reference](https://code.claude.com/docs/en/plugins-reference). This document covers the academicOps-specific implementation.

## Hook message visibility quick-reference

Full Output Matrix — PTY Hook Probe (Layer C) script — validated 2026-06-27

label client gate U✓A U✓B earA C✓A C✓B tx?
─────────────────────────────────────────────────────────────────────────────────────────────────
stop-block-reason claude block ✓ ✗ ✓ ✓ ✗ ✓
stop-additionalcontext-warn claude noblock ✓ ✗ ✓ ✓ ✗ ✓
stop-systemmessage claude - ✗ ✓ ✗ ✗ ? ✓
stop-warnmode-real claude noblock ✓ ✓ ✓ ✓ ? ✓
stop-blockmode-real claude block ✓ ✓ ✓ ✓ ? ✓
stop-block-suppressoutput claude block ✓ ✗ ✓ ✓ ✗ ✓\
stop-noblock-suppressoutput claude noblock ✓ ✗ ✓ ✓ ✗ ✓\
stop-block-continue-false claude block ✓ ✗ ✓ ✓ ✗ ✓
─────────────────────────────────────────────────────────────────────────────────────────────────
sessionend-block-reason claude block ✗ ✗ ✗ ✗ ✗ ✓\
sessionend-additionalcontext claude noblock ✗ ✗ ✗ ✗ ✗ ✓\
─────────────────────────────────────────────────────────────────────────────────────────────────
ups-additionalcontext claude noblock ✗ ✗ ✗ ? ✗ ✓
ups-systemmessage claude - ✗ ✓ ✗ ✗ ? ✓
ups-deny-reason claude block ✗ ✗ ✗ ✗ ✗ ✓\
─────────────────────────────────────────────────────────────────────────────────────────────────
pretool-deny-reason claude block ✗ ✗ ✗ ✓ ✗ ✓
pretool-ask-reason claude block ✗ ✗ ✗ ✗ ✗ ✓\
pretool-additionalcontext claude noblock ✗ ✗ ✗ ? ✗ ✓
pretool-deny-systemmessage claude block ✗ ✓ ✗ ✓ ? ✓
pretool-allow-systemmessage claude noblock ✗ ✓ ✗ ✗ ? ✓
─────────────────────────────────────────────────────────────────────────────────────────────────
posttool-additionalcontext claude noblock ✗ ✗ ✗ ? ✗ ✓
posttool-systemmessage claude - ✗ ✓ ✗ ✗ ? ✓
─────────────────────────────────────────────────────────────────────────────────────────────────
sessionstart-additionalcontext claude noblock ✗ ✗ ✗ ? ✗ ✓
sessionstart-systemmessage claude - ✗ ✓ ✗ ✗ ? ✓
─────────────────────────────────────────────────────────────────────────────────────────────────
agy-preinvocation-live agy - ✗ ✗ ? ✗ ✓ ✗
agy-postinvocation-live agy - ✗ ✗ ? ✗ ✓ ✗
agy-*-unmeas [5 stubs] agy - ? ? ? ? ? ✗
─────────────────────────────────────────────────────────────────────────────────────────────────
U✓A/B = user saw sentinel on a banner line (early OR late snap)
earA = user saw sentinelA on EARLY snap only (transient toasts)
C✓A/B = agent received sentinel in context ? = in transcript, source ambiguous
tx = visible in transcript

## Active Hooks

| File                  | Event            | Purpose                          |
| --------------------- | ---------------- | -------------------------------- |
| session_env_setup.sh  | SessionStart     | Environment setup                |
| user_prompt_submit.py | UserPromptSubmit | Context enrichment via temp file |
| unified_logger.py     | ALL events       | Universal event logging          |

Axiom enforcement is delegated to the `rbg` agent — axiom content is no longer injected at session start.

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

**Platform constraint (Claude Code 2.1.158, re-verified empirically 2026-05-31):** Stop events do **not** support `hookSpecificOutput` or `additionalContext`. If those fields are present the validator fails (`"Hook JSON output validation failed — (root): Invalid input"`, recorded as a `hook_non_blocking_error` and surfaced to the user as a generic "Stop hook error occurred" notification) and discards the **entire** payload — so `decision`/`reason` are dropped too and the agent is not blocked. The validator's own expected-schema lists `hookSpecificOutput` only for PreToolUse / UserPromptSubmit / PostToolUse / PostToolBatch — never Stop. The only agent-visible channel on Stop is `decision: "block"` + `reason`. `systemMessage` and `stopReason` are user-visible only — the agent never sees them (confirmed absent from the stream-json agent feed). Reproduction: `proof/anthropic-issue/` on the stophooktest branch.

| Field                | `decision: "block"`              | `decision: "approve"` |
| -------------------- | -------------------------------- | --------------------- |
| `reason`             | Fed to agent as next instruction | Silently discarded    |
| `systemMessage`      | Shown to user only               | Shown to user only    |
| `stopReason`         | Shown to user only               | Shown to user only    |
| `hookSpecificOutput` | **Not supported**                | **Not supported**     |

**Consequence:** non-blocking advisory injection on Stop is impossible. To make the agent see a Stop advisory, you must `decision: "block"` — the agent is forced to re-emit. The academicOps gates use a **block-once** pattern: block on the first Stop in a turn (gate opens via trigger), then approve subsequent Stops. The gate re-arms on `UserPromptSubmit`.

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
