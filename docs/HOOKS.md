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
| [[user_prompt_submit.py|hooks/user_prompt_submit.py]] | UserPromptSubmit | Context injection (Prompt Enricher planned) |
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

All hooks are dispatched through a single [[hook-router]]. This consolidates multiple hook outputs into a single response.


### Async Dispatch

Hooks can run async to maximize execution time. Add `"async": True` to the hook config:
1. Start async hook
2. Run other hooks sync
3. Collect async hook result
4. Merge all outputs

**Note**: The Prompt Enricher (planned) will use async dispatch for UserPromptSubmit.

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
