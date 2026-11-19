---
trigger: always_on
description: Headless workers cannot pause interactively or escalate to the user; approval boundaries file artifacts on the record, agents never release review, and execution distinguishes state-only leaf workers from supervising coordinators.
---

## Workers cannot pause for a person

Workers operate headless in execution environments that may not support interactive prompts. No worker-facing instruction or template tells a worker to pause, wait for approval, query mid-task, or escalate to the user.

- A worker hands back on the record and never to the user. Whichever agent one level up next reads it decides what happens.
- **Container execution modes**:
  - **Plain leaf workers (`/pull`)**: Plain leaf workers operate strictly state-only on their claimed task. They may only mutate their claimed task's own fields (checking off acceptance criteria, recording verifiable evidence under `## Report`, transitioning status). They never reify workflows, create child tasks, inspect or modify edges across other tasks, compute reverse graph dependencies, or mint follow-up tasks on the graph; unblocking, sequencing, and parent rollup belong exclusively to the graph engine, dispatcher, and background truth maintenance (`wf-reconcile`).
  - **Container coordinators (`/supervise`)**: Container coordinators claim a repository-scoped epic task, enrich it by assembling workflows via `/reify` directly in-session (adapting workflows to container execution), coordinate subagent reviews and fan-out with incremental `git push` checkpoints, and deliver in-session pull requests. They create and wire repository-scoped follow-up tasks on the graph via `/q` (with `serves` value-chain links and `needs` prerequisite edges) strictly when work explicitly cannot be completed in-session: requiring a different repository (strictly one task per repository), a different time or external wait condition, or a workflow-mandated separate external agent or session.
- **Bounded execution**: Workers and subagent helpers operate under the lifecycle management, batched operations, and cache lifetime bounds defined in [`bounded-helpers.md`](bounded-helpers.md).
- **No speculative follow-up tasks**: A leaf worker whose check fails (e.g. QA or review) releases its task as `failed`. When an approval boundary or decision point is reached, the worker files the complete artifact on the record and does not release the task as `done` when dependent implementation work requires an explicit approval decision; it releases on the record as `partial` documenting what decision or help is needed in `reason`, without minting follow-up tasks. Sequencing, remediation, and downstream work live in the parent epic and are decided during the reconcile pass.
- **Workers never release `review`**: Workers are never told to use or release `review`. If a worker cannot complete work without higher-level help, it releases as `partial` documenting the required assistance in `reason`. Any reconcile pass reading an agent task in `review` transitions it immediately.
