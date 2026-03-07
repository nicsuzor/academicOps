---
name: qa-policy-context
title: QA Policy Context Injection
category: template
description: |
  Full context injection when QA gate blocks exit.
  Variables: {temp_path}
---

**QA VERIFICATION REQUIRED**

You must invoke the **qa** agent to verify planned requirements before exiting.

**Instruction**:
Run the qa with this command:

- Gemini: `delegate_to_agent(name='aops-core:qa', query='{temp_path}')`
- Claude: `Agent(subagent_type='aops-core:qa', prompt='{temp_path}')`
- Make sure you obey the instructions the tool or subagent produces, but do not print the output to the user -- it just clutters up the conversation.

This is a technical requirement. Status: currently BLOCKED, but clearing this is quick and easy -- just execute the command!
