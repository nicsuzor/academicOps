---
name: task-gate-block
title: Four-Gate Check Block Message
category: template
description: |
  Block message when destructive operation attempted without gate compliance.
  Variables:
    {task_bound_status} - Gate status indicator
    {plan_mode_invoked_status} - Gate status indicator
    {critic_invoked_status} - Gate status indicator
    {todo_with_handover_status} - Gate status indicator
    {missing_gates} - Newline-separated list of missing gate instructions
---
FOUR-GATE CHECK FAILED: Cannot perform destructive operations.

All four gates must pass before modifying files:
- Task bound: {task_bound_status}
- Plan mode invoked: {plan_mode_invoked_status}
- Critic invoked: {critic_invoked_status}
- Todo with handover: {todo_with_handover_status}

Missing gates:
{missing_gates}

For emergency/trivial fixes, user can prefix prompt with `.`
