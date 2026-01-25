---
name: task-gate-warn
title: Three-Gate Check Warning Message
category: template
description: |
  Warning message when in warn-only mode without full gate compliance.
  Variables:
    {task_bound_status} - Gate status indicator
    {critic_invoked_status} - Gate status indicator
    {todo_with_handover_status} - Gate status indicator
---
THREE-GATE CHECK (warn-only): Destructive operation without full gate compliance.

Gate status:
- Task bound: {task_bound_status}
- Critic invoked: {critic_invoked_status}
- Todo with handover: {todo_with_handover_status}

This session is in WARN mode for testing. In production, this would BLOCK.
