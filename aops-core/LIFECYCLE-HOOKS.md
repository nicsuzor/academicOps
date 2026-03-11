---
name: lifecycle-hooks
title: Lifecycle Hook Configuration
type: index
category: framework
description: |
    Configurable lifecycle trigger hooks for the swarm-supervisor workflow.
    Minimal shell scripts that check preconditions and start agent sessions.
    All dispatch decisions (which runners, how many, which tasks) are made
    by the supervisor agent, not by these scripts.
permalink: lifecycle-hooks
tags: [framework, hooks, lifecycle, swarm, index]
---

> **Design principle**: Agents decide, code triggers. These hooks contain
> zero decision logic. They check preconditions (is queue non-empty?) and
> start supervisor sessions. The supervisor reads [[WORKERS.md]] and makes
> all dispatch decisions.

# Lifecycle Hooks

## Hook Registry

| Hook          | Script           | Trigger        | Purpose                                     |
| ------------- | ---------------- | -------------- | ------------------------------------------- |
| `queue-drain` | `queue-drain.sh` | cron, manual   | Start supervisor session if tasks are ready |
| `post-finish` | `post-finish.sh` | polecat finish | Notify on task completion/failure           |
| `stale-check` | `stale-check.sh` | cron, manual   | Detect and reset stalled tasks              |
| `merge-ready` | `merge-ready.sh` | cron, manual   | List merge-ready PRs and notify             |

Scripts live in `scripts/hooks/lifecycle/`.

> **Note**: Protocol retrospection is NOT a hook. It is a workflow step
> within the supervisor's post-merge phase (Phase 6b in the workflow spec).
> The supervisor already has access to transcripts and task bodies — it
> doesn't need a separate script to gather them.

## Decision Boundary

What shell hooks do vs what the supervisor agent does:

| Concern                       | Shell hooks           | Supervisor agent                   |
| ----------------------------- | --------------------- | ---------------------------------- |
| Is queue empty?               | Yes (grep task files) | No                                 |
| Which runners to use?         | No                    | Yes (reads WORKERS.md)             |
| How many workers?             | No                    | Yes (reads queue depth + task mix) |
| Which tasks get which worker? | No                    | Yes (reads task tags + complexity) |
| Send notifications?           | Yes (mechanical)      | No                                 |
| Reset stale tasks?            | Yes (threshold check) | No                                 |
| Merge PRs?                    | No                    | Human or supervisor session        |
| Identify process friction?    | No                    | Yes (Phase 6b retrospection)       |
| Improve own protocol?         | No                    | Yes (delegates to /learn)          |

## Notification Configuration

The only configuration these hooks need — how to notify humans.

| Parameter    | Default       | Description                                             |
| ------------ | ------------- | ------------------------------------------------------- |
| `NOTIFY_CMD` | `notify-send` | Notification command (`notify-send`, `ntfy`, or custom) |
| `NTFY_TOPIC` | `polecat`     | Topic for ntfy.sh notifications                         |

## Stale Check Configuration

| Parameter               | Default | Description                        |
| ----------------------- | ------- | ---------------------------------- |
| `STALE_THRESHOLD_HOURS` | `4`     | Hours before task considered stale |

## Cron Schedule (Example)

```crontab
# Start supervisor if tasks are ready (every 30 min during work hours)
*/30 9-17 * * 1-5  $AOPS/scripts/hooks/lifecycle/queue-drain.sh

# Check for stale tasks every 2 hours
0 */2 * * *        $AOPS/scripts/hooks/lifecycle/stale-check.sh

# Surface merge-ready PRs every hour
0 * * * *          $AOPS/scripts/hooks/lifecycle/merge-ready.sh
```

## Manual Invocation

```bash
# Start a supervisor session to drain the queue
./scripts/hooks/lifecycle/queue-drain.sh

# Dry run — see what the supervisor would be asked
./scripts/hooks/lifecycle/queue-drain.sh --dry-run

# Filter to a project
./scripts/hooks/lifecycle/queue-drain.sh -p aops-core

# Check for stale tasks (dry run by default)
./scripts/hooks/lifecycle/stale-check.sh
./scripts/hooks/lifecycle/stale-check.sh --reset

# List merge-ready PRs
./scripts/hooks/lifecycle/merge-ready.sh
```

## Adding a New Hook

1. Create script in `scripts/hooks/lifecycle/`
2. Script should only check preconditions and start an agent session (or run a mechanical command)
3. Add row to Hook Registry above
4. Any decision logic goes in the supervisor skill prompt, not the script
