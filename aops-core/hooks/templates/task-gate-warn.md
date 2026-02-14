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

📝 **Note**: No task bound (warn mode)

Proceeding, but consider binding a task for better tracking:

- Task bound: {task_bound_status}
- Hydrator invoked: {hydrator_invoked_status}
- Critic invoked: {critic_invoked_status}

**Quick bind**: `mcp__plugin_aops-core_task_manager__create_task(task_title="...", type="task")`

Task binding enables progress visibility, clean handovers, and QA verification.
