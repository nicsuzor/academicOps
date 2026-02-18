---
name: custodiet-instruction
title: Custodiet Instruction Template
category: template
description: |
  Short instruction injected by PostToolUse hook (custodiet_gate.py).
  Tells main agent to invoke custodiet skill with temp file path.
  Variables: {temp_path} - Path to temp file with full compliance context
---

**Compliance check required.** Invoke the **custodiet** agent with the file path argument: `{temp_path}`

Run the custodiet with this command:
- Gemini: `delegate_to_agent(name='aops-core:custodiet', query='{temp_path}')`
- Claude: `Task(subagent_type='aops-core:custodiet', prompt='{temp_path}')`

Pass the file path directly to the agent — it will read the file and perform the compliance check.
