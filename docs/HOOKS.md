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
| `session_env_setup.sh` | SessionStart | Set AOPS, PYTHONPATH |
| `sessionstart_load_axioms.py` | SessionStart | Inject FRAMEWORK, AXIOMS, CORE |
| `prompt_router.py` | UserPromptSubmit | Skill routing + focus reminder |
| `policy_enforcer.py` | PreToolUse | Block destructive operations |
| `autocommit_state.py` | PostToolUse | Auto-commit STATE.md changes |
| `unified_logger.py` | ALL events | Log to hook logs (no context) |

## See Also

- **`docs/JIT-INJECTION.md`** - Complete hook details, injection points, data sources
- **`docs/OBSERVABILITY.md`** - Session logging, transcript viewing
