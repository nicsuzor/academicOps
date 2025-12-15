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
| [[autocommit_state.py|hooks/autocommit_state.py]] | PostToolUse | Auto-commit STATE.md changes |
| [[unified_logger.py|hooks/unified_logger.py]] | ALL events | Log metadata to hook logs |
