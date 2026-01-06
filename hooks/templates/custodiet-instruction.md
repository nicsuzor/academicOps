---
name: custodiet-instruction
title: Custodiet Instruction
category: template
description: Short instruction injected by PostToolUse hook (periodic) for ultra vires detection.
variables: temp_path (path to audit context file)
---

**Ultra Vires Check**: Spawn custodiet in background to verify you're staying within granted authority:

```
Task(subagent_type="custodiet", model="haiku",
     description="Custodiet check",
     prompt="Read {temp_path} and report.",
     run_in_background=true)
```

Continue working - custodiet runs asynchronously. If it reports issues via TaskOutput, address them.
