---
name: enforcer-instruction
title: Enforcer Instruction Template
category: template
description: |
  Short instruction injected by PostToolUse hook (the enforcer_gate policy).
  Tells main agent to invoke enforcer (compliance) agent with temp file path.
  Variables: {temp_path} - Path to temp file with full compliance context
---

**Compliance check required.** Invoke the **RBG enforcer** agent with the file path argument: `{temp_path}`

Run the compliance check with this command:

`Agent(subagent_type='aops-core:rbg', prompt='Required audit of the session log at: {temp_path}')`
