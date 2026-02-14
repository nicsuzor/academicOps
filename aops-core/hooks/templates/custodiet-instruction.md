---
name: custodiet-instruction
title: Custodiet Instruction Template
category: template
description: |
  Short instruction injected by PostToolUse hook (custodiet_gate.py).
  Tells main agent to invoke custodiet skill with temp file path.
  Variables: {temp_path} - Path to temp file with full compliance context
---

**COMPLIANCE CHECK REQUIRED**

You must invoke the **custodiet** agent to run a compliance check before proceeding.

- DO NOT read the temp file yourself
- Run the custodiet with this command:
  - Gemini: `delegate_to_agent(name='aops-core:custodiet', query='Follow instructions in {temp_path}')`
  - Claude: `Task(subagent_type='aops-core:custodiet', prompt='Follow instructions in {temp_path}')`
- Make sure you obey the instructions the tool or subagent produces, but do not print the output to the user -- it just clutters up the conversation.
