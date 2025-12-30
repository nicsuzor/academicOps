---
title: JIT Context Injection
type: framework-doc
permalink: docs-jit-injection
description: Architecture for just-in-time context injection through hooks and CLAUDE.md files
---

# JIT Context Injection

How agents automatically receive the information they need.

## Summary

| When | What | Source                                             |
| ------------- | ------------------------------- | -------------------------------------------------- | ----------------------------------- |
| Session start | Paths, principles, user context | [[sessionstart_load_axioms.py                      |hooks/sessionstart_load_axioms.py]] |
| Session start | Project instructions | Claude Code native (CLAUDE.md and AGENTS.md files) |
| Every prompt | Context enrichment (planned) | [[user_prompt_submit.py|hooks/user_prompt_submit.py]] |
| Before tool | Policy enforcement | [[policy_enforcer.py                               |hooks/policy_enforcer.py]] |
| On demand | Skill instructions | `Skill(skill="X")`                                 |

**Design principle**: Agents should NOT need to search for context. Missing context = framework bug. (AXIOM 22)

## Hook Details

### SessionStart: [[sessionstart_load_axioms.py|hooks/sessionstart_load_axioms.py]]

Loads and injects as `additionalContext`:

| File | Path | Content |
|------|------|---------|
| [[FRAMEWORK.md|FRAMEWORK.md]] | `$AOPS/FRAMEWORK.md` | Path table |
| [[AXIOMS.md|AXIOMS.md]] | `$AOPS/AXIOMS.md` | Inviolable principles |
| CORE.md | `$ACA_DATA/CORE.md` | User context |

**Fail-fast**: Exits code 1 if any file missing or empty.

### UserPromptSubmit: [[user_prompt_submit.py|hooks/user_prompt_submit.py]]

**Current state**: Returns noop (empty JSON). Prompt Enricher planned but not yet implemented.

**Planned** (see `specs/prompt-enricher.md`):
- Classify task type
- Gather relevant context via memory search
- Select applicable guardrails
- Return enriched context to main agent

### PreToolUse: [[policy_enforcer.py|hooks/policy_enforcer.py]]

Blocks:
- `*-GUIDE.md` files (MINIMAL principle)
- `.md` files > 200 lines
- Destructive git: `reset --hard`, `clean -f`, `push --force`, `checkout -- .`, `stash drop`

Returns `{continue: false, systemMessage: "..."}` when blocked.

### PostToolUse: [[autocommit_state.py|hooks/autocommit_state.py]]

Auto-commits `data/` changes after state-modifying operations.

---

## Where to Find Injected Context

All hook injections are logged to `~/.claude/projects/<project>/<date>-<shorthash>-hooks.jsonl`

| Look For | In Field | Event Type |
|----------|----------|------------|
| AXIOMS/FRAMEWORK/CORE content | `additionalContext` | SessionStart |
| Skill routing suggestions | `additionalContext` | UserPromptSubmit |
| Policy blocks | `systemMessage` | PreToolUse |
| Full tool output | `tool_response` | PostToolUse |
| User's exact prompt | `prompt` | UserPromptSubmit |
| Tool parameters | `tool_input` | PreToolUse, PostToolUse |

**Query example**:
```bash
jq 'select(.additionalContext != null)' *-hooks.jsonl
```

See [[OBSERVABILITY.md|docs/OBSERVABILITY.md]] for complete hook log schema.

---

## CLAUDE.md Files (Claude Code Native)

Claude Code loads these at session start (not via aOps hooks).

**Loading order** (higher = higher precedence):
1. Enterprise policy paths
2. `./CLAUDE.md` or `./.claude/CLAUDE.md` (project root)
3. `./.claude/rules/*.md` (project rules)
4. `~/.claude/rules/*.md` (user rules)
5. `~/.claude/CLAUDE.md` (user defaults)

**Special**: `./CLAUDE.local.md` for personal config (don't commit).

**Upward recursion**: From cwd, loads all CLAUDE.md files going up.

**Subtree discovery**: Nested CLAUDE.md in subdirectories loads when Claude reads files there.

**Imports**: Use `@path/to/file` to import (max 5 hops).

---

## Test Coverage

| Hook                            | Tests                                                                                                                                     |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| [[sessionstart_load_axioms.py]] | `test_sessionstart_hook_format.py`, `test_session_start_loading.py`, `integration/test_session_start_content.py`                          |
| [[user_prompt_submit.py]]       | `test_userpromptsubmit_contract.py` |
| [[policy_enforcer.py]]          | `integration/test_git_safety_hook.py`                                                                                                     |
| [[autocommit_state.py]]         | `integration/test_autocommit_data.py`                                                                                                     |
| [[session_env_setup.sh]]        | **GAP**                                                                                                                                   |
| [[unified_logger.py]]           | **GAP**                                                                                                                                   |
