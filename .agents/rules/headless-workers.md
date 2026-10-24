---
trigger: always_on
description: Headless workers cannot pause interactively or escalate to the user; approval boundaries file artifacts on the record, and review is transient help rather than a decision wait state.
---

## Workers cannot pause for a person

Workers operate headless in execution environments that may not support interactive prompts. No worker-facing instruction or template tells a worker to pause, wait for approval, query mid-task, or escalate to the user.

- A worker hands back on the record and never to the user. Whichever agent one level up next reads it decides what happens.
- Workers never create or name follow-up tasks, and reports carry no 'Next task' pointer. A worker whose check fails (e.g. QA or review) releases its task as `failed`. When an approval boundary or decision point is reached, the worker files the complete artifact on the record and does not release the task as `done` when dependent implementation work requires an explicit approval decision; it releases on the record (e.g. `partial` or `review` documenting what decision or help is needed in `reason`), without minting follow-up tasks. Sequencing, remediation, and downstream work live in the parent epic and are decided during the reconcile pass.
- `review` means a worker needs help to finish the task; it is transient and never a waiting state for decisions. If a worker needs help from a higher level, it releases as `review` documenting what help is needed on the record. Any reconcile pass reading a `review` task transitions it immediately.
