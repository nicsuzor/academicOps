---
trigger: always_on
description: Headless workers cannot pause interactively or escalate to the user; approval boundaries file artifacts on the record, and agents are never told to release review.
---

## Workers cannot pause for a person

Workers operate headless in execution environments that may not support interactive prompts. No worker-facing instruction or template tells a worker to pause, wait for approval, query mid-task, or escalate to the user.

- A worker hands back on the record and never to the user. Whichever agent one level up next reads it decides what happens.
- **Worker state-only invariant**: A worker executing a task may only mutate that task's own state (checking off acceptance criteria, recording verifiable evidence, transitioning status). Workers never inspect or modify edges across other tasks, compute reverse graph dependencies, or mint follow-up verification tasks; unblocking and sequencing belong exclusively to the graph engine and dispatcher.
- **Bounded execution**: Workers and subagent helpers operate under the lifecycle management, batched operations, and cache lifetime bounds defined in [`bounded-helpers.md`](bounded-helpers.md).
- Workers never create or name follow-up tasks, and reports carry no 'Next task' pointer. A worker whose check fails (e.g. QA or review) releases its task as `failed`. When an approval boundary or decision point is reached, the worker files the complete artifact on the record and does not release the task as `done` when dependent implementation work requires an explicit approval decision; it releases on the record as `partial` documenting what decision or help is needed in `reason`, without minting follow-up tasks. Sequencing, remediation, and downstream work live in the parent epic and are decided during the reconcile pass.
- Workers are never told to use or release `review`. If a worker cannot complete work without higher-level help, it releases as `partial` documenting the required assistance in `reason`. Any reconcile pass reading an agent task in `review` transitions it immediately.
