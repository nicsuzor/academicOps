---
name: aops
type: command
category: instruction
description: Show framework capabilities - commands, skills, agents, and how to use them
triggers:
  - "show capabilities"
  - "what can you do"
  - "help with framework"
modifies_files: false
needs_task: false
mode: conversational
domain:
  - framework
---

# /aops - Framework Discovery command

Output the contents of README.md to show the user what the framework can do.

```
Read $AOPS/README.md
```

Present the full content to the user. This is their entry point for understanding available capabilities.
