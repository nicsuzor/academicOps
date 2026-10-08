---
trigger: always_on
description: Headless workers cannot pause interactively; a task needing a decision only Nic can make files a review artifact and ends, and pending agent steps release as partial.
---

## Workers cannot pause for a person

Workers operate headless in execution environments that may not support interactive prompts. No worker-facing instruction or template tells a worker to pause, wait for approval, or query the user mid-task.

- A worker that reaches an approval boundary, meaning a decision only Nic (the user) can make, files a review artifact (its exact form left to repository or user preference), marks the task for review, and finishes execution. A QA, code-review or merge step is agent work, not an approval boundary: the worker releases the task as `partial` with a follow-up task carrying that step.
- Work that proceeds after approval is scheduled as a separate downstream task that depends on the approval task being completed.
