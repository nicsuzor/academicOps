---
name: hook-router
title: Hook Router
category: spec
---

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

| Scenario | Hooks Fire? |
|----------|-------------|
| MCP tool in plugin A, hooks defined in plugin A | ✓ Yes |
| MCP tool in plugin A, hooks defined in plugin B | ✗ No |
| Built-in tool (Bash, Read, etc.), hooks in any plugin | ✓ Yes |

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
