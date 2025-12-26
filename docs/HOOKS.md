---
title: Hooks
type: framework-doc
permalink: docs-hooks
description: Claude Code hooks extend session functionality, injecting context and enforcing policies
---

# Hooks

Claude Code hooks extend session functionality. All hooks live in `hooks/`.

## Architecture

**Hooks inject context - they don't do LLM reasoning.**

```
Hook Event → Python script → Returns {additionalContext: "..."} or {continue: false}
```

**Timeouts**: 2-30 seconds. Hooks must NOT call the Claude/Anthropic API directly.

## Active Hooks

| File | Event | Purpose |
|------|-------|---------|
| [[session_env_setup.sh|hooks/session_env_setup.sh]] | SessionStart | Set AOPS, PYTHONPATH |
| [[sessionstart_load_axioms.py|hooks/sessionstart_load_axioms.py]] | SessionStart | Inject FRAMEWORK, AXIOMS, CORE |
| [[prompt_router.py|hooks/prompt_router.py]] | UserPromptSubmit | Skill routing + focus reminder |
| [[policy_enforcer.py|hooks/policy_enforcer.py]] | PreToolUse | Block destructive operations |
| [[autocommit_state.py|hooks/autocommit_state.py]] | PostToolUse | Auto-commit data/ changes |
| [[unified_logger.py|hooks/unified_logger.py]] | ALL events | Log metadata to hook logs |

## Exit Code Semantics

### PreToolUse Hooks

| Exit | Behavior | Message shown to |
|------|----------|------------------|
| 0 | Allow | JSON stdout (verbose mode) |
| 1 | Warn but allow | stderr → **user AND agent** |
| 2 | Block execution | stderr → **agent only** |

### PostToolUse Hooks

Tool has already executed - exit codes control feedback, not execution.

| Exit | Behavior | Message shown to |
|------|----------|------------------|
| 0 | Success | JSON stdout (verbose mode) |
| 1 | Non-blocking error | stderr (verbose mode only) |
| 2 | Report to agent | stderr → **agent** (for action) |

**Fail-fast rule**: If a PostToolUse hook detects a problem the agent should know about (e.g., autocommit failed), use exit 2 so Claude sees the error.

## Router Architecture

All hooks are dispatched through a single [[router.py|hooks/router.py]] per event type. This consolidates multiple hook outputs into a single response.

### Why Router?

**Problem**: Claude Code reports "success" for each hook that exits 0. With 4 hooks per SessionStart, the agent sees:

```
SessionStart:startup hook success: Success (×4)
UserPromptSubmit hook success: Success (×3)
```

This noise trains agents to skim past system-reminders, causing important guidance to be ignored.

**Solution**: Single router script that:
1. Dispatches to registered sub-hooks internally
2. Merges outputs (additionalContext concatenated, permissions aggregated)
3. Returns single consolidated response
4. Returns worst exit code (any failure = overall failure)

### Output Consolidation Rules

| Field | Merge Strategy |
|-------|---------------|
| `additionalContext` | Concatenate with `\n\n---\n\n` separator |
| `systemMessage` | Concatenate with `\n` |
| `permissionDecision` | **deny > ask > allow** (strictest wins) |
| `continue` | AND logic (any false = false) |
| `suppressOutput` | OR logic (any true = true) |
| exit code | MAX (worst wins: 2 > 1 > 0) |

### Async Dispatch

For UserPromptSubmit, the intent router (`prompt_router.py`) runs async to maximize its execution time:
1. Start intent router async
2. Run other hooks sync
3. Collect intent router result
4. Merge all outputs

### Adding New Hooks

To add a hook, register it in `HOOK_REGISTRY` in [[router.py|hooks/router.py]]:

```python
HOOK_REGISTRY = {
    "SessionStart": [
        {"script": "session_env_setup.sh"},
        {"script": "your_new_hook.py"},
        ...
    ],
}
```

For async execution, add `"async": True`:
```python
{"script": "slow_hook.py", "async": True}
```
