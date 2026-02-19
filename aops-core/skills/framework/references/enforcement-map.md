---
title: Enforcement Map
category: reference
description: |
  Documents all enforcement mechanisms in the academicOps framework.
  Per P#65: When adding enforcement measures, update this file.
---

# Enforcement Map

This document tracks all enforcement mechanisms in the academicOps framework.

## Environment Variables

| Variable                  | Default | Values          | Description                                     |
| ------------------------- | ------- | --------------- | ----------------------------------------------- |
| `CUSTODIET_MODE`          | `warn`  | `warn`, `block` | Controls custodiet compliance audit enforcement |
| `HYDRATION_GATE_MODE` ... |         |                 |                                                 |
| `HANDOVER_MODE` ...       |         |                 |                                                 |

## Enforcement Hooks

### PreToolUse Hooks

| Hook                     | Mode         | Description                                                          |
| ------------------------ | ------------ | -------------------------------------------------------------------- |
| `hydration_gate.py`      | warn/block   | Blocks until prompt-hydrator invoked                                 |
| `axiom_enforcer`         | **DISABLED** | Real-time detection of P#8 (Fail-Fast) and P#26 (Write-Without-Read) |
| `command_intercept.py`   | transform    | Transforms tool inputs (e.g., Glob excludes)                         |
| `overdue_enforcement.py` | warn         | Injects reminders for overdue tasks                                  |

### PostToolUse Hooks

| Hook                                | Mode    | Description                                                     |
| ----------------------------------- | ------- | --------------------------------------------------------------- |
| `gate_registry.py:accountant`       | passive | General state tracking (hydration, custodiet, handover)         |
| `gate_registry.py:task_binding`     | passive | Binds task to session on create/claim                           |
| `gate_registry.py:skill_activation` | passive | Clears hydration pending on non-infrastructure skill activation |

## Custodiet Compliance Audit

Custodiet runs periodically (every ~7 tool calls) to check for:

- Ultra vires behavior (acting beyond granted authority)
- Scope creep (work expanding beyond original request)
- Infrastructure failure workarounds (violates P#9, P#25)
- SSOT violations

## Axiom Enforcement (axiom_enforcer)

**Status**: **DISABLED** (as of 2026-02-04)

The `axiom_enforcer` gate provided real-time detection of axiom violations during `Edit`/`Write` operations:

- **P#8 (Fail-Fast)**: Detected code patterns like `except: pass`, `os.environ.get(..., default)`, and other silent fallbacks.
- **P#26 (Verify First)**: Detected "Write-Without-Read" violations, blocking writes to files that hadn't been read in the current session.

**Rationale for Disabling**: Delegated responsibility for these checks to the agent software (Gemini CLI / Claude Code) to reduce framework overhead and friction during interactive sessions.

### Output Formats

| Output  | Mode  | Effect                                       |
| ------- | ----- | -------------------------------------------- |
| `OK`    | any   | No issues found, continue                    |
| `WARN`  | warn  | Issues found, advisory warning surfaced      |
| `BLOCK` | block | Issues found, session halted until addressed |

**Mode control**: Set `CUSTODIET_GATE_MODE=block` to enable blocking (default: `warn`)

### Block Flag Mechanism

When mode is `block` and custodiet outputs `BLOCK`:

1. Block record saved to `$ACA_DATA/custodiet/blocks/`
2. Session block flag set via `custodiet_block.py`
3. All subsequent hooks check and fail until cleared
4. User must clear the block to continue

## Changing Modes

To switch from warn to block mode:

```bash
# In settings.local.json or CLAUDE_ENV_FILE
export CUSTODIET_GATE_MODE=block
```

Or set at session start in `session_env_setup.sh`.

## Adding New Enforcement

Per P#65, when adding enforcement measures:

1. Implement the enforcement logic in a hook
2. Add environment variable for mode control (default: warn)
3. Document in this file
4. Test in warn mode before enabling block mode
