---
name: custodiet-instruction
title: Custodiet Instruction Template
category: template
description: |
  Short instruction injected by PostToolUse hook (custodiet_gate.py).
  Tells main agent to spawn custodiet subagent with temp file path.
  Variables: {temp_path} - Path to temp file with full compliance context
---

**MANDATORY**: Spawn custodiet compliance check (do NOT read the temp file yourself):

```
Task(subagent_type="custodiet", model="haiku",
     description="Compliance check",
     prompt="Read {temp_path} and assess compliance.")
```

Follow custodiet's guidance: if BLOCK is returned, STOP and address the issue before continuing.
