---
trigger: always_on
description: Headless workers cannot pause interactively; tasks needing approval file a review artifact and end.
---

## Workers cannot pause for a person

Workers operate headless in execution environments that may not support interactive prompts. No worker-facing instruction or template tells a worker to pause, wait for approval, or query the user mid-task.

- A worker that reaches a review or approval boundary files a review artifact (its exact form left to repository or user preference), marks the task for review, and finishes execution.
- Work that proceeds after approval is scheduled as a separate downstream task that depends on the approval task being completed.
