---
name: custodiet-instruction
title: Custodiet Instruction Template
category: template
description: |
  Short instruction injected by PostToolUse hook (custodiet_gate.py).
  Tells main agent to invoke custodiet skill with temp file path.
  Variables: {temp_path} - Path to temp file with full compliance context
---

**MANDATORY**: Invoke custodiet compliance check (do NOT read the temp file yourself):

```
Invoke the **custodiet** skill:

"Analyze the user's implicit authority and provide a risk assessment of {temp_path}."
```

Follow custodiet's guidance: if BLOCK is returned, STOP and address the issue before continuing.
