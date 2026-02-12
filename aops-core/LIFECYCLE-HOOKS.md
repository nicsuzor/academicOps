---
name: lifecycle-hooks
title: Lifecycle Hook Configuration
type: index
category: framework
description: |
    Configurable lifecycle trigger hooks for the swarm-supervisor workflow.
    Shell scripts that invoke lifecycle phases. Modify this file to change
    trigger behavior without editing skill prompts or hook scripts.
permalink: lifecycle-hooks
tags: [framework, hooks, lifecycle, swarm, index]
---

> **Deployment-specific configuration** - Customize for your environment.
> Hook scripts are in `scripts/hooks/lifecycle/`. This file contains only
> the configurable parameters they read at runtime.

# Lifecycle Hook Configuration

Trigger hooks are minimal shell scripts that start agent work at lifecycle
boundaries. They don't contain logic — they invoke `polecat` commands or
agent sessions and let the supervisor/worker prompts make all decisions.

## Hook Registry

Available lifecycle hooks and their triggers.

| Hook | Script | Trigger | Purpose |
|------|--------|---------|---------|
| `queue-drain` | `queue-drain.sh` | cron, manual | Drain ready tasks via polecat swarm |
| `post-finish` | `post-finish.sh` | polecat finish | After worker finishes: notify, capture |
| `stale-check` | `stale-check.sh` | cron, manual | Detect and reset stalled tasks |
| `merge-ready` | `merge-ready.sh` | cron, manual | Surface merge-ready PRs for review |

## Queue Drain Configuration

Settings for `queue-drain.sh` — the main trigger that starts worker execution.

| Parameter | Value | Description |
|-----------|-------|-------------|
| `MIN_READY_TASKS` | `1` | Minimum ready tasks before spawning swarm |
| `DEFAULT_PROJECT` | (unset) | Project filter (empty = all projects) |
| `CALLER_IDENTITY` | `polecat` | Identity for task claiming |
| `DRY_RUN` | `false` | Simulate without executing |

### Runner Command Template

The queue-drain hook invokes this command to start workers. Replace the
command to use any runner that integrates with the task queue.

```bash
# Default: polecat swarm (spawns claude + gemini workers)
RUNNER_CMD="polecat swarm"

# Alternative: single polecat run
# RUNNER_CMD="polecat run"

# Alternative: custom runner (must claim tasks via MCP API)
# RUNNER_CMD="/path/to/my-runner --queue aops"
```

**Runner contract**: Any runner can be used as long as it:

1. Claims tasks atomically via `claim_next_task()` or `update_task(status=in_progress)`
2. Sets task status on completion (`done`, `merge_ready`, or `blocked`)
3. Exits with standard codes (0=success, 1=failure, 3=queue-empty)

### Swarm Sizing (when using polecat swarm)

> See [[WORKERS.md]] Swarm Sizing Defaults for the full sizing table.

| Parameter | Value | Description |
|-----------|-------|-------------|
| `MAX_CLAUDE_WORKERS` | `2` | Maximum Claude workers to spawn |
| `MAX_GEMINI_WORKERS` | `3` | Maximum Gemini workers to spawn |
| `SWARM_AUTO_SIZE` | `true` | Auto-calculate from queue size |

When `SWARM_AUTO_SIZE` is true, the hook reads the ready task count
and applies the sizing table from WORKERS.md to determine worker counts.

## Post-Finish Configuration

Settings for `post-finish.sh` — runs after a worker completes a task.

| Parameter | Value | Description |
|-----------|-------|-------------|
| `NOTIFY_ON_SUCCESS` | `true` | Send notification on task completion |
| `NOTIFY_ON_FAILURE` | `true` | Send notification on task failure |
| `NOTIFY_CMD` | `notify-send` | Notification command (or `ntfy`, `curl`) |
| `AUTO_MERGE_ATTEMPT` | `true` | Attempt auto-merge after finish |

### Notification Templates

```bash
# Success notification
NOTIFY_SUCCESS_TITLE="Task Complete"
NOTIFY_SUCCESS_BODY="{{task_id}}: {{task_title}}"

# Failure notification
NOTIFY_FAILURE_TITLE="Task Failed"
NOTIFY_FAILURE_BODY="{{task_id}} failed (exit {{exit_code}})"
```

## Stale Check Configuration

Settings for `stale-check.sh` — detects and resets stalled workers.

| Parameter | Value | Description |
|-----------|-------|-------------|
| `STALE_THRESHOLD_HOURS` | `4` | Hours before task considered stale |
| `AUTO_RESET` | `false` | Automatically reset stale tasks |
| `NOTIFY_ON_STALE` | `true` | Notify when stale tasks detected |

## Merge-Ready Configuration

Settings for `merge-ready.sh` — surfaces tasks ready for human review.

| Parameter | Value | Description |
|-----------|-------|-------------|
| `AUTO_MERGE_CLEAN` | `false` | Auto-merge PRs with passing checks |
| `REQUIRE_HUMAN_REVIEW` | `true` | Always require human approval |
| `NOTIFY_CMD` | `notify-send` | How to surface merge-ready tasks |

## Cron Schedule (Example)

```crontab
# Drain queue every 30 minutes during work hours
*/30 9-17 * * 1-5  $AOPS/scripts/hooks/lifecycle/queue-drain.sh

# Check for stale tasks every 2 hours
0 */2 * * *        $AOPS/scripts/hooks/lifecycle/stale-check.sh

# Surface merge-ready PRs every hour
0 * * * *          $AOPS/scripts/hooks/lifecycle/merge-ready.sh
```

## Customization Guide

To customize lifecycle hooks for your deployment:

1. **Change runner**: Edit `RUNNER_CMD` in Queue Drain Configuration
2. **Add notifications**: Change `NOTIFY_CMD` to your preferred method
3. **Adjust timing**: Modify cron schedules above
4. **Add a new hook**: Create script in `scripts/hooks/lifecycle/`, add row to Hook Registry
5. **Disable a hook**: Remove from cron or set `DRY_RUN=true`

Hook scripts read this configuration at runtime. Changes take effect on next
invocation without modifying the scripts themselves.
