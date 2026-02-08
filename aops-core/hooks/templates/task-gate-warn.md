---
name: task-gate-warn
title: TASK GATE Warning Message
category: template
description: |
  Warning message when in warn-only mode without full gate compliance.
  Variables:
    {task_bound_status} - Gate status indicator (✓ or ✗)
    {hydrator_invoked_status} - Gate status indicator (checks plan_mode_invoked)
    {critic_invoked_status} - Gate status indicator (✓ or ✗)
---

⚠️ **TASK GATE (warn)**: Missing gate compliance.

Gate status:

- Task bound: {task_bound_status}
- Hydrator invoked: {hydrator_invoked_status}
- Critic invoked: {critic_invoked_status}

Proceeding in warn mode. For full enforcement, set `TASK_GATE_MODE=block`.
