---
name: hook-router
title: Hook Router
category: spec
---

# Hook Router

## Giving Effect

- [[hooks/router.py]] - Single entry point that dispatches to registered sub-hooks
- [[hooks/hooks.json]] - Hook registration configuration
- [[hooks/gate_registry.py]] - Gate registration and configuration

## Router Architecture

The gates.py gate locking / unlocking is really buggy. we've spent way too much time trying to debug it for gemini cli and claude code, and it always seems like there's dead code lying around, backwards compatible code messing things up and confusing me, and bug fixes that create weird unintended consequences. Let's completely refactor and redesign the system to be much more robust? I want it to be configurable and modular, but most of all i want it to be robust.

- All hooks are dispatched through a single [[router.py|hooks/router.py]].
- Introduce a single pydantic state object that we load at the very start of unified router and save to disk at the very end only.
- Create a single pydantic class that represents a gate configuration. factor down what every gate needs: open/closed, match conditions, messages, etc etc. no more loosely structured config dicts.
- Work out how to create a gate Protocol or superclass that implements the logic of gates consistently. All gates basically need state update to do the same thing: match a pattern in the combination of hook name, caller, hook input and current state.
- So each gate should be configured with a list of matching criteria for state transitions (open -> close, close -> open, open -> open, close -> close) and then record all the same state variables (open y/n, turns_since_state_change (or turns_since_last_open?), time_since_last_open. gates should also specify the user message and the context injection template to be filled on each state transition or event.
- We should avoid having, for example, HydrationState.turns_since_hydration and different state objects for other gates, and definitely avoid the duplication we'd get if we had HydrationState.turns_since_critic and CriticState.status. all gate config and state objects should be strongly typed.
- Adding new gates should be easy if we have generic config and generic matchers: create a new configuration, specify the transitions, specify the filename of the templates for messages, and that's it.

## Gate Block Feedback (Claude vs Gemini)

When gates block tool execution, the feedback mechanism differs by client. We have a translation layer that converts our aggregated hook result to gemini-cli / claude code expected formats.

### Why Router instead of individual exit codes?

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

| Field                | Merge Strategy                           |
| -------------------- | ---------------------------------------- |
| `additionalContext`  | Concatenate with `\n\n---\n\n` separator |
| `systemMessage`      | Concatenate with `\n`                    |
| `permissionDecision` | **deny > ask > allow** (strictest wins)  |
| `continue`           | AND logic (any false = false)            |
| `suppressOutput`     | OR logic (any true = true)               |
| exit code            | MAX (worst wins: 2 > 1 > 0)              |

## Plugin-Scoped Hooks

**Critical**: Claude Code hooks are **plugin-scoped**. Hooks defined in a plugin only fire for tools and events from that same plugin.

### Implications

| Scenario                                              | Hooks Fire? |
| ----------------------------------------------------- | ----------- |
| MCP tool in plugin A, hooks defined in plugin A       | ✓ Yes       |
| MCP tool in plugin A, hooks defined in plugin B       | ✗ No        |
| Built-in tool (Bash, Read, etc.), hooks in any plugin | ✓ Yes       |

### Example: Task Manager

The `task_manager` MCP server must be defined in **aops-core** (where hooks are defined), not aops-tools. Otherwise, PreToolUse/PostToolUse hooks won't fire for task operations.

```
# Correct: task_manager in aops-core/.mcp.json
aops-core/
├── .mcp.json          # defines task_manager
├── hooks/hooks.json   # defines PreToolUse, PostToolUse
└── hooks/task_binding.py  # fires for task_manager calls ✓

# Wrong: task_manager in aops-tools/.mcp.json
aops-tools/
├── .mcp.json          # defines task_manager
└── (no hooks)         # task_binding.py never fires ✗
```

### Debugging Hook Scope Issues

If hooks aren't firing for an MCP tool:

1. Check which plugin defines the MCP server (`.mcp.json`)
2. Check which plugin defines the hooks (`hooks/hooks.json`)
3. Ensure they're the **same plugin**
