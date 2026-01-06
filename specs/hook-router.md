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

| Field | Merge Strategy |
|-------|---------------|
| `additionalContext` | Concatenate with `\n\n---\n\n` separator |
| `systemMessage` | Concatenate with `\n` |
| `permissionDecision` | **deny > ask > allow** (strictest wins) |
| `continue` | AND logic (any false = false) |
| `suppressOutput` | OR logic (any true = true) |
| exit code | MAX (worst wins: 2 > 1 > 0) |
