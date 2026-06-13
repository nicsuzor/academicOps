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
  Platform syntax:
    Gemini uses invoke_agent (Gemini CLI's direct-agent-invocation tool).
    Claude uses Agent(subagent_type='aops-core:rbg', ...) (Claude Code SDK).
    agy (Antigravity 2.0) is Claude-tool-compatible: agents ship with Claude tool
    names (no transformation in build.py), SPAWN_TOOLS has no separate agy entry,
    and agy uses Claude Code hook event names. So agy uses the same Agent() call
    as Claude. This was established when the post-copy ${CLAUDE_PLUGIN_ROOT}
    replacement was added for the antigravity build (see translate_tool_calls).
---

<!-- aops:enforcer-channel -->

**Compliance check required.** Invoke the **enforcer** agent with the file path argument: `{temp_path}`

This periodic compliance check is required as part of the academicOps enforcer gate.

Run the compliance check with this command:

- Gemini: `invoke_agent(agent_name='rbg', prompt='Required audit of the session log. The file at {temp_path} is the session log — read it and return a verdict on the activity recorded there.')`
- Claude: `Agent(subagent_type='aops-core:rbg', prompt='Required audit of the session log. The file at {temp_path} is the session log — read it and return a verdict on the activity recorded there.')`
- agy: `Agent(subagent_type='aops-core:rbg', prompt='Required audit of the session log. The file at {temp_path} is the session log — read it and return a verdict on the activity recorded there.')`
