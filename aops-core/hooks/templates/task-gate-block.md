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

⏸️ **Task Binding Required**

Before modifying files, bind your work to a task. This helps you:

- **Track progress**: See what's done, what's pending
- **Enable handover**: Clean session end with context preserved
- **Verify work**: QA can check against task acceptance criteria

**Current status**:

- Task bound: {task_bound_status}
- Hydrator invoked: {hydrator_invoked_status}
- Critic invoked: {critic_invoked_status}

**To bind a task**:

- **Create new**: `mcp__plugin_aops-core_task_manager__create_task(task_title="...", type="task")`
- **Claim existing**: `mcp__plugin_aops-core_task_manager__update_task(id="task-id", status="in_progress")`
- **Find available**: `mcp__plugin_aops-core_task_manager__list_tasks(status="active")`

{missing_gates}

**Bypass**: User can prefix prompt with `.` for quick fixes that skip task binding.
