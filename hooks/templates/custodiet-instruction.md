---
name: custodiet-instruction
title: Custodiet Instruction
category: template
description: Short instruction injected by PostToolUse hook (periodic) for ultra vires detection.
---

# Custodiet Instruction Template

Short instruction injected every ~7 tool calls.
Tells main agent to spawn custodiet subagent.

Variables:
- `{temp_path}` - Path to temp file with session context

---
**Ultra Vires Check**: Spawn custodiet to verify you're staying within granted authority:

```
Task(subagent_type="custodiet", model="haiku",
     description="Custodiet check",
     prompt="Read {temp_path} and check for authority violations.")
```

If custodiet reports issues, address them before continuing. This check catches drift early.
