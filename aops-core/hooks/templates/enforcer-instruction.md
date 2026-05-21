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

- Gemini: `aops_core_enforcer(message='Required audit of the session log. The file at {temp_path} is the session log — read it and return a verdict on the activity recorded there.')`
- Claude: `Agent(subagent_type='aops-core:rbg', prompt='Required audit of the session log. The file at {temp_path} is the session log — read it and return a verdict on the activity recorded there.')`

The framing inside the `prompt` / `message` argument is what the enforcer agent sees. It names the artifact (a session log), states the action (audit it), and points to the path — so the receiver isn't surprised by a `/tmp/` path and doesn't have to guess what kind of review is being asked for.
