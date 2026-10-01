---
description: Trigger a pass through Ida's assigned follow-up tasks and surface them for action
---

# /followups

Review and surface all pending Ida-held follow-up tasks awaiting action or trigger events.

## Execution

Execute the following to inspect Ida's held follow-ups from the personal knowledge base:

```bash
pkb list-tasks --assignee ida --parent agent_brains_ida --status ida_held
```

For each surfaced follow-up task:

1. Check the state of its referenced `depends_on` working task.
2. If the working task is `done`, `review`, or `partial`, evaluate the deliverable and prepare the delivery message back to Nic on his originating channel.
3. If the working task is still in progress, confirm the trigger condition remains valid.
4. Report an executive summary of pending follow-ups and actions taken.
