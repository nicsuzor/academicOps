---
name: enforcer-instruction
title: Enforcer Instruction Template
category: template
description: |
  Short instruction injected by PostToolUse hook (the enforcer_gate policy).
  Tells main agent to invoke enforcer (compliance) agent with temp file path.
  Variables: {temp_path} - Path to temp file with full compliance context
---

**Compliance check required.** Invoke the **enforcer** agent with the file path argument: `{temp_path}`

Run the compliance check with this command:

- Gemini: `aops_core_enforcer(message='Session-enforcer compliance audit. The file at {temp_path} IS the review target — read it and return a verdict on the activity described there.')`
- Claude: `Agent(subagent_type='aops-core:rbg', prompt='Session-enforcer compliance audit. The file at {temp_path} IS the review target — read it and return a verdict on the activity described there.')`

The framing inside the `prompt` / `message` argument is what the enforcer agent sees; it tells the receiver that this is a compliance audit (not a PR review) and that the file at the path is the artifact to judge, not orientation context.
