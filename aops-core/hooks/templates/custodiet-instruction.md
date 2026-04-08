---
name: custodiet-instruction
title: Custodiet Instruction Template
category: template
description: |
  Short instruction injected by PostToolUse hook (custodiet_gate.py).
  Tells main agent to invoke rbg (compliance) agent with temp file path.
  Variables: {temp_path} - Path to temp file with full compliance context
---

**Compliance check required.** Invoke the **rbg** agent with the file path argument: `{temp_path}`

Run the compliance check with this command:

- Gemini: `aops_core_rbg(message='{temp_path}')`
- Claude: `Agent(subagent_type='aops-core:custodiet', prompt='{temp_path}')`

Pass the file path directly to the agent — it will read the file and perform the compliance check.
