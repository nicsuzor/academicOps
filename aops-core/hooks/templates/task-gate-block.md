---
name: task-gate-block
title: TASK GATE Block Message
category: template
description: |
  Block message when destructive operation attempted without gate compliance.
  Variables:
    {task_bound_status} - Gate status indicator
    {hydrator_invoked_status} - Gate status indicator
    {critic_invoked_status} - Gate status indicator
    {missing_gates} - Newline-separated list of missing gate instructions
---
TASK GATE CHECK: Cannot perform destructive operations.

All gates must pass before modifying files:
- Task bound: {task_bound_status}
- Hydrator invoked: {hydrator_invoked_status}
- Critic invoked: {critic_invoked_status}

Missing gates:
{missing_gates}

For emergency/trivial fixes, user can prefix prompt with `.`
