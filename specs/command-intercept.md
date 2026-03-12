---
name: command-intercept
title: Command Intercept
category: spec
status: draft
type: spec
tier: core
depends_on: []
created: 2026-01-25
tags: [spec, hooks, tool-transformation]
---

# Command Intercept

## Giving Effect

- [[hooks/command_intercept.py]] - PreToolUse hook that intercepts and transforms tool calls
- [[hooks/gate_registry.py]] - Registry for tool-specific intercept behaviors
- [[hooks/gate_config.py]] - Configuration for intercept rules

## Feature Purpose

A modular PreToolUse hook

that intercepts and transforms tool calls before execution. Tools without registered transformers **pass through unchanged**, but the system requires explicit configuration (P#8).

### Problem Statement

Claude Code's built-in tools (Glob, Grep, etc.) have fixed behaviors that sometimes conflict with project needs:

- **Glob** does not respect `.gitignore`, returning `.venv/`, `node_modules/`, and other noise
- **Grep** respects `.gitignore` but may need additional exclusions
- Other tools may need parameter normalization or augmentation

Currently, the only options are:

1. Block the tool entirely (too restrictive)
2. Accept the default behavior (wastes context on noise)

### Solution

Intercept tool calls at PreToolUse and use Claude Code's `updatedInput` capability to modify parameters before execution. This allows transparent transformation without blocking.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PreToolUse Event                        │
│                  (tool_name, tool_input)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   command_intercept.py                       │
│                                                              │
│  1. Load config from $ACA_DATA/command_intercept.yaml       │
│  2. Check if tool_name has registered transformer           │
│  3. If yes: apply transformation, return updatedInput       │
│  4. If no: pass through (no-op)                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               hookSpecificOutput                             │
│  {                                                          │
│    "hookEventName": "PreToolUse",                           │
│    "permissionDecision": "allow",                           │
│    "updatedInput": { ...modified params... }                │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Location

`$ACA_DATA/command_intercept.yaml`

### Schema

```yaml
# command_intercept.yaml
# Modular tool transformations for PreToolUse hook

version: 1

# Global settings
enabled: true  # Master switch (default: true)

# Per-tool transformers
tools:
  Glob:
    enabled: true
    transformers:
      - name: exclude_directories
        config:
          patterns:
            - ".venv"
            - "node_modules"
            - "__pycache__"
            - ".git"
            - "*.egg-info"

  # Future: Grep exclusions, Bash normalization, etc.
  # Grep:
  #   enabled: true
  #   transformers:
  #     - name: add_default_excludes
  #       config:
  #         glob_excludes: ["*.min.js", "*.map"]
```

### Default Behavior

When a tool has no registered transformers: **pass through unchanged** (no-op). A missing or invalid config file is a misconfiguration error — the hook must fail fast (P#8), not silently pass through.

## First Transformer: `exclude_directories`

### Transformer Purpose

Add exclusion patterns

to Glob calls to filter out directories that should not be searched.

### Implementation

```python
def transform_glob_exclude_directories(
    tool_input: dict[str, Any],
    config: dict[str, Any]
) -> dict[str, Any]:
    """
    Transform Glob input to exclude configured directories.

    Since Glob doesn't support exclusions natively, we modify the
    pattern to use negative lookahead or post-filter the path.

    Strategy: If pattern is "**/*.py", transform to exclude paths
    containing configured directories.
    """
    patterns = config.get("patterns", [])
    if not patterns:
        return tool_input  # No-op

    # Option A: Modify path to be more specific (if searching from root)
    # Option B: Return updatedInput with additionalContext warning
    # Option C: Use glob's path parameter to narrow scope

    # For now: Add context warning that exclusions are advisory
    # until we determine best strategy

    return tool_input  # Implementation TBD
```

### Limitation

Glob does not support exclusion patterns natively. Strategies to evaluate:

1. **Path scoping**: If `path` not set, default to `./src` or similar
2. **Pattern rewriting**: Transform `**/*.py` to `!(.*venv*)/**/*.py` (if supported)
3. **Advisory context**: Add `additionalContext` warning the agent to filter results
4. **Tool substitution**: Return `permissionDecision: "deny"` with message to use `fd` instead

**Recommendation**: Start with option 3 (advisory context) and evaluate option 4 (tool substitution) if advisory proves insufficient.

## Hook Registration

Register in `GateRegistry` (see `router.py`):

```python
"PreToolUse": [
    {"script": "unified_logger.py"},
    {"script": "hydration_gate.py"},
    {"script": "command_intercept.py"},  # NEW: Before policy_enforcer
    {"script": "policy_enforcer.py"},
    {"script": "overdue_enforcement.py"},
],
```

Position after `hydration_gate.py` (so hydration runs first) and before `policy_enforcer.py` (so policy can validate transformed input).

## File Structure

```
aops-core/
├── hooks/
│   ├── command_intercept.py     # Main hook dispatcher
│   └── transformers/
│       ├── __init__.py
│       └── glob_exclude.py      # First transformer
├── specs/
│   └── command-intercept.md     # This spec
```

## Output Format

### When transformation applied

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {
      "pattern": "src/**/*.py"
    },
    "additionalContext": "Glob transformed: excluded .venv, node_modules"
  }
}
```

### When no transformation (pass-through)

```json
{}
```

Empty output = no modification, hook router continues to next hook.

## Extension Points

### Adding New Transformers

1. Create transformer module in `hooks/transformers/`
2. Register in config under `tools.<ToolName>.transformers`
3. Transformer receives `(tool_input, config)`, returns modified `tool_input`

### Transformer Interface

```python
from typing import Any, Protocol

class Transformer(Protocol):
    """Transformer protocol for command_intercept."""

    def transform(
        self,
        tool_input: dict[str, Any],
        config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Transform tool input.

        Args:
            tool_input: Original tool parameters
            config: Transformer-specific config from YAML

        Returns:
            Modified tool_input (or original if no changes)
        """
        ...
```

## Testing

### Unit Tests

```python
def test_glob_exclude_passthrough_when_disabled():
    """When transformer disabled, input unchanged."""

def test_glob_exclude_adds_context_warning():
    """When enabled, adds advisory context about exclusions."""

def test_missing_config_fails_fast():
    """Missing config file = error, not silent pass-through (P#8)."""

def test_unknown_tool_is_noop():
    """Tools not in config pass through unchanged."""
```

### Integration Test

```python
def test_glob_excludes_venv_in_real_session():
    """
    End-to-end: Glob call in real Claude Code session
    should not return .venv files.
    """
```

## Implementation Phases

### Phase 1: Infrastructure (this spec)

- [x] Router support for `updatedInput` (implemented in `router.py`)
- [ ] Create `command_intercept.py` hook skeleton
- [ ] Register in `GateRegistry`
- [ ] Load config from `$ACA_DATA/command_intercept.yaml`
- [ ] Fail with error when config is missing or invalid (P#8)

### Phase 2: First Transformer

- [ ] Implement `glob_exclude.py` transformer
- [ ] Strategy: Advisory context (option 3)
- [ ] Test with real Glob calls

### Phase 3: Evaluate & Iterate

- [ ] Measure effectiveness of advisory approach
- [ ] If insufficient, implement tool substitution (option 4)
- [ ] Add Grep transformer if needed

## User Expectations

This section defines the verifiable behavior of the command intercept system. Note that while the routing infrastructure supports tool transformation, the active interceptor and transformers are currently in the design phase.

### Current State: Passive Pass-through

- **Expectation**: By default, all tool calls pass through the framework without modification.
- **Pass Criteria**: A `Glob` or `Grep` call returns results matching standard Claude Code / Gemini CLI behavior.
- **Pass Criteria**: The hook output is empty (`{}`), indicating no transformation was attempted.

### Design Goal: Transparent Transformation

- **Expectation**: When a transformation is applied, the agent and user are notified of the change to maintain epistemic integrity (P#115).
- **Pass Criteria**: The hook response contains `updatedInput` with modified parameters.
- **Pass Criteria**: The hook response contains `additionalContext` or `systemMessage` explaining what was transformed (e.g., "Glob transformed: excluded .venv").

### Design Goal: Fail-Fast Configuration

- **Expectation**: The system surfaces configuration errors immediately (P#8). A missing or invalid config is a misconfiguration that must be reported, not silently bypassed.
- **Pass Criteria**: If `$ACA_DATA/command_intercept.yaml` is missing, malformed, or has an invalid version, the hook exits with a non-zero status and a clear error message identifying the problem.
- **Fail Criteria**: A configuration error is silently ignored and the hook passes through as if no config existed.

### Design Goal: Context Noise Reduction

- **Expectation**: The `exclude_directories` transformer for `Glob` reduces context waste by filtering out high-noise directories.
- **Pass Criteria**: With the transformer active and configured to exclude `node_modules`, a `Glob` search for `**/*.js` does not return any files from `node_modules/`.

## Related

- [[hook-router]] - Hook routing architecture
- [[enforcement-map]] - Policy enforcement patterns
- Task `framework-1a9ab370` - Original request for .venv exclusion
