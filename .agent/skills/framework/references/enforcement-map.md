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

| Variable         | Default | Values          | Description                                             |
| ---------------- | ------- | --------------- | ------------------------------------------------------- |
| `TASK_GATE_MODE` | `warn`  | `warn`, `block` | Controls four-gate enforcement in task_required_gate.py |
| `CUSTODIET_MODE` | `warn`  | `warn`, `block` | Controls custodiet compliance audit enforcement         |

## Enforcement Hooks

### PreToolUse Hooks

| Hook                     | Mode         | Description                                  |
| ------------------------ | ------------ | -------------------------------------------- |
| `hydration_gate.py`      | warn/block   | Blocks until prompt-hydrator invoked         |
| `task_required_gate.py`  | configurable | Four-gate check for destructive operations   |
| `command_intercept.py`   | transform    | Transforms tool inputs (e.g., Glob excludes) |
| `overdue_enforcement.py` | warn         | Injects reminders for overdue tasks          |

### PostToolUse Hooks

| Hook                         | Mode         | Description                                     |
| ---------------------------- | ------------ | ----------------------------------------------- |
| `custodiet_gate.py`          | configurable | Periodic compliance audit (every ~7 tool calls) |
| `task_binding.py`            | passive      | Binds task to session on create/claim           |
| `todowrite_handover_gate.py` | passive      | Sets todo_with_handover gate on TodoWrite       |
| `handover_gate.py`           | passive      | Clears stop gate when /dump invoked             |

## Four-Gate Model (task_required_gate.py)

Destructive operations require ALL FOUR gates to pass:

1. **Task bound** - Session has an active task via update_task or create_task
2. **Plan mode invoked** - EnterPlanMode has been called to design approach
3. **Critic invoked** - Critic agent has reviewed the plan
4. **Todo with handover** - TodoWrite includes a session end/dump step

**Current state**: Only `task_bound` gate is enforced. Other three are tracked but not enforced (for validation).

**Mode control**: Set `TASK_GATE_MODE=block` to enable blocking (default: `warn`)

## Custodiet Compliance Audit

Custodiet runs periodically (every ~7 tool calls) to check for:

- Ultra vires behavior (acting beyond granted authority)
- Scope creep (work expanding beyond original request)
- Infrastructure failure workarounds (violates P#9, P#25)
- SSOT violations

### Output Formats

| Output  | Mode  | Effect                                       |
| ------- | ----- | -------------------------------------------- |
| `OK`    | any   | No issues found, continue                    |
| `WARN`  | warn  | Issues found, advisory warning surfaced      |
| `BLOCK` | block | Issues found, session halted until addressed |

**Mode control**: Set `CUSTODIET_MODE=block` to enable blocking (default: `warn`)

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
export CUSTODIET_MODE=block
export TASK_GATE_MODE=block
```

Or set at session start in `session_env_setup.sh`.

## Stop Hooks

| Hook / Condition         | Mode      | Description                                                                                                           |
| ------------------------ | --------- | --------------------------------------------------------------------------------------------------------------------- |
| `reflection_check.py`    | block     | Blocks session end until Framework Reflection with all 8 required fields is present                                  |
| `session_end_commit_check.py` | block | Blocks if uncommitted changes exist when reflection or test success detected                                         |
| `uac_verified` condition | soft gate | Blocks Stop if unchecked `- [ ]` items remain in task UAC section (Acceptance Criteria/Requirements/UAC headers) |

## Adding New Enforcement

Per P#65, when adding enforcement measures:

1. Implement the enforcement logic in a hook
2. Add environment variable for mode control (default: warn)
3. Document in this file
4. Test in warn mode before enabling block mode
