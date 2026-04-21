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

| Variable              | Default | Values                 | Description                                       |
| --------------------- | ------- | ---------------------- | ------------------------------------------------- |
| `ENFORCER_GATE_MODE`  | `block` | `warn`, `block`        | Controls enforcer compliance audit enforcement    |
| `HYDRATION_GATE_MODE` | `off`   | `off`, `warn`, `block` | Controls hydration gate enforcement               |
| `QA_GATE_MODE`        | `block` | `warn`, `block`        | Controls QA gate enforcement                      |
| `COMMIT_GATE_MODE`    | `warn`  | `warn`, `block`        | Controls commit gate enforcement                  |
| `HANDOVER_GATE_MODE`  | `warn`  | `warn`, `block`        | Controls handover (finalization) gate enforcement |

## Enforcement Hooks

### PreToolUse Hooks

| Hook                     | Mode      | Description                                  |
| ------------------------ | --------- | -------------------------------------------- |
| `command_intercept.py`   | transform | Transforms tool inputs (e.g., Glob excludes) |
| `overdue_enforcement.py` | warn      | Injects reminders for overdue tasks          |

### PostToolUse Hooks

| Hook               | Mode         | Description                                     |
| ------------------ | ------------ | ----------------------------------------------- |
| `enforcer_gate.py` | configurable | Periodic compliance audit (every ~7 tool calls) |
| `handover_gate.py` | passive      | Clears stop gate when /dump invoked             |

## Enforcer Compliance Audit

The enforcer gate runs periodically (every ~7 tool calls) to check for:

- Ultra vires behavior (acting beyond granted authority)
- Scope creep (work expanding beyond original request)
- Infrastructure failure workarounds (violates A8 — Halt on Failure)
- SSOT violations

### Output Formats

| Output  | Mode  | Effect                                       |
| ------- | ----- | -------------------------------------------- |
| `OK`    | any   | No issues found, continue                    |
| `WARN`  | warn  | Issues found, advisory warning surfaced      |
| `BLOCK` | block | Issues found, session halted until addressed |

**Mode control**: Set `ENFORCER_GATE_MODE=block` to enable blocking (default: `block`)

### Block Flag Mechanism

When mode is `block` and the enforcer outputs `BLOCK`:

1. Block record saved to `$ACA_DATA/enforcer/blocks/`
2. Session block flag set via `compliance_block.py`
3. All subsequent hooks check and fail until cleared
4. User must clear the block to continue

## Changing Modes

To switch from warn to block mode:

```bash
# In settings.local.json or CLAUDE_ENV_FILE
export ENFORCER_GATE_MODE=block
export QA_GATE_MODE=block
export HANDOVER_GATE_MODE=block
```

Or set at session start in `session_env_setup.sh`.

## Supervisor Plan-Review Gate

**Location**: `aops-core/skills/supervisor/instructions/decomposition-and-review.md` — Phase 2.5

**What it enforces**: After decomposition + Phase 2 review synthesis, the supervisor MUST check whether the parent task's `status == "queued"` before dispatching any subtasks. If the parent is not yet `queued`, the supervisor posts a synthesis summary, sets parent `status = "ready"`, and STOPS — no subtasks are dispatched.

**Condition**: `parent.status != "queued"` → HALT; `parent.status == "queued"` → proceed to DISPATCH.

**Approval record**: The `ready → queued` status transition performed by the human IS the approval record. No separate marker or metadata.

**Mode**: Always block — there is no warn-only bypass for this gate.

---

## Adding New Enforcement

Per P#65, when adding enforcement measures:

1. Implement the enforcement logic in a hook
2. Add environment variable for mode control (default: warn)
3. Document in this file
4. Test in warn mode before enabling block mode
