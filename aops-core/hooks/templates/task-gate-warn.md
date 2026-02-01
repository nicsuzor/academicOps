---
name: task-gate-warn
title: TASK GATE Warning Message
category: template
description: |
  Warning message when in warn-only mode without full gate compliance.
  Variables:
    {task_bound_status} - Gate status indicator
    {hydrator_invoked_status} - Gate status indicator
    {critic_invoked_status} - Gate status indicator
---
TASK GATE (warn): Missing gate compliance (other gates may still block).

Gate status:
- Task bound: {task_bound_status}
- Hydrator invoked: {hydrator_invoked_status}
- Critic invoked: {critic_invoked_status}
