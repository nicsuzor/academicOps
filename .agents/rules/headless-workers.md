---
trigger: always_on
description: Headless workers cannot pause interactively or escalate to the user; approval boundaries file artifacts on the record, review is transient help, and nested agent CLI sessions are forbidden in polecats.
---

## Workers cannot pause for a person

Workers operate headless in execution environments that may not support interactive prompts. No worker-facing instruction or template tells a worker to pause, wait for approval, query mid-task, or escalate to the user.

- A worker hands back on the record and never to the user. Whichever agent one level up next reads it decides what happens.
- When an approval boundary or decision point is reached, the worker files the complete artifact on the record and does not release the task as `done` when dependent implementation work requires an explicit approval decision; it structures the approval boundary per the review rules (e.g. `partial` with a queued review task wired with `depends_on`, or an explicit decision task) so dependent work remains strictly blocked until approval is recorded. Work that proceeds after the decision is scheduled as a separate downstream task that depends on it.
- `review` means a worker needs help to finish the task; it is transient and never a waiting state for decisions. If a worker needs help from a higher level, it releases as `review` documenting what help is needed on the record. Any reconcile pass reading a `review` task transitions it immediately.

## No nested agent CLI sessions in polecats

Polecat worker containers do not mount credentials for interactive login nor API keys for child agent sessions. Workers inside polecat containers must never start or invoke a nested agent CLI session (such as `claude`, `claude -p`, `agy`, or other interactive harnesses). Any task that calls for a nested agent CLI session must be declined and released with that reason instead of attempted.
