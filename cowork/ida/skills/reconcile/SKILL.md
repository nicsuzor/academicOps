---
name: reconcile
description: Maintain task graph truth against repository, PR, release, and session state by resolving and executing the universal truth-maintenance reconciliation workflow template. Use for graph reconciliation, stale-claim recovery, PR/release sync, or post-absence catch-up. Exclude for new task intake (use /q) or dispatching ready tasks (use /dispatch).
---

# /reconcile -- Task Graph Truth Maintenance

Maintain consistency between the PKB task graph, repository PRs/releases, active sessions, and the daily note.

## Procedure

Resolve and execute the universal graph-reconciliation workflow template from `/workflow-library` (enumerating universal templates via native file tools or composing via `/reify`):

1. **Single-flight and scoped load**: Check for an active reconciliation lock and scope queries by `since: <cursor_utc>` when provided.
2. **Reconcile state**: Advance open asks via groundwork, sync PRs and releases, clear non-user `review` tasks, roll up bounded composite tasks, settle `failed` tasks from composite parents, check formal evidence sufficiency, reset stale claims, and prune falsified nodes.
3. **Emit report**: Return one synthesized summary naming affected task IDs and next pickup boundary.
