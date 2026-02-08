---
name: task-gate-block
title: TASK GATE Block Message
category: template
description: |
  Block message when destructive operation attempted without gate compliance.
  Variables:
    {task_bound_status} - Gate status indicator (✓ or ✗)
    {hydrator_invoked_status} - Gate status indicator (checks plan_mode_invoked)
    {critic_invoked_status} - Gate status indicator (✓ or ✗)
    {missing_gates} - Newline-separated list of missing gate instructions
---

⛔ **TASK GATE: Cannot perform destructive operations.**

The unified TASK GATE requires compliance before modifying files:

- Task bound: {task_bound_status}
- Hydrator invoked: {hydrator_invoked_status}
- Critic invoked: {critic_invoked_status}

**Missing gates:**
{missing_gates}

For emergency/trivial fixes, user can prefix prompt with `.`
