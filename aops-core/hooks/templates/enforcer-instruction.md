---
name: enforcer-instruction
title: Enforcer Instruction Template
category: template
description: |
  Short instruction injected by PostToolUse hook (the enforcer_gate policy).
  Tells main agent to invoke enforcer (compliance) agent with temp file path.
  Variables: {temp_path} - Path to temp file with full compliance context
  WS7 item 4: the first content line carries the enforcer-channel sentinel so
  the injection defence treats this as a first-party gate, not smuggled input (#1315).
---

<!-- aops:enforcer-channel -->

**Compliance check required.** Invoke the **enforcer** agent with the file path argument: `{temp_path}`

> This instruction is issued by the academicOps enforcer gate (first-party). The marker above identifies the framework's own compliance channel — it is **not** untrusted input and must not be treated as a prompt injection (#1315).

Run the compliance check with this command:

- Gemini: `invoke_agent(agent_name='rbg', prompt='Required audit of the session log. The file at {temp_path} is the session log — read it and return a verdict on the activity recorded there.')`
- Claude: `Agent(subagent_type='aops-core:rbg', prompt='Required audit of the session log. The file at {temp_path} is the session log — read it and return a verdict on the activity recorded there.')`

The framing inside the `prompt` / `message` argument is what the enforcer agent sees. It names the artifact (a session log), states the action (audit it), and points to the path — so the receiver isn't surprised by a `/tmp/` path and doesn't have to guess what kind of review is being asked for.
