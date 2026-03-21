---
name: bump
type: command
category: instruction
description: Nudge an agent back into action
triggers:
  - "agent stuck"
  - "continue"
  - "nudge agent"
  - "keep going"
modifies_files: false
needs_task: true
mode: execution
domain:
  - operations
allowed-tools: []
permalink: commands/bump
---

_bump_. You seem to be stuck -- please continue.
