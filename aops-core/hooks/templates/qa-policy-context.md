---
name: qa-policy-context
title: QA Policy Context Injection
category: template
description: |
  Full context injection when QA gate blocks exit.
  Variables: {temp_path}
---

**QA VERIFICATION REQUIRED**

You must invoke the **marsha** agent (using the `/verify` skill) to verify planned requirements before exiting.

**Instruction**:
Run verification with this command:

- Gemini: `aops_core_marsha(message='{temp_path}')`
- Claude: `Agent(subagent_type='aops-core:marsha', prompt='{temp_path}\n\nInvoke /verify for methodology.')`
- Make sure you obey the instructions the tool or subagent produces, but do not print the output to the user -- it just clutters up the conversation.

This is a technical requirement. Status: currently BLOCKED, but clearing this is quick and easy -- just execute the command!
