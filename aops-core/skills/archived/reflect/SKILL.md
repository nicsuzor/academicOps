---
name: reflect
type: skill
category: instruction
description: End-of-day and weekly reflection on intention progress — part of the daily skill
triggers:
  - "reflect"
  - "end of day"
  - "how did today go"
  - "weekly review"
  - "review my progress"
modifies_files: true
needs_task: false
mode: conversational
domain:
  - operations
allowed-tools: Skill, Read, Bash, Write, Edit, AskUserQuestion, mcp__pkb__get_task_children, mcp__pkb__list_tasks
version: 1.1.0
permalink: skills-reflect
---

# /reflect

Reflection is part of the `/daily` skill. See [[daily/instructions/reflect.md]] for the full reflection workflow.

When the user asks to reflect, invoke the daily skill and follow the reflection instructions.
