---
name: rbg-instruction
title: RBG Instruction Template
category: template
description: |
  Short instruction injected by PostToolUse hook (the rbg_gate policy).
  Tells main agent to invoke rbg (compliance) agent with temp file path.
  Variables: {temp_path} - Path to temp file with full compliance context
---

<academicOps rbg compliance check>
**Compliance check required.** Invoke the **RBG rbg** agent with the file path argument: `{temp_path}`

Run the compliance check with this command:

`Agent(subagent_type='aops-core:rbg', prompt='Required audit of the session log at: {temp_path}')`
</academicOps rbg compliance check>
